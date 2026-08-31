# aura-cli-nim

Artefatos nativos Nim opcionais para a [AuraCli](https://github.com/luantrip/AuraCli). O pacote contém payloads pré-compilados por plataforma; ele não é necessário para instalar ou executar o wheel Python base.

## Instalação

```bash
pip install aura-cli-nim
```

Ou como extra da AuraCli:

```bash
pip install 'aura-cli[nim]'
```

## Artefatos

| Artefato | Função |
|---|---|
| `imagination` | Scanner de filesystem |
| `nexus` | Análise de grafo de dependências |
| `sentinel` | Detecção de alterações |
| `prism` | Chunking semântico |
| `forge` | Validação/sanitização de código |
| `aura-monitor` | Browser de terminal |
| `notebook` | Biblioteca compartilhada de memória |

Os artefatos ficam em um diretório de target canônico, por exemplo `linux-x86_64`, `macos-aarch64` ou `windows-x86_64`. Executáveis Windows usam `.exe`; a library Notebook usa `.dll`, `.dylib` ou `.so` conforme o target. Cada payload publicado inclui `SHA256SUMS`.

A API `aura_cli_nim` somente localiza arquivos existentes e executáveis. A validação de formato nativo, arquitetura, ABI, permissões e segurança de execução permanece no runtime da AuraCli antes de qualquer carregamento ou processo.

## Fallback e desempenho

Se a plataforma em execução não possuir um wheel correspondente, ou se um artefato falhar na validação, a AuraCli usa o fallback Python quando existe. Nexus usa o analisador AST Python; Imagination usa o scanner Python; Forge usa análise Python, mas sanitização indisponível é reportada explicitamente. Prism, Sentinel e Monitor retornam erro controlado quando não há backend nativo válido.

O pacote não promete um fator fixo de aceleração. Ganhos dependem de plataforma, versão do compilador, carga, tamanho do projeto e configuração; qualquer claim quantitativo deve ser sustentado por benchmark reproduzível.

## Verificação local

```python
from aura_cli_nim import get_all_binaries

artifacts = get_all_binaries()
print(artifacts)
```

Essa consulta não executa nem carrega os artefatos. A verificação completa de release é feita por `scripts/verify_nim_release.py` no repositório principal.
