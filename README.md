# email-manager

> Ler, buscar, resumir, preparar respostas e enviar emails via IMAP/SMTP com confirmacao explicita antes de envio.

## O que faz

- Lista emails por IMAP, incluindo nao lidos e filtros por remetente, assunto ou data.
- Mostra mensagens por UID sem marcar como lidas por padrao.
- Prepara respostas encadeadas e rascunhos de envio com dry-run.
- Envia email por SMTP somente depois de confirmacao explicita usando `--yes-send`.
- Inclui wizard passo a passo para criar o config IMAP/SMTP sem salvar senha.

## Pre-requisitos

| Requisito | Como configurar |
|-----------|----------------|
| Python 3 | Ja disponivel no container OpenClaw |
| Conta IMAP/SMTP | Configurar `~/.openclaw/state/email-manager/config.json` |
| Credenciais | Definir variaveis como `EMAIL_MAIN_USER` e `EMAIL_MAIN_PASSWORD` |

## Wizard De Configuracao

Rode:

```bash
python3 ~/.openclaw/skills/email-manager/scripts/configure_wizard.py
```

O wizard pergunta uma informacao por vez:

1. nome da conta;
2. provedor (`gmail`, `outlook` ou `custom`);
3. email/login;
4. nome do remetente;
5. prefixo das variaveis de ambiente;
6. mailbox IMAP;
7. hosts e portas apenas se o provedor for `custom`.

Ele grava `~/.openclaw/state/email-manager/config.json` e mostra os `export` necessarios. Ele nao pede nem salva senha.

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
│   ├── configure_wizard.py
│   └── email_cli.py
└── references/
    └── config.md
```

## Validacao

```bash
python3 tests/wizard_functional_test.py
python3 tests/local_functional_test.py
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
| 0.2.0 | 2026-05-15 | Adiciona wizard passo a passo para configuracao IMAP/SMTP |
| 0.1.0 | 2026-05-15 | Release inicial local com IMAP/SMTP, dry-run e config por env vars |

## Licenca

Proprietary — uso restrito ao platform QuickClaw. Ver LICENSE.
