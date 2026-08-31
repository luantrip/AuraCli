# Estado da documentação

Este documento registra as convenções atuais para manter a documentação da
AuraCli coerente com o código nativo.

## Identidade visual e ferramentas

- O editor ANSI integrado é o **AuraPaint**, identidade nativa da AuraCli.
- O comando `aura-paint` abre o editor diretamente quando o projeto está
  instalado.
- A TUI continua baseada em Textual; os componentes são mantidos dentro de
  `aura_cli/tui/` e não dependem de uma instalação externa do editor.

## Sessões e integrações

- Use `aura --resume <id-ou-prefixo>` para iniciar a CLI com uma sessão
  existente.
- Use `/resume <id-ou-prefixo-ou-nome>` durante uma sessão interativa.
- Sessões importadas de outros agentes devem permanecer identificadas pela
  origem e passar pela validação normal antes de serem restauradas.

## Manutenção

- Evite números fixos de testes, widgets ou arquivos em READMEs: eles mudam
  conforme a cobertura evolui.
- A documentação de cada domínio deve explicar responsabilidade e integração,
  não duplicar inventários gerados automaticamente.
- O catálogo oficial de comandos e ferramentas deve apontar para os guias em
  `docs/user-guides/` e para a documentação de arquitetura em
  `docs/reference/`.
