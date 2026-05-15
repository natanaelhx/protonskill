#!/usr/bin/env python3
"""Local functional test for email_cli.py.

Starts minimal IMAP and SMTP servers on localhost, then exercises config
validation, listing, showing, dry-run send, and real SMTP submission without
touching any external account.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from email.parser import Parser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "email_cli.py"

MESSAGE = (
    "From: Alice Example <alice@example.com>\r\n"
    "To: Bot <bot@example.com>\r\n"
    "Subject: Functional Test\r\n"
    "Date: Fri, 15 May 2026 12:00:00 +0000\r\n"
    "Message-ID: <functional-test@example.com>\r\n"
    "\r\n"
    "Hello from the fake IMAP server.\r\n"
)


class MinimalIMAPServer(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.ready = threading.Event()
        self.error: Exception | None = None
        self.host = "127.0.0.1"
        self.port = 0

    def run(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((self.host, 0))
                server.listen(5)
                self.port = server.getsockname()[1]
                self.ready.set()
                while True:
                    conn, _addr = server.accept()
                    threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
        except Exception as exc:
            self.error = exc
            self.ready.set()

    def handle_client(self, conn: socket.socket) -> None:
        with conn:
            conn.sendall(b"* OK fake imap ready\r\n")
            buffer = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buffer += chunk
                while b"\r\n" in buffer:
                    raw, buffer = buffer.split(b"\r\n", 1)
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace")
                    parts = line.split(" ", 2)
                    tag = parts[0]
                    command = parts[1].upper() if len(parts) > 1 else ""
                    rest = parts[2] if len(parts) > 2 else ""

                    if command == "CAPABILITY":
                        self.send(conn, b"* CAPABILITY IMAP4rev1 UIDPLUS")
                        self.send(conn, f"{tag} OK CAPABILITY completed".encode())
                    elif command == "LOGIN":
                        self.send(conn, f"{tag} OK LOGIN completed".encode())
                    elif command in {"SELECT", "EXAMINE"}:
                        self.send(conn, b"* 1 EXISTS")
                        self.send(conn, f"{tag} OK [{command}] completed".encode())
                    elif command == "UID" and rest.upper().startswith("SEARCH"):
                        self.send(conn, b"* SEARCH 101")
                        self.send(conn, f"{tag} OK SEARCH completed".encode())
                    elif command == "UID" and rest.upper().startswith("FETCH"):
                        if "HEADER.FIELDS" in rest.upper():
                            payload = MESSAGE.split("\r\n\r\n", 1)[0].encode() + b"\r\n\r\n"
                        else:
                            payload = MESSAGE.encode()
                        prefix = f"* 1 FETCH (UID 101 FLAGS (\\Seen) BODY[] {{{len(payload)}}}".encode()
                        conn.sendall(prefix + b"\r\n" + payload + b")\r\n")
                        self.send(conn, f"{tag} OK FETCH completed".encode())
                    elif command == "LOGOUT":
                        self.send(conn, b"* BYE logging out")
                        self.send(conn, f"{tag} OK LOGOUT completed".encode())
                        return
                    else:
                        self.send(conn, f"{tag} BAD unsupported command {command}".encode())

    @staticmethod
    def send(conn: socket.socket, line: bytes) -> None:
        conn.sendall(line + b"\r\n")


class MinimalSMTPServer(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.ready = threading.Event()
        self.error: Exception | None = None
        self.host = "127.0.0.1"
        self.port = 0
        self.messages: list[str] = []

    def run(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((self.host, 0))
                server.listen(5)
                self.port = server.getsockname()[1]
                self.ready.set()
                while True:
                    conn, _addr = server.accept()
                    threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
        except Exception as exc:
            self.error = exc
            self.ready.set()

    def handle_client(self, conn: socket.socket) -> None:
        with conn:
            conn.sendall(b"220 fake smtp ready\r\n")
            data_mode = False
            message_lines: list[str] = []
            while True:
                raw = self.recv_line(conn)
                if raw is None:
                    return
                line = raw.decode("utf-8", errors="replace")
                if data_mode:
                    if line == ".":
                        self.messages.append("\n".join(message_lines))
                        message_lines = []
                        data_mode = False
                        conn.sendall(b"250 message accepted\r\n")
                    else:
                        message_lines.append(line)
                    continue

                upper = line.upper()
                if upper.startswith(("EHLO", "HELO")):
                    conn.sendall(b"250-localhost\r\n250 OK\r\n")
                elif upper.startswith("MAIL FROM"):
                    conn.sendall(b"250 sender ok\r\n")
                elif upper.startswith("RCPT TO"):
                    conn.sendall(b"250 recipient ok\r\n")
                elif upper == "DATA":
                    data_mode = True
                    conn.sendall(b"354 end with dot\r\n")
                elif upper == "QUIT":
                    conn.sendall(b"221 bye\r\n")
                    return
                else:
                    conn.sendall(b"250 ok\r\n")

    @staticmethod
    def recv_line(conn: socket.socket) -> bytes | None:
        data = b""
        while not data.endswith(b"\r\n"):
            chunk = conn.recv(1)
            if not chunk:
                return None
            data += chunk
        return data[:-2]


def run_cli(config: Path, *args: str) -> dict:
    env = os.environ.copy()
    env["EMAIL_TEST_USER"] = "bot@example.com"
    env["EMAIL_TEST_PASSWORD"] = "test-password"
    result = subprocess.run(
        [sys.executable, str(CLI), "--config", str(config), *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(args)}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return json.loads(result.stdout)


def main() -> None:
    imap = MinimalIMAPServer()
    smtp = MinimalSMTPServer()
    imap.start()
    smtp.start()
    imap.ready.wait(5)
    smtp.ready.wait(5)
    if imap.error:
        raise imap.error
    if smtp.error:
        raise smtp.error

    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "email-manager.json"
        config.write_text(
            json.dumps(
                {
                    "default_account": "main",
                    "accounts": {
                        "main": {
                            "from": "Bot <bot@example.com>",
                            "imap": {
                                "host": imap.host,
                                "port": imap.port,
                                "ssl": False,
                                "mailbox": "INBOX",
                                "user_env": "EMAIL_TEST_USER",
                                "password_env": "EMAIL_TEST_PASSWORD",
                            },
                            "smtp": {
                                "host": smtp.host,
                                "port": smtp.port,
                                "ssl": False,
                                "starttls": False,
                            },
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        assert run_cli(config, "check-config", "--connect")["ok"] is True

        listed = run_cli(config, "list", "--limit", "5")
        assert listed["ok"] is True
        assert listed["messages"][0]["uid"] == "101"
        assert listed["messages"][0]["subject"] == "Functional Test"

        shown = run_cli(config, "show", "101")
        assert shown["ok"] is True
        assert "fake IMAP server" in shown["message"]["body"]

        dry_run = run_cli(
            config,
            "send",
            "--to",
            "alice@example.com",
            "--subject",
            "Dry run",
            "--body",
            "Draft only",
        )
        assert dry_run["status"] == "dry-run"
        assert smtp.messages == []

        sent = run_cli(
            config,
            "send",
            "--to",
            "alice@example.com",
            "--subject",
            "Live fake send",
            "--body",
            "Send through fake SMTP",
            "--yes-send",
        )
        assert sent["status"] == "sent"
        assert len(smtp.messages) == 1
        parsed = Parser().parsestr(smtp.messages[0])
        assert parsed["Subject"] == "Live fake send"
        assert "Send through fake SMTP" in parsed.get_payload()

    print("local functional test passed")


if __name__ == "__main__":
    main()
