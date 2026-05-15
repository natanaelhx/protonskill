---
name: protonskill
description: >
  Ler, buscar, resumir e enviar emails do Proton Mail via Proton Mail Bridge
  usando IMAP/SMTP local e um wizard de configuracao passo a passo. Use quando o
  usuario pedir Proton Mail, Proton Bridge, caixa de entrada, emails nao lidos,
  busca, resumo, follow-up, rascunho, envio de email ou configuracao IMAP/SMTP.
  Keywords: Proton Mail, Proton Bridge, protonskill, email, inbox, wizard, IMAP,
  SMTP, responder, enviar email, unread, nao lidos
---

# Protonskill

Use esta skill para operar Proton Mail por meio do Proton Mail Bridge local. A skill usa o helper `scripts/email_cli.py` para IMAP/SMTP, cobre leitura, busca, resumo, preparacao de respostas e envio controlado.

Proton Mail nao deve ser acessado diretamente por IMAP/SMTP remoto. Use Proton Mail Bridge rodando na mesma maquina do OpenClaw/Zeus, com as credenciais IMAP/SMTP geradas pelo Bridge. As portas padrao do Bridge sao IMAP `1143` e SMTP `1025`, mas o usuario pode alterar no Bridge.

## Quick Start

Skill path:

```text
~/.openclaw/skills/protonskill
```

1. Se a configuracao ainda nao existir, rode o wizard:

```bash
python3 ~/.openclaw/skills/protonskill/scripts/configure_wizard.py
```

2. Defina as variaveis de ambiente que o wizard mostrar.
3. Valide a conta:

```bash
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py check-config --connect
```

4. Use sempre a CLI local para interagir com emails:

```bash
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py check-config
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py list --unread --limit 10
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py show <uid>
```

## Workflow

### 1. Rodar Wizard De Configuracao

Quando o usuario pedir para configurar Proton Mail, conduza o passo a passo com `scripts/configure_wizard.py`. O wizard pergunta uma informacao por vez:

- nome da conta;
- provedor, com `proton-bridge` como padrao;
- email/remetente;
- nome do remetente;
- nomes das variaveis de ambiente;
- host/porta/SSL do Bridge, com defaults `127.0.0.1:1143` e `127.0.0.1:1025`;
- mailbox IMAP.

O wizard nunca pede nem grava a senha. Ele grava apenas host, porta, remetente e nomes de env vars em `~/.openclaw/state/protonskill/config.json`.

### 2. Verificar Configuracao

Rode `check-config` antes de acessar a caixa. Se faltar config ou variavel de ambiente, explique ao usuario exatamente o que falta e aponte `references/config.md`.

```bash
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py check-config --account proton
```

### 3. Ler E Buscar Emails

Para triagem, comece por uma lista pequena e depois abra apenas os UIDs relevantes:

```bash
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py list --unread --limit 20
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py list --from pessoa@exemplo.com --limit 10
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py list --subject "invoice" --limit 10
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py show 12345 --max-body-chars 6000
```

Ao responder ao usuario, inclua `uid`, remetente, assunto e data para cada email citado. Resuma conteudo longo antes de colar texto completo.

### 4. Preparar Respostas

Quando o usuario pedir para responder, primeiro mostre um rascunho com destinatarios, assunto e corpo. Para respostas encadeadas, use `--reply-to-uid` no dry-run:

```bash
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py send \
  --reply-to-uid 12345 \
  --body-file /tmp/email-reply.txt
```

### 5. Enviar Emails

Envio e uma acao externa. Nunca envie sem confirmacao explicita do usuario no turno atual depois de mostrar o rascunho final.

Fluxo obrigatorio:

- Preparar o rascunho.
- Rodar `send` sem `--yes-send` para dry-run.
- Mostrar destinatarios, cc/bcc, assunto e corpo final ao usuario.
- So depois de aprovacao explicita, repetir o comando com `--yes-send`.

```bash
python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py send \
  --to pessoa@exemplo.com \
  --subject "Follow-up" \
  --body-file /tmp/email-body.txt

python3 ~/.openclaw/skills/protonskill/scripts/email_cli.py send \
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
- Para Proton Mail, exigir Proton Mail Bridge instalado, logado e rodando. Nao tentar conectar direto nos servidores Proton por IMAP/SMTP.
- Usar a senha IMAP/SMTP gerada pelo Bridge, nao a senha normal da conta Proton.
- Se o Bridge mudou as portas padrao, usar exatamente as portas exibidas em Bridge settings.

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
- `scripts/configure_wizard.py`: wizard interativo para criar o config Proton Bridge.
- `references/config.md`: formato de configuracao, variaveis de ambiente e notas do Proton Bridge.
