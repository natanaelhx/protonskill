# protonskill

> Ler, buscar, resumir, preparar respostas e enviar emails do Proton Mail via Proton Mail Bridge local.

## O que faz

- Configura Proton Mail Bridge via wizard passo a passo.
- Lista emails por IMAP local, incluindo nao lidos e filtros por remetente, assunto ou data.
- Mostra mensagens por UID sem marcar como lidas por padrao.
- Prepara respostas encadeadas e rascunhos de envio com dry-run.
- Envia email por SMTP somente depois de confirmacao explicita usando `--yes-send`.
- Nao salva senha no arquivo de configuracao.

## Pre-requisitos

| Requisito | Como configurar |
|-----------|----------------|
| Python 3 | Ja disponivel no container OpenClaw |
| Proton Mail Bridge | Instalar, logar e deixar rodando localmente |
| Conta Proton Mail paga | Bridge e necessario para IMAP/SMTP do Proton Mail |
| Config local | Criar `~/.openclaw/state/protonskill/config.json` pelo wizard |
| Credenciais Bridge | Definir variaveis como `EMAIL_PROTON_USER` e `EMAIL_PROTON_PASSWORD` |

## Wizard De Configuracao

Rode:

```bash
python3 ~/.openclaw/skills/protonskill/scripts/configure_wizard.py
```

O wizard pergunta uma informacao por vez:

1. nome da conta;
2. provedor, com `proton-bridge` como padrao;
3. email/remetente;
4. nome do remetente;
5. prefixo das variaveis de ambiente;
6. host e porta IMAP do Bridge;
7. host e porta SMTP do Bridge;
8. mailbox IMAP.

Ele grava `~/.openclaw/state/protonskill/config.json` e mostra os `export` necessarios. Ele nao pede nem salva senha.

Defaults do Proton Mail Bridge:

- IMAP: `127.0.0.1:1143`
- SMTP: `127.0.0.1:1025`

## Exemplos de Uso

### Triar nao lidos

**Usuario:** "Veja meus emails nao lidos no Proton."

**Bot:** Lista UIDs, remetentes, assuntos, datas, resumo curto e proxima acao sugerida.

### Responder com seguranca

**Usuario:** "Responda o email 12345 confirmando a reuniao."

**Bot:** Gera um dry-run da resposta, mostra destinatario, assunto e corpo, e pede aprovacao explicita antes de enviar.

## Estrutura

```text
protonskill/
├── SKILL.md
├── skill.json
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
openclaw skills install protonskill
```

## Changelog

| Versao | Data | Mudanca |
|--------|------|---------|
| 0.3.0 | 2026-05-15 | Alinha nome da skill ao repo e foca Proton Mail Bridge |
| 0.2.0 | 2026-05-15 | Adiciona wizard passo a passo para configuracao IMAP/SMTP |
| 0.1.0 | 2026-05-15 | Release inicial local com IMAP/SMTP, dry-run e config por env vars |

## Licenca

Proprietary — uso restrito ao platform QuickClaw. Ver LICENSE.
