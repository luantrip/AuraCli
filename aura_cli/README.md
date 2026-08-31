# ◈ aura_cli — Pacote Principal

Pacote Python do Aura CLI. Orquestra a interação entre interface, agentes autônomos e serviços de performance.

## Estrutura Interna

- **`cli/`** — Interface de linha de comando (Rich).
  - `main.py` — Entry point do comando `aura` (Typer).
  - `app_loop.py` — Loop principal da sessão interativa.
  - `command_processor.py` — Roteamento de comandos slash.
  - `commands/` — Implementação dos comandos (`/agi`, `/ops`, `/session`, etc.).
  - `workers/` — Workers assíncronos (`agi_worker`, `ops_worker`, `tester_worker`).
  - `ui/` — Componentes de renderização Rich (temas, componentes, chat).

- **`tui/`** — Interface gráfica TUI (Textual).
  - `app.py` — Aplicação Textual principal.
  - `widgets/` — widgets Textual customizados.
  - `screens/` — Telas modulares (history, context, tools).
  - `tools/` — Ferramentas embarcadas (AuraPaint, File Manager, Monitor).

- **`core/`** — Lógica central e serviços.
  - `llm/` — Integração multi-provider via LiteLLM.
  - `agents/` — Orquestrador, workers e agentes especializados.
  - `personas/` — Skills e personas dos agentes (ex-`consciousness/`).
  - `tools/` — catálogo extensível de ferramentas (fs, git, shell, web, docker…).
  - `memory/` — Memória persistente, notebook, vector store.
  - `sessions/` — Gerenciamento de sessões e estado.

- **`adk/`** — Agent Development Kit (ADK).
  - Infraestrutura para agentes nativos com métricas e memória ADK.

## Como Executar

### Modo Interativo (padrão)

```bash
aura           # Inicia o shell interativo
/tui           # Abre a interface TUI dentro do shell
```

### Modo Chat Direto

```bash
aura chat "Como listar arquivos em Python?"
```

### Retomar sessões

```bash
aura --resume <id-ou-prefixo>
/resume <id-ou-prefixo-ou-nome>
```
