---
name: email-manager
description: >
  Ler, buscar, resumir e enviar emails por IMAP/SMTP usando uma CLI local segura.
  Use quando o usuario pedir caixa de entrada, emails nao lidos, busca de
  mensagens, resumo de conversas, follow-up, rascunho de resposta ou envio de
  email. Exige configuracao de conta e credenciais em variaveis de ambiente.
  Keywords: email, e-mail, inbox, caixa de entrada, unread, nao lidos, responder,
  reply, enviar email, send mail, IMAP, SMTP, Gmail, Outlook
---

# Email Manager

Use esta skill para operar email pessoal ou profissional por IMAP/SMTP com o helper local `scripts/email_cli.py`. A skill cobre leitura, busca, resumo, preparacao de respostas e envio controlado.

## Quick Start

Skill path:

```text
~/.openclaw/skills/email-manager
```

1. Se a configuracao ainda nao existir, leia `references/config.md`.
2. Crie ou valide `~/.openclaw/state/email-manager/config.json`.
3. Use sempre a CLI local para interagir com emails:

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py check-config
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py list --unread --limit 10
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py show <uid>
```

## Workflow

### 1. Verificar Configuracao

Rode `check-config` antes de acessar a caixa. Se faltar config ou variavel de ambiente, explique ao usuario exatamente o que falta e aponte `references/config.md`.

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py check-config --account main
```

### 2. Ler E Buscar Emails

Para triagem, comece por uma lista pequena e depois abra apenas os UIDs relevantes:

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py list --unread --limit 20
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py list --from pessoa@exemplo.com --limit 10
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py list --subject "invoice" --limit 10
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py show 12345 --max-body-chars 6000
```

Ao responder ao usuario, inclua `uid`, remetente, assunto e data para cada email citado. Resuma conteudo longo antes de colar texto completo.

### 3. Preparar Respostas

Quando o usuario pedir para responder, primeiro mostre um rascunho com destinatarios, assunto e corpo. Para respostas encadeadas, use `--reply-to-uid` no dry-run:

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py send \
  --reply-to-uid 12345 \
  --body-file /tmp/email-reply.txt
```

### 4. Enviar Emails

Envio e uma acao externa. Nunca envie sem confirmacao explicita do usuario no turno atual depois de mostrar o rascunho final.

Fluxo obrigatorio:

- Preparar o rascunho.
- Rodar `send` sem `--yes-send` para dry-run.
- Mostrar destinatarios, cc/bcc, assunto e corpo final ao usuario.
- So depois de aprovacao explicita, repetir o comando com `--yes-send`.

```bash
python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py send \
  --to pessoa@exemplo.com \
  --subject "Follow-up" \
  --body-file /tmp/email-body.txt

python3 ~/.openclaw/skills/email-manager/scripts/email_cli.py send \
  --to pessoa@exemplo.com \
  --subject "Follow-up" \
  --body-file /tmp/email-body.txt \
  --yes-send
```

Se a aprovacao for ambigua, incompleta ou antiga, peca confirmacao novamente. Nao envie emails em massa, anexos ou mensagens sensiveis sem revisar destinatarios e conteudo com cuidado extra.

## Regras De Seguranca

- Nunca imprimir senhas, tokens, app passwords ou conteudo de arquivos de credenciais.
- Nunca gravar segredos no `config.json`; use variaveis de ambiente.
- Usar `BODY.PEEK` para leitura sempre que possivel, evitando marcar mensagens como lidas.
- Tratar `bcc` como sensivel: nao repetir em resumo publico a menos que o usuario esteja revisando o envio.
- Para assuntos legais, medicos, financeiros ou trabalhistas, deixar claro quando o texto e um rascunho e pedir confirmacao antes de envio.
- Se a conta usar Gmail, Outlook ou provedor com MFA, orientar o usuario a configurar app password/OAuth compativel com IMAP/SMTP; a skill nao deve tentar contornar MFA.

## Formato De Resposta

Responda em PT-BR por padrao, de forma curta e operacional.

- Para triagem: listar prioridade, `uid`, remetente, assunto, data e proxima acao sugerida.
- Para busca: explicar o filtro usado e mostrar apenas os resultados relevantes.
- Para rascunho/envio: mostrar `Para`, `Cc`, `Bcc` quando houver, `Assunto` e corpo completo antes de pedir confirmacao.
- Para erro de configuracao: informar o arquivo ou variavel ausente e o comando de validacao.

## Exemplos

Usuario: "Veja meus emails nao lidos."

Resposta esperada: listar ate 10 mensagens nao lidas com `uid`, remetente, assunto, data e resumo de uma linha.

Usuario: "Responda o email 12345 dizendo que confirmo a reuniao."

Resposta esperada: gerar dry-run com destinatario e assunto encadeados, mostrar o corpo final e pedir aprovacao explicita antes de usar `--yes-send`.

## Recursos

- `scripts/email_cli.py`: CLI sem dependencias externas para IMAP/SMTP.
- `references/config.md`: formato de configuracao, variaveis de ambiente e exemplos por provedor.
