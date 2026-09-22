"""HTTP API Client for interacting with Doushi.ai backend."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

from doushi.config import get_api_key, get_api_url
from doushi.ui import print_error_panel, print_tier_limit_error

# Platform tier dataset upload limits (Bytes, Label, MB)
TIER_LIMITS: Dict[str, Tuple[int, str, float]] = {
    "free": (25 * 1024 * 1024, "25 MB", 25.0),
    "starter": (150 * 1024 * 1024, "150 MB", 150.0),
    "pro": (2 * 1024 * 1024 * 1024, "2 GB", 2048.0),
    "growth": (5 * 1024 * 1024 * 1024, "5 GB", 5120.0),
    "team": (5 * 1024 * 1024 * 1024, "5 GB", 5120.0),
    "scale": (5 * 1024 * 1024 * 1024, "5 GB", 5120.0),
    "enterprise": (20 * 1024 * 1024 * 1024, "20 GB", 20480.0),
}


class DoushiAPIError(Exception):
    """Custom exception for Doushi API errors with status and details."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


ALLOWED_DATASET_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".xls", ".json", ".tsv"}


class DoushiClient:
    """Synchronous HTTP client for Doushi backend."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 60.0):
        self.api_key = api_key or get_api_key()
        self.base_url = (base_url or get_api_url()).rstrip("/")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "doushi-cli/0.1.0",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Validate response status and return parsed JSON."""
        try:
            data = response.json()
        except Exception:
            data = {"detail": response.text}

        if response.is_success:
            return data

        detail = data.get("detail") if isinstance(data, dict) else str(data)
        if not detail:
            detail = response.reason_phrase

        if response.status_code == 401:
            raise DoushiAPIError(
                message="Authentication failed. Please configure a valid API key with `doushi configure` or `doushi login`.",
                status_code=401,
                details=data
            )
        elif response.status_code == 403:
            raise DoushiAPIError(
                message=f"Access denied: {detail}",
                status_code=403,
                details=data
            )
        elif response.status_code == 413:
            raise DoushiAPIError(
                message=f"Payload limit exceeded: {detail}",
                status_code=413,
                details=data
            )
        elif response.status_code == 404:
            raise DoushiAPIError(
                message=f"Resource not found: {detail}",
                status_code=404,
                details=data
            )
        else:
            raise DoushiAPIError(
                message=f"API Error ({response.status_code}): {detail}",
                status_code=response.status_code,
                details=data
            )

    def check_auth_or_exit(self) -> str:
        """Ensure API key exists, or display helpful error and exit."""
        if not self.api_key:
            print_error_panel(
                title="Authentication Required",
                message="No Doushi API Key found. You must configure your credentials before running this command.",
                remedy="Run `doushi configure` or `doushi login` to set up your API Key,\nor export DOUSHI_API_KEY='dsh_live_...'"
            )
            sys.exit(1)
        return self.api_key

    def get_whoami(self) -> Dict[str, Any]:
        """Fetch current user and organization details."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/users/sync", json={}, headers=self._get_headers())
            return self._handle_response(resp)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects for current organization."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/api/projects", headers=self._get_headers())
            data = self._handle_response(resp)
            if isinstance(data, list):
                return data
            return data.get("projects", [])

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Fetch details of a single project."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/api/projects/{project_id}", headers=self._get_headers())
            return self._handle_response(resp)

    def create_project(self, name: str, provider: str = "gemini", api_key_override: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project record in database."""
        self.check_auth_or_exit()
        payload = {
            "name": name,
            "llm_provider": provider,
            "api_key": api_key_override or "default"
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/projects", json=payload, headers=self._get_headers())
            return self._handle_response(resp)

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.delete(f"{self.base_url}/api/projects/{project_id}", headers=self._get_headers())
            return self._handle_response(resp)

    def check_file_limits(self, file_path: Path, tier: str = "free") -> None:
        """Pre-flight check on dataset size and format against active tier limit."""
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file '{file_path}' does not exist.")
            
        file_size_bytes = file_path.stat().st_size
        if file_size_bytes == 0:
            raise ValueError(f"Dataset file '{file_path.name}' is empty (0 bytes).")

        ext = file_path.suffix.lower()
        if ext not in ALLOWED_DATASET_EXTENSIONS:
            allowed_list = ", ".join(sorted(ALLOWED_DATASET_EXTENSIONS))
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported dataset formats: {allowed_list}"
            )

        normalized_tier = tier.lower()
        max_bytes, limit_label, max_mb = TIER_LIMITS.get(normalized_tier, TIER_LIMITS["free"])
        
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_bytes > max_bytes:
            print_tier_limit_error(file_path.name, file_size_mb, normalized_tier, max_mb)
            sys.exit(1)

    def request_upload_url(self, project_id: str, filename: str, file_size: int) -> Dict[str, Any]:
        """Request S3 presigned upload URL from backend."""
        self.check_auth_or_exit()
        payload = {
            "project_id": project_id,
            "filename": filename,
            "file_size": file_size
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/upload-url", json=payload, headers=self._get_headers())
            return self._handle_response(resp)

    def upload_file_to_s3(self, presigned_url: str, file_path: Path) -> None:
        """Upload dataset directly to S3 with live transfer progress bar."""
        file_size = file_path.stat().st_size
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Uploading dataset[/bold cyan] {task.fields[filename]}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task_id = progress.add_task("upload", filename=file_path.name, total=file_size)
            
            with open(file_path, "rb") as f:
                content = f.read()
                
            headers = {"Content-Type": "application/octet-stream"}
            with httpx.Client(timeout=120.0) as client:
                resp = client.put(presigned_url, content=content, headers=headers)
                if not resp.is_success:
                    raise DoushiAPIError(
                        f"Failed to upload dataset to storage: {resp.status_code} {resp.text}",
                        status_code=resp.status_code
                    )
            progress.update(task_id, completed=file_size)

    def start_pipeline(self, project_id: str, prompt: str) -> Dict[str, Any]:
        """Dispatch autonomous agent training pipeline."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/predict-goal",
                data={"project_id": project_id, "prompt": prompt},
                headers=self._get_headers()
            )
            return self._handle_response(resp)

    def predict(self, project_id: str, data: Any) -> Dict[str, Any]:
        """Send inference request to project model."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            if isinstance(data, list):
                # Batch prediction
                resp = client.post(
                    f"{self.base_url}/api/projects/{project_id}/predict-batch",
                    json={"data": data},
                    headers=self._get_headers()
                )
            else:
                resp = client.post(
                    f"{self.base_url}/api/projects/{project_id}/predict",
                    json={"data": data},
                    headers=self._get_headers()
                )
            return self._handle_response(resp)

    def chat(self, project_id: str, message: str) -> Dict[str, Any]:
        """Send chat message to project agent."""
        self.check_auth_or_exit()
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/projects/{project_id}/chat",
                json={"message": message},
                headers=self._get_headers()
            )
            return self._handle_response(resp)
