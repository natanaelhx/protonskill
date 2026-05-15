#!/usr/bin/env python3
"""Interactive setup wizard for the protonskill skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("~/.openclaw/state/protonskill/config.json").expanduser()

PROVIDERS: dict[str, dict[str, Any]] = {
    "proton-bridge": {
        "imap": {"host": "127.0.0.1", "port": 1143, "ssl": False, "mailbox": "INBOX"},
        "smtp": {"host": "127.0.0.1", "port": 1025, "ssl": False, "starttls": False},
        "note": "Requer Proton Mail Bridge rodando localmente e credenciais geradas pelo Bridge.",
    },
    "gmail": {
        "imap": {"host": "imap.gmail.com", "port": 993, "ssl": True, "mailbox": "INBOX"},
        "smtp": {"host": "smtp.gmail.com", "port": 465, "ssl": True, "starttls": False},
        "note": "Use uma App Password do Google, nao a senha normal da conta.",
    },
    "outlook": {
        "imap": {"host": "outlook.office365.com", "port": 993, "ssl": True, "mailbox": "INBOX"},
        "smtp": {"host": "smtp.office365.com", "port": 587, "ssl": False, "starttls": True},
        "note": "Alguns tenants Microsoft exigem OAuth e rejeitam senha/app password.",
    },
    "custom": {
        "imap": {"host": "", "port": 993, "ssl": True, "mailbox": "INBOX"},
        "smtp": {"host": "", "port": 465, "ssl": True, "starttls": False},
        "note": "Use os hosts IMAP/SMTP do seu provedor.",
    },
}


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def prompt_bool(label: str, default: bool = True) -> bool:
    default_text = "s" if default else "n"
    value = prompt(label, default_text).lower()
    return value in {"s", "sim", "y", "yes", "true", "1"}


def prompt_int(label: str, default: int) -> int:
    while True:
        value = prompt(label, str(default))
        try:
            return int(value)
        except ValueError:
            print("Valor invalido. Digite um numero.")


def env_prefix(account: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", account).strip("_").upper()
    return f"EMAIL_{normalized or 'MAIN'}"


def account_slug(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")
    return slug or "main"


def build_config() -> tuple[dict[str, Any], str, str]:
    print("Wizard Protonskill")
    print("Este wizard cria o config do Proton Mail Bridge sem salvar senha no arquivo.")
    print()

    account = account_slug(prompt("1. Nome da conta 🧩", "proton"))
    provider = prompt("2. Provedor 📬 (proton-bridge/gmail/outlook/custom)", "proton-bridge").lower()
    if provider not in PROVIDERS:
        provider = "custom"
    template = json.loads(json.dumps(PROVIDERS[provider]))

    if template.get("note"):
        print(f"Nota: {template['note']}")
    email_addr = prompt("3. Email/remetente ✉️")
    display_name = prompt("4. Nome do remetente 👤", email_addr)
    prefix = prompt("5. Prefixo das env vars 🔐", env_prefix(account)).upper()
    user_env = f"{prefix}_USER"
    password_env = f"{prefix}_PASSWORD"

    imap = template["imap"]
    smtp = template["smtp"]
    step = 6
    if provider in {"custom", "proton-bridge"}:
        imap["host"] = prompt(f"{step}. Host IMAP 📥", imap["host"] or "imap.example.com")
        step += 1
        imap["port"] = prompt_int(f"{step}. Porta IMAP 🔌", int(imap["port"]))
        step += 1
        imap["ssl"] = prompt_bool(f"{step}. IMAP usa SSL? 🔒", bool(imap["ssl"]))
        step += 1
        smtp["host"] = prompt(f"{step}. Host SMTP 📤", smtp["host"] or "smtp.example.com")
        step += 1
        smtp["port"] = prompt_int(f"{step}. Porta SMTP 🔌", int(smtp["port"]))
        step += 1
        smtp["ssl"] = prompt_bool(f"{step}. SMTP usa SSL direto? 🔒", bool(smtp["ssl"]))
        step += 1
        smtp["starttls"] = prompt_bool(f"{step}. SMTP usa STARTTLS? 🔐", bool(smtp["starttls"]))
        step += 1
    mailbox = prompt(f"{step}. Mailbox IMAP 📂", str(imap.get("mailbox") or "INBOX"))
    imap["mailbox"] = mailbox

    imap["user_env"] = user_env
    imap["password_env"] = password_env
    smtp["user_env"] = user_env
    smtp["password_env"] = password_env

    config = {
        "default_account": account,
        "accounts": {
            account: {
                "from": f"{display_name} <{email_addr}>",
                "imap": imap,
                "smtp": smtp,
            }
        },
    }
    return config, user_env, password_env


def main() -> None:
    parser = argparse.ArgumentParser(description="Email Manager setup wizard")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Config path to write")
    parser.add_argument("--force", action="store_true", help="Overwrite without asking")
    args = parser.parse_args()

    path = Path(args.config).expanduser()
    config, user_env, password_env = build_config()

    if path.exists() and not args.force:
        if not prompt_bool(f"Config ja existe em {path}. Sobrescrever? ⚠️", False):
            print("Cancelado. Nenhum arquivo foi alterado.")
            return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"Config gravado em: {path}")
    print("Agora defina as credenciais no ambiente antes de usar a skill:")
    print(f'export {user_env}="seu-email@exemplo.com"')
    print(f'export {password_env}="senha-gerada-pelo-proton-bridge"')
    print()
    print("Depois valide com:")
    print("python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py check-config --connect")


if __name__ == "__main__":
    main()
