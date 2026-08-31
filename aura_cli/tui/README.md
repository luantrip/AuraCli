# 🌌 Aura TUI

Interface gráfica de terminal do Aura CLI, construída com **Textual**. Transforma o terminal em um ambiente interativo com chat, ferramentas embarcadas e navegação por teclado.

## Estrutura

```
tui/
├── app.py              # Aplicação Textual principal (AuraTUI)
├── bridge.py           # Bridge entre CLI workers e TUI (eventos assíncronos)
├── screens/            # Telas completas (history, context, tools menu, settings)
├── widgets/            # widgets Textual customizados
│   ├── chat.py         # AuraChatLog — renderizador de conversa com markdown
│   ├── status.py       # AuraStatusSidebar — sidebar de status e contexto
│   ├── settings_panel.py  # Painel de configurações e API keys
│   ├── memory_browser.py  # Explorador de memória e notebooks
│   ├── history/        # Navegador de sessões históricas
│   ├── constitution/   # Wizard de constituição do projeto
│   ├── diff/           # Painel de revisão de diffs
│   └── ...
├── tools/              # Ferramentas TUI embarcadas
│   ├── paint/          # AuraPaint: editor nativo ANSI/ASCII art
│   ├── file_manager/   # Gerenciador de arquivos
│   └── monitor/        # Browser de terminal (aura-monitor)
├── services/           # Serviços TUI (sync, session autosave)
├── keybinds/           # Configuração de atalhos (keybind_config.py)
├── routing/            # Detecção de modo e abertura de telas
├── styles/             # Temas CSS (*.tcss)
└── utils/              # Detecção de terminal, ícones, etc.
```

## Arquitetura

A TUI usa arquitetura reativa: widgets subscrevem a propriedades `reactive` e o Textual re-renderiza automaticamente quando o estado muda.

- **Entrada de usuário** → `AuraTUI.on_key` / `RichPromptInput` → `bridge.py` → workers CLI
- **Eventos de worker** → `status_queue` → `bridge.py` → eventos Textual → widgets atualizam
- **Telas** abertas via `open_screen(ScreenId.X)` — registro centralizado em `routing/`
- **Workspace diff** → `WorkspaceDiff` → `WorkspaceDiffPanel` para revisão visual

## Ferramentas Embarcadas

| Ferramenta | Atalho | Descrição |
|------------|--------|-----------|
| AuraPaint | `/paint` | Editor ANSI art nativo com 20+ ferramentas de desenho |
| File Manager | `/files` | Navegador com preview e integração AuraPaint |
| Monitor | `/monitor` | Browser de terminal via binário `aura-monitor` |

## Temas

Os temas ficam em `styles/` (`.tcss`) e são carregados pelo `ThemeLoader`. Temas disponíveis:
`aura_minimal`, `dark`, `light`, `cyberpunk`, `nebula`, `holographic`, `mono`.

## Desenvolvimento

```bash
# Rodar TUI isolada
python -m aura_cli.tui

# Abrir o editor nativo diretamente
aura-paint [arquivo.ansi]

# Testes TUI
pytest tests/unit/tui/
pytest tests/unit/ui/
```

Veja [docs/developer-guides/tui-components.md](../../docs/developer-guides/tui-components.md) para guia de criação de widgets.
