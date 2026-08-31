# Release gate operacional

Este checklist separa evidência automatizada de validações que exigem um
ambiente interativo ou serviços externos. Um resultado `MANUAL` não deve ser
convertido em `PASS` por conveniência.

## Gate automatizado

Execute a partir da raiz do projeto:

```bash
.venv/bin/python scripts/operational_release_gate.py --json
.venv/bin/python scripts/check_docs.py
.venv/bin/ruff check aura_cli tests
.venv/bin/pytest -q
python -m build --wheel --outdir /tmp/aura-cli-wheel
```

Registre a contagem de testes, warnings, código de saída e o nome do wheel.
Inspecione o wheel e confirme que ele não contém estudos, caches, logs, bytecode
ou testes.

## Gate interativo

Use um terminal real, não apenas um snapshot headless:

```bash
TERM=xterm-256color .venv/bin/python scripts/operational_release_gate.py --json
```

Com o leitor de tela nativo configurado, defina `AURA_SCREEN_READER` para o
comando disponível no ambiente e repita o gate. Durante a sessão, registre:

- foco inicial, mudança de foco e retorno ao composer;
- streaming, aprovação, cancelamento, erro e conclusão;
- resize estreito, terminal sem cor e navegação por teclado;
- leitura dos estados por VoiceOver, NVDA, Orca ou leitor equivalente, quando o
  dispositivo compatível estiver configurado para validação manual.

O script valida a disponibilidade do executável; a observação do foco falado e
da navegação continua sendo responsabilidade do operador.

## Integrações externas

Em ambiente controlado, com credenciais próprias e sem tools mutantes:

1. execute uma completion mínima por provider habilitado;
2. injete timeout, erro transitório e resposta inválida na fronteira HTTP;
3. confirme retry limitado, fallback, redaction e estado terminal;
4. repita o cenário após troca de sessão, perfil e diretório de trabalho;
5. anexe comandos, timestamps, provider/modelo e resultado sem registrar chaves.

Falhas de serviço externo devem ser classificadas como `FAIL`, não ocultadas
como `MANUAL`. A validação física de acessibilidade é opcional e específica do
dispositivo; ela não inicia automaticamente e não bloqueia o fluxo padrão. Os
gates externos continuam exigindo registro ou aceitação formal pelo responsável.
