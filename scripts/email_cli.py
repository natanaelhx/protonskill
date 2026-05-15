#!/usr/bin/env python3
"""Small IMAP/SMTP helper for the email-manager skill.

Outputs JSON so an agent can parse results reliably. The script has no external
dependencies and intentionally defaults to dry-run for sending.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email
import html.parser
import imaplib
import json
import os
import re
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.utils import formatdate, getaddresses, make_msgid, parsedate_to_datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("~/.openclaw/state/email-manager/config.json").expanduser()


class ConfigError(RuntimeError):
    pass


class HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def config_path() -> Path:
    return Path(os.environ.get("EMAIL_MANAGER_CONFIG", str(DEFAULT_CONFIG))).expanduser()


def sample_config() -> dict[str, Any]:
    return {
        "default_account": "main",
        "accounts": {
            "main": {
                "from": "Your Name <you@example.com>",
                "imap": {
                    "host": "imap.example.com",
                    "port": 993,
                    "ssl": True,
                    "mailbox": "INBOX",
                    "user_env": "EMAIL_MAIN_USER",
                    "password_env": "EMAIL_MAIN_PASSWORD",
                },
                "smtp": {
                    "host": "smtp.example.com",
                    "port": 465,
                    "ssl": True,
                    "starttls": False,
                    "user_env": "EMAIL_MAIN_USER",
                    "password_env": "EMAIL_MAIN_PASSWORD",
                },
            }
        },
    }


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def fail(message: str, code: int = 2) -> None:
    print_json({"ok": False, "error": message})
    raise SystemExit(code)


def load_config(account_name: str | None) -> tuple[str, dict[str, Any]]:
    path = config_path()
    if not path.exists():
        raise ConfigError(
            f"Config not found at {path}. Run init-config or read references/config.md."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc

    accounts = data.get("accounts")
    if not isinstance(accounts, dict) or not accounts:
        raise ConfigError("Config must contain a non-empty 'accounts' object.")

    selected = account_name or data.get("default_account") or next(iter(accounts))
    if selected not in accounts:
        raise ConfigError(f"Account '{selected}' not found in config.")
    return selected, accounts[selected]


def section(account: dict[str, Any], name: str) -> dict[str, Any]:
    value = account.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"Account is missing '{name}' section.")
    return value


def credential(settings: dict[str, Any], key: str, required: bool = True) -> str | None:
    env_name = settings.get(f"{key}_env")
    if env_name:
        value = os.environ.get(str(env_name))
        if value:
            return value
        if required:
            raise ConfigError(f"Environment variable {env_name} is not set.")
        return None

    if key == "password" and settings.get(key):
        raise ConfigError("Inline passwords are refused. Use password_env instead.")

    value = settings.get(key)
    if value:
        return str(value)
    if required:
        raise ConfigError(f"Missing credential '{key}' or '{key}_env'.")
    return None


def decode_mime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def parse_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return value


def parse_addresses(value: str | None) -> list[str]:
    if not value:
        return []
    return [addr for _name, addr in getaddresses([value]) if addr]


def message_summary(uid: str, msg: Message, flags: str = "") -> dict[str, Any]:
    return {
        "uid": uid,
        "date": parse_date(msg.get("Date")),
        "from": decode_mime(msg.get("From")),
        "to": parse_addresses(msg.get("To")),
        "cc": parse_addresses(msg.get("Cc")),
        "subject": decode_mime(msg.get("Subject")),
        "message_id": msg.get("Message-ID", ""),
        "flags": flags,
    }


def imap_connect(account: dict[str, Any], readonly: bool = True) -> imaplib.IMAP4:
    settings = section(account, "imap")
    host = settings.get("host")
    if not host:
        raise ConfigError("IMAP host is missing.")
    use_ssl = bool(settings.get("ssl", True))
    port = int(settings.get("port") or (993 if use_ssl else 143))
    user = credential(settings, "user")
    password = credential(settings, "password")

    if use_ssl:
        conn: imaplib.IMAP4 = imaplib.IMAP4_SSL(str(host), port)
    else:
        conn = imaplib.IMAP4(str(host), port)
    conn.login(user, password)  # type: ignore[arg-type]
    mailbox = str(settings.get("mailbox") or "INBOX")
    typ, data = conn.select(mailbox, readonly=readonly)
    if typ != "OK":
        raise RuntimeError(f"Unable to select mailbox {mailbox}: {data!r}")
    return conn


def smtp_connect(account: dict[str, Any]) -> smtplib.SMTP:
    settings = section(account, "smtp")
    host = settings.get("host")
    if not host:
        raise ConfigError("SMTP host is missing.")
    use_ssl = bool(settings.get("ssl", True))
    starttls = bool(settings.get("starttls", False))
    port = int(settings.get("port") or (465 if use_ssl else 587))
    user = credential(settings, "user", required=False)
    password = credential(settings, "password", required=False)

    if use_ssl:
        conn: smtplib.SMTP = smtplib.SMTP_SSL(str(host), port, context=ssl.create_default_context())
    else:
        conn = smtplib.SMTP(str(host), port)
        if starttls:
            conn.starttls(context=ssl.create_default_context())
    if user and password:
        conn.login(user, password)
    return conn


def imap_date(raw: str) -> str:
    parsed = dt.datetime.strptime(raw, "%Y-%m-%d")
    return parsed.strftime("%d-%b-%Y")


def imap_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def search_criteria(args: argparse.Namespace) -> list[str]:
    criteria: list[str] = ["UNSEEN" if args.unread else "ALL"]
    if args.since:
        criteria.extend(["SINCE", imap_date(args.since)])
    if args.sender:
        criteria.extend(["FROM", imap_quote(args.sender)])
    if args.subject:
        criteria.extend(["SUBJECT", imap_quote(args.subject)])
    if args.raw:
        criteria.extend(args.raw)
    return criteria


def extract_flags(prefix: bytes) -> str:
    match = re.search(rb"FLAGS \(([^)]*)\)", prefix)
    if not match:
        return ""
    return match.group(1).decode("utf-8", errors="replace")


def fetch_header(conn: imaplib.IMAP4, uid: bytes) -> tuple[Message, str]:
    typ, data = conn.uid(
        "fetch",
        uid,
        "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID REFERENCES)])",
    )
    if typ != "OK":
        raise RuntimeError(f"Fetch failed for UID {uid.decode()}: {data!r}")
    flags = ""
    raw_header = b""
    for item in data:
        if isinstance(item, tuple):
            flags = extract_flags(item[0])
            raw_header = item[1]
            break
    return email.message_from_bytes(raw_header), flags


def extract_body(msg: Message, max_chars: int) -> tuple[str, list[dict[str, Any]]]:
    attachments: list[dict[str, Any]] = []
    plain_parts: list[str] = []
    html_parts: list[str] = []

    def decode_part(part: Message) -> str:
        payload = part.get_payload(decode=True)
        if payload is None:
            value = part.get_payload()
            return value if isinstance(value, str) else ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = (part.get_content_disposition() or "").lower()
            filename = part.get_filename()
            content_type = part.get_content_type()
            if disposition == "attachment" or filename:
                payload = part.get_payload(decode=True)
                attachments.append(
                    {
                        "filename": decode_mime(filename) if filename else "",
                        "content_type": content_type,
                        "size": len(payload or b""),
                    }
                )
                continue
            if content_type == "text/plain":
                plain_parts.append(decode_part(part))
            elif content_type == "text/html":
                html_parts.append(decode_part(part))
    else:
        if msg.get_content_type() == "text/html":
            html_parts.append(decode_part(msg))
        else:
            plain_parts.append(decode_part(msg))

    if plain_parts:
        body = "\n\n".join(part.strip() for part in plain_parts if part.strip())
    else:
        extractor = HTMLTextExtractor()
        extractor.feed("\n".join(html_parts))
        body = extractor.text()

    if len(body) > max_chars:
        body = body[:max_chars] + "\n[truncated]"
    return body, attachments


def fetch_full_message(conn: imaplib.IMAP4, uid: str, peek: bool = True) -> Message:
    macro = "BODY.PEEK[]" if peek else "RFC822"
    typ, data = conn.uid("fetch", uid.encode("utf-8"), f"({macro})")
    if typ != "OK":
        raise RuntimeError(f"Fetch failed for UID {uid}: {data!r}")
    for item in data:
        if isinstance(item, tuple):
            return email.message_from_bytes(item[1])
    raise RuntimeError(f"No message body returned for UID {uid}.")


def cmd_init_config(args: argparse.Namespace) -> None:
    payload = sample_config()
    if args.print_only:
        print_json(payload)
        return
    path = config_path()
    if path.exists() and not args.force:
        fail(f"Config already exists at {path}. Use --force to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_json({"ok": True, "path": str(path), "next": "Edit config and set credential env vars."})


def cmd_check_config(args: argparse.Namespace) -> None:
    try:
        account_name, account = load_config(args.account)
        imap_settings = section(account, "imap")
        smtp_settings = section(account, "smtp")
        credential(imap_settings, "user")
        credential(imap_settings, "password")
        credential(smtp_settings, "user", required=False)
        credential(smtp_settings, "password", required=False)
        result: dict[str, Any] = {
            "ok": True,
            "account": account_name,
            "config": str(config_path()),
            "imap_host": imap_settings.get("host"),
            "smtp_host": smtp_settings.get("host"),
            "connect": {},
        }
        if args.connect:
            conn = imap_connect(account, readonly=True)
            conn.logout()
            result["connect"]["imap"] = "ok"
            smtp = smtp_connect(account)
            smtp.quit()
            result["connect"]["smtp"] = "ok"
        print_json(result)
    except Exception as exc:
        fail(str(exc))


def cmd_list(args: argparse.Namespace) -> None:
    try:
        account_name, account = load_config(args.account)
        conn = imap_connect(account, readonly=True)
        criteria = search_criteria(args)
        typ, data = conn.uid("search", None, *criteria)
        if typ != "OK":
            raise RuntimeError(f"Search failed: {data!r}")
        uids = data[0].split() if data and data[0] else []
        selected = uids[-args.limit :] if args.limit else uids
        messages = []
        for uid in reversed(selected):
            msg, flags = fetch_header(conn, uid)
            messages.append(message_summary(uid.decode("utf-8"), msg, flags))
        conn.logout()
        print_json(
            {
                "ok": True,
                "account": account_name,
                "criteria": criteria,
                "count": len(uids),
                "returned": len(messages),
                "messages": messages,
            }
        )
    except Exception as exc:
        fail(str(exc))


def cmd_show(args: argparse.Namespace) -> None:
    try:
        account_name, account = load_config(args.account)
        conn = imap_connect(account, readonly=not args.mark_read)
        msg = fetch_full_message(conn, args.uid, peek=not args.mark_read)
        body, attachments = extract_body(msg, args.max_body_chars)
        conn.logout()
        summary = message_summary(args.uid, msg)
        summary.update({"body": body, "attachments": attachments})
        print_json({"ok": True, "account": account_name, "message": summary})
    except Exception as exc:
        fail(str(exc))


def read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        return Path(args.body_file).expanduser().read_text(encoding="utf-8")
    if args.body is not None:
        return args.body
    raise ConfigError("Provide --body or --body-file.")


def split_addresses(values: list[str] | None) -> list[str]:
    if not values:
        return []
    parsed: list[str] = []
    for value in values:
        parsed.extend(addr for _name, addr in getaddresses([value]) if addr)
    return parsed


def reply_headers(account: dict[str, Any], uid: str) -> dict[str, str]:
    conn = imap_connect(account, readonly=True)
    try:
        msg = fetch_full_message(conn, uid, peek=True)
    finally:
        conn.logout()
    subject = decode_mime(msg.get("Subject"))
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    refs = " ".join(
        item
        for item in [msg.get("References", ""), msg.get("Message-ID", "")]
        if item
    ).strip()
    return {
        "to": decode_mime(msg.get("From")),
        "subject": subject,
        "in_reply_to": msg.get("Message-ID", ""),
        "references": refs,
    }


def build_message(args: argparse.Namespace, account: dict[str, Any]) -> EmailMessage:
    smtp_settings = section(account, "smtp")
    reply = reply_headers(account, args.reply_to_uid) if args.reply_to_uid else {}
    body = read_body(args)
    to_addrs = split_addresses(args.to) or parse_addresses(reply.get("to"))
    cc_addrs = split_addresses(args.cc)
    bcc_addrs = split_addresses(args.bcc)
    subject = args.subject or reply.get("subject")
    from_addr = args.from_addr or account.get("from") or smtp_settings.get("from")

    if not from_addr:
        user = credential(smtp_settings, "user", required=False)
        from_addr = user
    if not from_addr:
        raise ConfigError("Missing From address. Set account.from or pass --from.")
    if not to_addrs:
        raise ConfigError("Missing recipient. Pass --to or use --reply-to-uid.")
    if not subject:
        raise ConfigError("Missing subject. Pass --subject.")

    msg = EmailMessage()
    msg["From"] = str(from_addr)
    msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)
    if bcc_addrs:
        msg["Bcc"] = ", ".join(bcc_addrs)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    if reply.get("in_reply_to"):
        msg["In-Reply-To"] = reply["in_reply_to"]
    if reply.get("references"):
        msg["References"] = reply["references"]
    msg.set_content(body)
    return msg


def message_preview(msg: EmailMessage) -> dict[str, Any]:
    return {
        "from": msg.get("From", ""),
        "to": parse_addresses(msg.get("To")),
        "cc": parse_addresses(msg.get("Cc")),
        "bcc": parse_addresses(msg.get("Bcc")),
        "subject": msg.get("Subject", ""),
        "body": msg.get_content(),
        "headers": {
            "message_id": msg.get("Message-ID", ""),
            "in_reply_to": msg.get("In-Reply-To", ""),
            "references": msg.get("References", ""),
        },
    }


def cmd_send(args: argparse.Namespace) -> None:
    try:
        account_name, account = load_config(args.account)
        msg = build_message(args, account)
        preview = message_preview(msg)
        if not args.yes_send:
            print_json(
                {
                    "ok": True,
                    "account": account_name,
                    "status": "dry-run",
                    "message": preview,
                    "next": "After explicit user approval, rerun with --yes-send.",
                }
            )
            return

        recipients = preview["to"] + preview["cc"] + preview["bcc"]
        clean_msg = EmailMessage()
        for key, value in msg.items():
            if key.lower() != "bcc":
                clean_msg[key] = value
        clean_msg.set_content(msg.get_content())
        smtp = smtp_connect(account)
        try:
            smtp.send_message(clean_msg, to_addrs=recipients)
        finally:
            smtp.quit()
        print_json({"ok": True, "account": account_name, "status": "sent", "message": preview})
    except Exception as exc:
        fail(str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Email Manager IMAP/SMTP helper")
    parser.add_argument("--config", help="Override EMAIL_MANAGER_CONFIG")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-config", help="Create a sample config")
    init.add_argument("--print", dest="print_only", action="store_true", help="Print sample JSON")
    init.add_argument("--force", action="store_true", help="Overwrite existing config")
    init.set_defaults(func=cmd_init_config)

    check = sub.add_parser("check-config", help="Validate config and env vars")
    check.add_argument("--account")
    check.add_argument("--connect", action="store_true", help="Test live IMAP/SMTP login")
    check.set_defaults(func=cmd_check_config)

    list_cmd = sub.add_parser("list", help="List message headers")
    list_cmd.add_argument("--account")
    list_cmd.add_argument("--limit", type=int, default=10)
    list_cmd.add_argument("--unread", action="store_true")
    list_cmd.add_argument("--since", help="YYYY-MM-DD")
    list_cmd.add_argument("--from", dest="sender")
    list_cmd.add_argument("--subject")
    list_cmd.add_argument("--raw", nargs="*", help="Additional raw IMAP SEARCH tokens")
    list_cmd.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="Show one message by UID")
    show.add_argument("uid")
    show.add_argument("--account")
    show.add_argument("--max-body-chars", type=int, default=8000)
    show.add_argument("--mark-read", action="store_true")
    show.set_defaults(func=cmd_show)

    send = sub.add_parser("send", help="Draft or send an email")
    send.add_argument("--account")
    send.add_argument("--from", dest="from_addr")
    send.add_argument("--to", action="append")
    send.add_argument("--cc", action="append")
    send.add_argument("--bcc", action="append")
    send.add_argument("--subject")
    send.add_argument("--body")
    send.add_argument("--body-file")
    send.add_argument("--reply-to-uid")
    send.add_argument("--yes-send", action="store_true", help="Actually send the email")
    send.set_defaults(func=cmd_send)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.config:
        os.environ["EMAIL_MANAGER_CONFIG"] = args.config
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except ConfigError as exc:
        fail(str(exc))
    except KeyboardInterrupt:
        fail("Interrupted.", code=130)
