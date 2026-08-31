# Scripts de desenvolvimento e release

Os scripts deste diretório são periféricos de manutenção, build, validação e
instalação; não fazem parte do runtime normal do Aura CLI. Execute-os a partir de qualquer diretório:
os entrypoints resolvem a raiz do projeto pela própria localização.

| Script | Responsabilidade | Efeito |
|---|---|---|
| `build_all.sh` | Prepara `.venv`, instala o modo dev, compila Nim quando disponível e executa os testes | modifica ambiente/build |
| `build_nim.sh` | Compila e espelha os artefatos Nim para o target local | modifica `bin/` e pacote Nim |
| `build_linux.sh` | Valida pré-requisitos e delega o build nativo Linux | modifica artefatos de build |
| `install_aura_cli.sh` | Instala o projeto e mantém um bloco gerenciado no `.zshrc` | modifica `.venv` e shell do usuário |
| `aura_cli_shell_patch.zsh` | Configura PATH e alias; deve ser carregado com `source` | modifica apenas o shell atual |
| `check_docs.py` | Valida links locais da documentação | somente leitura |
| `generate_tool_manifest.py` | Regenera metadados canônicos das ferramentas | modifica o manifesto gerado |
| `track_generated_artifacts.py` | Executa um comando isolando `AURA_HOME` e relata alterações | executa comando informado |
| `verify_nim_release.py` | Verifica formato, espelhamento, checksums e smoke dos binários | leitura; grava com `--write-manifest` |
| `check_workflow_security.py` | Valida permissões mínimas, triggers e exceções explícitas de release | somente leitura |
| `measure_runtime_health.py` | Mede replay semântico, round-trip de sessão e coleta de sistema usando fixtures versionados | leitura; pode gravar relatório indicado |
| `tool_discovery.py` | Descoberta por reflexão usada somente na geração do manifesto | módulo de build, não entrypoint |
| `rea-scripts/` | Probes, campanhas REA e launchers de estudo preservados para reprodução futura | fora do fluxo de manutenção |

## Catracas rápidas

```bash
python scripts/check_docs.py
python scripts/check_workflow_security.py
python scripts/measure_runtime_health.py --output audit_measurements/phase13_runtime_health.json
python scripts/generate_tool_manifest.py --check
ruff check scripts
ruff format --check scripts
bash -n scripts/*.sh
zsh -n scripts/aura_cli_shell_patch.zsh
```

O patch Zsh principal configura o ambiente e expõe somente o gate de release:
`aura_ci_gate`. Os executores de campanhas e probes ficam em
`scripts/rea-scripts/` e não fazem parte da manutenção cotidiana.

O build Linux não instala compiladores, pacotes do sistema nem executa instaladores
remotos. Prepare Nim, OpenSSL e um compilador C explicitamente antes de executá-lo.
O instalador de shell cria `~/.zshrc.aura-cli.bak` antes de atualizar seu bloco.
