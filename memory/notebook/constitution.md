# 📋 Constituição do Projeto Aura CLI

**Criado em:** 2024-12-07
**Última atualização:** 2024-12-07
**Versão:** 2.0

---

## 🎯 Visão Geral

### Descrição do Projeto
Aura CLI é um assistente de código AI de linha de comando, projetado para auxiliar desenvolvedores com tarefas de programação, DevOps e gerenciamento de projetos.

### Objetivo Principal
Fornecer uma interface de terminal poderosa e intuitiva para interagir com modelos de linguagem e executar tarefas de desenvolvimento de forma autônoma.

---

## 🛠️ Stack Tecnológico

### Linguagens Principais
- **Python 3.11+**: Core da aplicação
- **Nim**: Módulos de alta performance (notebook, monitor, imagination)

### Frameworks
- **Typer**: CLI framework
- **Rich**: Terminal UI
- **prompt_toolkit**: Input handling
- **LiteLLM**: Multi-provider LLM

### Banco de Dados
- Arquivos JSON/Markdown para persistência
- SQLite para cache (opcional)

### Outras Tecnologias
- Threading para workers assíncronos
- FFI para integração Python/Nim

---

## 📁 Estrutura do Projeto

### Organização de Diretórios
```
aura_cli/
├── cli/           # Interface de linha de comando
│   ├── ui/        # Componentes visuais
│   └── workers/   # AGI e OPS workers
├── core/          # Núcleo do sistema
│   ├── tools/     # Ferramentas disponíveis
│   ├── agents/    # Sistema de agentes
│   └── memory/    # Sistema de memória
├── tui/           # Interface TUI (Textual)
└── consciousness/ # Skills e retrieval
```

### Convenções de Nomenclatura
- **Arquivos:** snake_case.py
- **Diretórios:** lowercase ou snake_case
- **Módulos:** snake_case

---

## 💻 Convenções de Código

### Estilo de Código
- PEP 8 para Python
- Linha máxima: 100 caracteres
- Imports ordenados (isort)

### Padrões de Nomenclatura
- **Variáveis:** snake_case
- **Funções:** snake_case
- **Classes:** PascalCase
- **Constantes:** UPPER_SNAKE_CASE

### Documentação
- Docstrings Google style para funções públicas
- Type hints obrigatórios
- Comentários em português ou inglês

### Tratamento de Erros
- Exceções específicas quando possível
- Logging estruturado com get_logger
- Fallbacks graceful para operações externas

---

## 🔄 Git e Versionamento

### Padrão de Branches
- `main`: Produção estável
- `feature/*`: Novas funcionalidades
- `bugfix/*`: Correções
- `docs/*`: Documentação

### Formato de Commits
```
<type>(<scope>): <description>

[body]

[footer]
```

Types: feat, fix, docs, style, refactor, test, chore

### Processo de Review
- Pull Request obrigatório para main
- Testes passando antes do merge

---

## 🧪 Testes

### Estratégia de Testes
- Testes unitários para funções isoladas
- Testes de integração para workflows
- Mocks para chamadas externas (LLM, filesystem)

### Cobertura Mínima
- Core modules: 70%
- CLI: 50%

### Ferramentas de Teste
- pytest
- pytest-asyncio
- pytest-cov

---

## 🔐 Segurança

### Práticas de Segurança
- Nunca commitar API keys
- Usar keyring para armazenamento seguro
- Validar inputs do usuário
- Mascarar secrets em logs

### Variáveis de Ambiente
- GOOGLE_API_KEY
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- Usar .env para desenvolvimento local

---

## 📝 Regras do Agente

### Comportamentos Obrigatórios
- Verificar se arquivos existem antes de editar
- Usar ferramentas disponíveis ao invés de simular
- Manter consistência com código existente
- Respeitar padrões de nomenclatura do projeto
- Documentar mudanças significativas

### Comportamentos Proibidos
- Não deletar arquivos sem confirmação explícita
- Não expor API keys ou secrets
- Não fazer commits sem revisão do usuário
- Não ignorar erros silenciosamente

### Prioridades
1. **Segurança**: Nunca comprometer dados ou credenciais
2. **Qualidade**: Código limpo e testável
3. **Performance**: Otimizar quando necessário
4. **UX**: Feedback claro ao usuário

---

## 📚 Regras Aprendidas

*Esta seção é atualizada automaticamente com regras aprendidas durante o uso.*

- Sempre usar type hints em funções públicas
- Preferir composição sobre herança
- Usar logging ao invés de print para debug
- Documentar comportamentos não óbvios

---

*Constituição gerenciada pela Aura CLI v2.0*
