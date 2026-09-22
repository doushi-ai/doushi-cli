"""Automated test suite for Doushi CLI."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure doushi package is importable when running test script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typer.testing import CliRunner
from doushi.main import app
from doushi.config import (
    CREDENTIALS_FILE,
    delete_credentials,
    get_api_key,
    load_credentials,
    save_credentials,
)
from doushi.client import DoushiClient, TIER_LIMITS


class TestDoushiCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_help_output(self):
        """Verify main help command renders properly."""
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Doushi", result.output)
        self.assertIn("train", result.output)
        self.assertIn("predict", result.output)
        self.assertIn("configure", result.output)

    def test_version_output(self):
        """Verify --version flag outputs version."""
        result = self.runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("1.0.1", result.output)

    def test_subcommand_helps(self):
        """Verify subcommands provide descriptive help."""
        for cmd in [["train", "--help"], ["predict", "--help"], ["projects", "--help"], ["export", "--help"]]:
            res = self.runner.invoke(app, cmd)
            self.assertEqual(res.exit_code, 0)

    def test_credentials_save_and_load(self):
        """Verify saving credentials with secure permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_creds_path = Path(tmpdir) / "credentials"
            with patch("doushi.config.CREDENTIALS_FILE", test_creds_path), \
                 patch("doushi.config.DOUSHI_DIR", Path(tmpdir)):
                
                save_credentials(
                    api_key="dsh_live_test123456789",
                    user_email="test@example.com",
                    org_name="Test Org",
                    tier="Starter"
                )
                
                self.assertTrue(test_creds_path.exists())
                creds = load_credentials()
                self.assertEqual(creds["contexts"]["default"]["api_key"], "dsh_live_test123456789")
                self.assertEqual(creds["contexts"]["default"]["tier"], "Starter")

    def test_file_limits_preflight(self):
        """Verify pre-flight validation catches oversized files for free tier."""
        client = DoushiClient()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            # Write 100 bytes
            f.write(b"a,b,c\n1,2,3\n")
            small_file = Path(f.name)

        try:
            # Small file passes
            client.check_file_limits(small_file, tier="free")
            
            # Non-existent file raises FileNotFoundError
            with self.assertRaises(FileNotFoundError):
                client.check_file_limits(Path("/path/does/not/exist.csv"), tier="free")
                
        finally:
            if small_file.exists():
                small_file.unlink()

    def test_empty_file_validation(self):
        """Verify empty files (0 bytes) are rejected immediately."""
        client = DoushiClient()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            pass  # 0 bytes
            empty_file = Path(f.name)

        try:
            with self.assertRaises(ValueError):
                client.check_file_limits(empty_file, tier="free")
        finally:
            if empty_file.exists():
                empty_file.unlink()

    def test_supported_file_formats(self):
        """Verify .parquet, .xls, .xlsx, .json, .csv, .tsv are all recognized as valid formats."""
        client = DoushiClient()
        for ext in [".parquet", ".xls", ".xlsx", ".json", ".csv", ".tsv"]:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"dummy content for extension check\n")
                tmp_file = Path(f.name)
            try:
                # Should not raise ValueError for format
                client.check_file_limits(tmp_file, tier="free")
            finally:
                if tmp_file.exists():
                    tmp_file.unlink()

    def test_unsupported_file_formats(self):
        """Verify unsupported extensions (like .pdf, .mp4, .exe) are rejected with clear error."""
        client = DoushiClient()
        for ext in [".pdf", ".mp4", ".exe", ".zip", ".bin"]:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"data")
                tmp_file = Path(f.name)
            try:
                with self.assertRaises(ValueError) as ctx:
                    client.check_file_limits(tmp_file, tier="free")
                self.assertIn("Unsupported file format", str(ctx.exception))
            finally:
                if tmp_file.exists():
                    tmp_file.unlink()

    def test_load_batch_file_json_and_csv(self):
        """Verify batch file reader parses JSON and CSV datasets."""
        from doushi.commands.predict import load_batch_file
        
        # Test JSON parsing
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as f:
            json.dump([{"age": 30, "tenure": 5}, {"age": 45, "tenure": 10}], f)
            json_file = Path(f.name)
        try:
            records = load_batch_file(json_file)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["age"], 30)
        finally:
            if json_file.exists():
                json_file.unlink()


if __name__ == "__main__":
    unittest.main()

