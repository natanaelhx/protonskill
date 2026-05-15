# Email Manager Configuration

The helper reads account settings from:

```text
~/.openclaw/state/email-manager/config.json
```

Override this path with `EMAIL_MANAGER_CONFIG=/path/to/config.json`.
The CLI also accepts `--config /path/to/config.json` before the subcommand.

## Create A Sample Config

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py init-config --print
```

To write the sample file:

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py init-config
```

## Config Shape

Store hostnames and environment variable names in JSON. Do not store passwords in JSON.

```json
{
  "default_account": "main",
  "accounts": {
    "main": {
      "from": "Your Name <you@example.com>",
      "imap": {
        "host": "imap.example.com",
        "port": 993,
        "ssl": true,
        "mailbox": "INBOX",
        "user_env": "EMAIL_MAIN_USER",
        "password_env": "EMAIL_MAIN_PASSWORD"
      },
      "smtp": {
        "host": "smtp.example.com",
        "port": 465,
        "ssl": true,
        "starttls": false,
        "user_env": "EMAIL_MAIN_USER",
        "password_env": "EMAIL_MAIN_PASSWORD"
      }
    }
  }
}
```

Set credentials in the shell or OpenClaw secret environment, for example:

```bash
export EMAIL_MAIN_USER="you@example.com"
export EMAIL_MAIN_PASSWORD="provider-app-password"
```

## Common Providers

Gmail:

- IMAP host: `imap.gmail.com`, port `993`, SSL `true`
- SMTP host: `smtp.gmail.com`, port `465`, SSL `true`
- Use an app password for accounts with 2-Step Verification.

Outlook / Microsoft 365:

- IMAP host: `outlook.office365.com`, port `993`, SSL `true`
- SMTP host: `smtp.office365.com`, port `587`, SSL `false`, STARTTLS `true`
- Some tenants require OAuth and will reject password auth.

Generic IMAP/SMTP:

- Prefer IMAP over SSL on port `993`.
- Prefer SMTP SSL on port `465` or STARTTLS on port `587`.
- Confirm whether the SMTP username differs from the IMAP username.

## Validation

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py check-config
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py check-config --connect
```

`--connect` performs real IMAP/SMTP login checks. Use it only when the user expects a live account test.
