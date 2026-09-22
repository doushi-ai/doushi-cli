"""Configuration and credential management for Doushi CLI."""

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_API_URL = "https://api.doushi.ai"
DEFAULT_DASHBOARD_URL = "https://app.doushi.ai"

DOUSHI_DIR = Path.home() / ".doushi"
CREDENTIALS_FILE = DOUSHI_DIR / "credentials"
CONFIG_FILE = DOUSHI_DIR / "config.json"


def ensure_doushi_dir() -> None:
    """Ensure ~/.doushi directory exists with secure permissions."""
    DOUSHI_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(DOUSHI_DIR, stat.S_IRWXU)  # 0700
    except Exception:
        pass


def get_api_url() -> str:
    """Get active API endpoint from env, config file, or default."""
    if os.getenv("DOUSHI_API_URL"):
        return os.environ["DOUSHI_API_URL"].rstrip("/")
    config = load_config()
    return config.get("api_url", DEFAULT_API_URL).rstrip("/")


def get_api_key() -> Optional[str]:
    """Get active API key from env or credentials file."""
    # 1. Environment variable override
    if os.getenv("DOUSHI_API_KEY"):
        return os.environ["DOUSHI_API_KEY"].strip()
    
    # 2. Stored credentials
    creds = load_credentials()
    current_context = creds.get("current_context", "default")
    contexts = creds.get("contexts", {})
    context_data = contexts.get(current_context, {})
    return context_data.get("api_key")


def load_credentials() -> Dict[str, Any]:
    """Load credentials JSON from ~/.doushi/credentials."""
    if not CREDENTIALS_FILE.exists():
        return {"current_context": "default", "contexts": {}}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"current_context": "default", "contexts": {}}


def save_credentials(api_key: str, user_email: Optional[str] = None, org_name: Optional[str] = None, tier: Optional[str] = None, context: str = "default") -> None:
    """Save credentials to ~/.doushi/credentials with secure 0600 permissions."""
    ensure_doushi_dir()
    creds = load_credentials()
    if "contexts" not in creds:
        creds["contexts"] = {}
    
    creds["current_context"] = context
    creds["contexts"][context] = {
        "api_key": api_key,
        "user_email": user_email,
        "org_name": org_name,
        "tier": tier,
    }
    
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)
    
    try:
        os.chmod(CREDENTIALS_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except Exception:
        pass


def delete_credentials() -> None:
    """Remove stored credentials on logout."""
    if CREDENTIALS_FILE.exists():
        try:
            CREDENTIALS_FILE.unlink()
        except Exception:
            pass


def load_config() -> Dict[str, Any]:
    """Load settings from ~/.doushi/config.json."""
    if not CONFIG_FILE.exists():
        return {
            "api_url": DEFAULT_API_URL,
            "output_format": "table",
            "auto_open_browser": True
        }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"api_url": DEFAULT_API_URL, "output_format": "table"}


def save_config(config: Dict[str, Any]) -> None:
    """Save settings to ~/.doushi/config.json."""
    ensure_doushi_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
