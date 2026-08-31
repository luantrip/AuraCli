# Aura Nim Engine (opcional)

Os módulos nativos da AuraCli são implementados em Nim e consumidos por bridges Python em `aura_cli/core/`. Eles aceleram, quando disponíveis, scanning, análise de dependências, detecção de mudanças, sanitização, navegação e memória de notebook. **O wheel Python base não depende do Nim**; cada integração possui fallback Python ou retorna uma falha explícita quando não há substituto seguro.

## Módulos e artefatos

| Fonte | Artefato canônico | Função |
|---|---|---|
| `imagination.nim` | `bin/<target>/imagination[.exe]` | Scanner de projeto |
| `nexus.nim` | `bin/<target>/nexus[.exe]` | Construtor de grafo de dependências |
| `sentinel.nim` | `bin/<target>/sentinel[.exe]` | Detector de mudanças com estado persistido |
| `prism.nim` | `bin/<target>/prism[.exe]` | Chunking semântico de código |
| `forge.nim` | `bin/<target>/forge[.exe]` | Validação e sanitização de código |
| `monitor/monitor.nim` | `bin/<target>/aura-monitor[.exe]` | Browser de terminal |
| `notebook/notebook.nim` | `bin/<target>/notebook.so`, `.dylib` ou `.dll` | Biblioteca de memória via ctypes |

Os nomes de target suportados são `linux-x86_64`, `linux-aarch64`, `macos-x86_64`, `macos-aarch64`, `windows-x86_64` e `windows-aarch64`. O runtime Python é a autoridade para normalização de tag, extensão, nome, magic e arquitetura; o pacote auxiliar somente localiza o payload instalado.

## Build local

```bash
# Build completo da plataforma hospedeira
./scripts/build_nim.sh

# Build de um alvo específico
./scripts/build_nim.sh --target nexus

# Build debug
./scripts/build_nim.sh --debug

# Verificar somente se o compilador Nim real está disponível
./scripts/build_nim.sh --check
```

O build exige Nim >= 1.6.0 e, para `aura-monitor` com TLS, headers/bibliotecas OpenSSL conforme a plataforma. A saída é criada em `bin/<target>/` e espelhada em `packages/aura-cli-nim/aura_cli_nim/bin/<target>/`. O script limpa o target atual antes de uma build completa, remove stale artifacts do componente em build parcial e falha se a verificação de release não passar.

## Integração e segurança

| Componente | Bridge Python principal | Fallback ou comportamento de falha |
|---|---|---|
| `imagination` | `core/context/imagination_manager.py` e `core/tools/imagination_tools.py` | Scanner Python; paths contidos no workspace |
| `nexus` | `core/context/graph_service.py` | `DependencyAnalyzer` baseado em AST |
| `sentinel` | `core/context/sentinel_manager.py` | Falha explícita; o state fica no projeto |
| `prism` | `core/memory/prism_bridge.py` | Lista vazia com `last_error` |
| `forge` | `core/quality/forge_bridge.py` | Análise Python; sanitização indisponível é erro explícito |
| `aura-monitor` | `core/context/monitor_manager.py` | Falha explícita; somente `http/https` público ou arquivo contido |
| `notebook` | `core/memory/memory_manager.py` e `core/memory/notebook_service.py` | Fallback Python atômico e fail-closed |

Todos os subprocessos passam por um runner comum com `shell=False`, `cwd` definido, timeout e limite separado para stdout/stderr. O Sentinel não é sondado com `--version`, porque versões históricas podem interpretar esse argumento como diretório de projeto e criar estado persistente. Libraries não são carregadas por simples existência: o runtime verifica formato nativo, arquitetura, nome canônico e conjunto ABI antes de `ctypes`.

## Artefatos distribuíveis

O pacote `aura-cli-nim` é opcional e contém wheels específicos por plataforma, com `SHA256SUMS`. O wheel base pode ser instalado sozinho. O pacote auxiliar não promete ganho numérico fixo: qualquer comparação de performance deve ser feita com benchmark reproduzível, mesma máquina, mesma carga e mesma versão.
