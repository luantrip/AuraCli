# Aura CLI — Test Suite

Suite de testes automatizados do Aura CLI. A suíte reúne testes unitários, e2e e de integração entre
`unit`, `e2e` e `integration`. O gate offline (`tests/unit` + `tests/e2e`) roda sem
rede, Docker, providers reais nem binários Nim nativos.

## Estrutura

```
tests/
├── unit/                   # Testes unitários (isolados, rápidos)
│   ├── adk/                # ADK agents e memory
│   ├── agents/             # Workers AGI/Ops
│   ├── cli/                # Comandos slash, UI Rich, workers
│   │   ├── commands/
│   │   ├── ui/components/
│   │   └── workers/
│   ├── core/               # Lógica central
│   │   ├── agents/         # Orquestrador, planning, tool_calling
│   │   ├── agi/            # Factory, execution, validation
│   │   ├── consciousness/  # Personas/skills (tests em core/personas)
│   │   ├── extensions/     # Loader, registry, hooks
│   │   ├── llm/            # Base, model_profiles, rate_limiter, task_router
│   │   ├── memory/         # ConversationMemory, notebook, constitution
│   │   ├── ops_tools/      # Git, DB, infra, CI/CD, monitoramento, segurança
│   │   ├── quality/        # Análise de código
│   │   ├── refactoring/    # Executor incremental
│   │   ├── sessions/       # Session manager
│   │   ├── tools/          # File system, shell, git, web, pintura
│   │   └── ...             # 30+ módulos adicionais
│   ├── tui/                # TUI Textual — widgets, screens, bridge
│   ├── ui/                 # Testes de componentes Rich
│   └── services/           # Serviços transversais
├── integration/            # Testes de integração (cross-module)
├── e2e/                    # Testes end-to-end (cenários completos)
└── conftest.py             # Fixtures globais
```

## Executar

```bash
# Gate offline recomendado (unit + e2e, sem rede/Docker/Nim nativo)
pytest -q -rs tests/unit tests/e2e

# Módulo específico
pytest tests/unit/core/memory/

# Com output detalhado
pytest tests/unit/core/llm/ -v

# Apenas falhas rápidas
pytest tests/unit/ -x -q
```

> Use o interpretador do ambiente do projeto (`.venv/bin/python -m pytest ...`).
> O `conftest.py` configura mocks (tiktoken, litellm), isolamento de artefatos e
> `pytest-timeout`; rodar fora do venv pode travar em I/O de rede ou prompts.

## Convenções

- Testes unitários não devem fazer I/O real — usar `tmp_path` ou `monkeypatch`
- Testes que requerem variáveis de ambiente (API keys) usam `pytest.mark.skipif`
- Testes de contrato Nim exigem o binário nativo correspondente à plataforma; sem o
  build local eles falham/skip conforme o formato validado pelo runtime

## Configuração

`pyproject.toml` contém a configuração do pytest (`[tool.pytest.ini_options]`). Fixtures compartilhadas estão em `conftest.py` na raiz do projeto e em `tests/conftest.py`.
