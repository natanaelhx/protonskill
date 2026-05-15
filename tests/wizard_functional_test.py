#!/usr/bin/env python3
"""Functional test for configure_wizard.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIZARD = ROOT / "scripts" / "configure_wizard.py"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        answers = "\n".join(
            [
                "proton",
                "proton-bridge",
                "bot@example.com",
                "Bot Example",
                "EMAIL_PROTON",
                "127.0.0.1",
                "1143",
                "n",
                "127.0.0.1",
                "1025",
                "n",
                "n",
                "INBOX",
                "",
            ]
        )
        result = subprocess.run(
            [sys.executable, str(WIZARD), "--config", str(config_path), "--force"],
            input=answers,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(f"wizard failed\nstdout={result.stdout}\nstderr={result.stderr}")

        config = json.loads(config_path.read_text(encoding="utf-8"))
        account = config["accounts"]["proton"]
        assert account["from"] == "Bot Example <bot@example.com>"
        assert account["imap"]["host"] == "127.0.0.1"
        assert account["imap"]["port"] == 1143
        assert account["smtp"]["host"] == "127.0.0.1"
        assert account["smtp"]["port"] == 1025
        assert account["imap"]["user_env"] == "EMAIL_PROTON_USER"
        assert account["smtp"]["password_env"] == "EMAIL_PROTON_PASSWORD"
        assert "EMAIL_PROTON_PASSWORD" in result.stdout

    print("wizard functional test passed")


if __name__ == "__main__":
    main()
