# email-manager

> Ler, buscar, resumir, preparar respostas e enviar emails via IMAP/SMTP com confirmacao explicita antes de envio.

## O que faz

- Lista emails por IMAP, incluindo nao lidos e filtros por remetente, assunto ou data.
- Mostra mensagens por UID sem marcar como lidas por padrao.
- Prepara respostas encadeadas e rascunhos de envio com dry-run.
- Envia email por SMTP somente depois de confirmacao explicita usando `--yes-send`.

## Pre-requisitos

| Requisito | Como configurar |
|-----------|----------------|
| Python 3 | Ja disponivel no container OpenClaw |
| Conta IMAP/SMTP | Configurar `~/.openclaw/state/email-manager/config.json` |
| Credenciais | Definir variaveis como `EMAIL_MAIN_USER` e `EMAIL_MAIN_PASSWORD` |

## Exemplos de Uso

### Triar nao lidos

**Usuario:** "Veja meus emails nao lidos."

**Bot:** Lista UIDs, remetentes, assuntos, datas, resumo curto e proxima acao sugerida.

### Responder com seguranca

**Usuario:** "Responda o email 12345 confirmando a reuniao."

**Bot:** Gera um dry-run da resposta, mostra destinatario, assunto e corpo, e pede aprovacao explicita antes de enviar.

## Estrutura

```text
email-manager/
├── SKILL.md
├── skill.json
├── README.md
├── LICENSE
├── scripts/
│   └── email_cli.py
└── references/
    └── config.md
```

## Instalacao

Instalada automaticamente via plataforma QuickClaw.

Para instalacao manual:

```bash
openclaw skills install email-manager
```

## Changelog

| Versao | Data | Mudanca |
|--------|------|---------|
| 0.1.0 | 2026-05-15 | Release inicial local com IMAP/SMTP, dry-run e config por env vars |

## Licenca

Proprietary — uso restrito ao platform QuickClaw. Ver LICENSE.
