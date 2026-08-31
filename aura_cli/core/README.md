# 🧠 Aura Core

O módulo `core` é o motor do Aura CLI — conecta LLMs, memória, ferramentas e agentes.

## Sistemas Principais

### LLM (`llm/`)
Multi-provider via **LiteLLM** com fallback automático entre providers.
- `base.py` — cliente unificado, `query_with_fallback()`
- `model_profiles.py` — perfis por tipo de tarefa
- `task_router.py` — seleção automática de modelo por contexto
- `rate_limiter.py` — controle de taxa e circuit breaker
- Providers: Google Gemini, Cerebras, Groq, OpenRouter, OpenAI, Anthropic, NVIDIA

### Configuração (`config.py`)
Gestão de configurações com **Pydantic** (`AppSettings`, `ConfigCompat`).
- Armazenamento seguro de API keys em `~/.aura/config.json`
- Migração automática de formatos antigos

### Memória (`memory/`)
- `memory_service.py` — serviço central com suporte a SQLite
- `notebook_service.py` — páginas de memória longa por sessão em `.aura/notebooks/`
- `vector_store.py` — busca semântica com **fastembed** (fallback keyword-based)
- `constitution_template.py` — constituição do projeto com regras aprendidas

### Personas e Skills (`personas/`)
Sistema de conhecimento e personas dos agentes (migrado de `consciousness/`).
- `skill_retriever.py` — recuperação semântica de skills (`.md` em `personas/skills/`)
- `agent_runner.py` — execução de agentes definidos em `personas/agents/*.md`
- `integrations.py` — `ConsciousnessManager` para injeção de contexto em prompts

### Ferramentas (`tools/` + `service_registry.py`)
Ferramentas registradas via `service_registry.py`, cobrindo:
- Sistema de arquivos, Git, shell, web search
- Docker, Kubernetes, CI/CD, segurança
- Análise de código, AST, codebase traversal
- Imaginação (arte ASCII/ANSI), pintura headless

### Agentes (`agents/`)
- `agent_base.py` — `AgentBase` com consciousness integration
- `agent_orchestrator.py` — orquestração multi-agente
- `adk_wrapper.py` — ponte entre sistema nativo e ADK
- `specialized_agents/` — `CodeAgent`, `RefactorAgent`, `ReviewAgent`, `OpsAgent`, `TestAgent`
- `planning/` — decomposição de problemas, executor paralelo, validador

### Extensões (`extensions/`)
Sistema de plugins com `ExtensionLoader`, `ExtensionRegistry` e `plugin_api.py`.
- Drop plugins `.py` em `extensions/` no projeto para carregamento automático

### Hooks (`hooks/`)
- `manager.py` — hooks de subprocess tipo Kiro (`HookEvent`: PreToolUse, PostToolUse…)
- `extension_hooks.py` — hooks de callback para extensões (`HookType`: BEFORE_TOOL_CALL…)

### Avaliação e confiabilidade (`evaluation/` e `reliability/`)

- `evaluation/` — agendamento durável, seleção de candidatos, métricas e relatórios.
- `reliability/` — retry com backoff, idempotência, perfis isolados e fault injection.

### Integrações nativas (`arena/`, `skills/` e `mcp/`)

- `arena/` — torneio de subagentes, strategy cards e rubric de julgamento.
- `skills/` — instalação, validação, empacotamento e busca de `.aura-skill`.
- `mcp/` — servidor MCP com adapters, autenticação e transports stdio/HTTP.

### Outros Módulos Notáveis
| Módulo | Função |
|--------|--------|
| `sessions/` | Gerenciamento de sessões e estado de projeto |
| `checkpoint/` | Git shadow repo para undo/redo |
| `tangent/` | Modo de exploração lateral sem poluir sessão principal |
| `todo/` | Rastreamento de tarefas em `.aura/to-do.md` |
| `quality/` | Análise de complexidade, dead code, duplicatas, segurança |
| `refactoring/` | Executor incremental com checkpoints automáticos |
| `context/` | `ProjectIndexer`, `CodeIndex`, `SentinelManager` |
| `ops_tools/` | Git avançado, Docker, K8s, CI/CD, DB, infra, segurança |
| `metrics/` | Bridge de observabilidade ADK ↔ stats legados |
| `agi/evidence_tree.py` | Contexto AGI materializado como evidências por tarefa |
| `sessions/external_*` | Descoberta e importação segura de sessões Grok/Codex |
