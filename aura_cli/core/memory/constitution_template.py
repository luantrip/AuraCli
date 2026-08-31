"""
Constitution Template for Aura CLI Projects.

This module provides templates and utilities for creating and managing
project constitutions. A constitution defines the rules, conventions,
and guidelines that agents must follow when working on a project.

Features:
    - Comprehensive constitution template
    - Section-based organization
    - Validation helpers
    - Migration utilities for updating constitutions
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ConstitutionSection:
    """Represents a section of the constitution."""

    title: str
    content: str
    required: bool = False
    examples: List[str] = field(default_factory=list)


CONSTITUTION_TEMPLATE = """# 📋 Constituição do Projeto

**Criado em:** {created_date}
**Última atualização:** {updated_date}
**Versão:** 1.0

---

## 🎯 Overview

### Project Description
{project_description}

### Objetivo Principal
{main_objective}

---

## 🛠️ Tech Stack

### Linguagens Principais
{languages}

### Frameworks
{frameworks}

### Banco de Dados
{database}

### Outras Tecnologias
{other_tech}

---

## 📁 Estrutura do Projeto

### Directory Organisation
```
{directory_structure}
```

### Naming Conventions
- **Arquivos:** {file_naming}
- **Diretórios:** {dir_naming}
- **Módulos:** {module_naming}

---

## 💻 Code Conventions

### Code Style
{code_style}

### Naming Patterns
- **Variáveis:** {var_naming}
- **Funções:** {func_naming}
- **Classes:** {class_naming}
- **Constantes:** {const_naming}

### Documentation
{documentation_style}

### Tratamento de Erros
{error_handling}

---

## 🔄 Git e Versionamento

### Branch Pattern
{branch_pattern}

### Formato de Commits
{commit_format}

### Processo de Review
{review_process}

---

## 🧪 Testes

### Testing Strategy
{test_strategy}

### Minimum Coverage
{test_coverage}

### Ferramentas de Teste
{test_tools}

---

## 🔐 Security

### Security Practices
{security_practices}

### Environment Variables
{env_vars}

---

## 📝 Regras do Agente

### Required Behaviours
{agent_must}

### Comportamentos Proibidos
{agent_must_not}

### Prioridades
{agent_priorities}

---

## 📚 Regras Aprendidas

*Esta seção é atualizada automaticamente com regras aprendidas durante o uso do agente.*

{learned_rules}

---

*Constituição gerenciada pela Aura CLI*
"""


MINIMAL_CONSTITUTION_TEMPLATE = """# 📋 Constituição do Projeto

**Criado em:** {created_date}

## Tech Stack
- **Linguagem:** {language}
- **Banco de Dados:** {database}
- **Estilo da API:** {api_style}

## Conventions
- Usar {naming_convention} para nomenclatura
- {documentation_rule}
- {testing_rule}

## Regras do Agente
- Sempre verificar se arquivos existem antes de editar
- Manter consistência com o código existente
- Comentar código complexo

---

*Constituição gerenciada pela Aura CLI*
"""


CONSTITUTION_QUESTIONS = [
    {
        "id": "project_description",
        "question": "Descreva brevemente o projeto (o que ele faz):",
        "default": "Projeto em desenvolvimento",
        "required": True,
    },
    {
        "id": "language",
        "question": "Qual é a principal linguagem de programação?",
        "options": [
            "Python",
            "JavaScript/TypeScript",
            "Go",
            "Rust",
            "Java",
            "C/C++",
            "Outra",
        ],
        "default": "Python",
        "required": True,
    },
    {
        "id": "frameworks",
        "question": "Quais frameworks você usa? (separados por vírgula)",
        "default": "Nenhum específico",
        "required": False,
    },
    {
        "id": "database",
        "question": "Qual banco de dados será usado?",
        "options": [
            "PostgreSQL",
            "MySQL",
            "SQLite",
            "MongoDB",
            "Redis",
            "Nenhum",
            "Outro",
        ],
        "default": "SQLite",
        "required": False,
    },
    {
        "id": "api_style",
        "question": "Qual o estilo da API?",
        "options": ["REST", "GraphQL", "gRPC", "CLI", "Library", "Não aplicável"],
        "default": "REST",
        "required": False,
    },
    {
        "id": "naming_convention",
        "question": "Convenção de nomenclatura para variáveis/funções:",
        "options": ["snake_case", "camelCase", "PascalCase", "kebab-case"],
        "default": "snake_case",
        "required": True,
    },
    {
        "id": "test_strategy",
        "question": "Estratégia de testes:",
        "options": [
            "TDD",
            "Testes unitários",
            "Testes de integração",
            "Sem testes definidos",
        ],
        "default": "Testes unitários",
        "required": False,
    },
    {
        "id": "commit_format",
        "question": "Formato de mensagens de commit:",
        "options": [
            "Conventional Commits",
            "Livre",
            "Ticket + descrição",
            "Personalizado",
        ],
        "default": "Conventional Commits",
        "required": False,
    },
]


def generate_constitution(
    answers: Dict[str, Any],
    template: str = "minimal",
) -> str:
    """
    Generate a constitution from interview answers.

    Args:
        answers: Dictionary with answers to constitution questions
        template: Template to use ("minimal" or "full")

    Returns:
        Generated constitution content
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if template == "minimal":
        return MINIMAL_CONSTITUTION_TEMPLATE.format(
            created_date=now,
            language=answers.get("language", "Python"),
            database=answers.get("database", "SQLite"),
            api_style=answers.get("api_style", "REST"),
            naming_convention=answers.get("naming_convention", "snake_case"),
            documentation_rule="Documentar funções públicas com docstrings",
            testing_rule="Incluir testes para novas funcionalidades",
        )

    return CONSTITUTION_TEMPLATE.format(
        created_date=now,
        updated_date=now,
        project_description=answers.get(
            "project_description", "Projeto em desenvolvimento"
        ),
        main_objective=answers.get("main_objective", "Definido pelo usuário"),
        languages=answers.get("language", "Python"),
        frameworks=answers.get("frameworks", "Nenhum específico"),
        database=answers.get("database", "SQLite"),
        other_tech=answers.get("other_tech", "N/A"),
        directory_structure=answers.get("directory_structure", "src/\ntests/\ndocs/"),
        file_naming=answers.get("file_naming", "snake_case.py"),
        dir_naming=answers.get("dir_naming", "lowercase"),
        module_naming=answers.get("module_naming", "snake_case"),
        code_style=answers.get("code_style", "PEP 8 para Python"),
        var_naming=answers.get("naming_convention", "snake_case"),
        func_naming=answers.get("naming_convention", "snake_case"),
        class_naming="PascalCase",
        const_naming="UPPER_SNAKE_CASE",
        documentation_style=answers.get(
            "documentation_style", "Docstrings Google style"
        ),
        error_handling=answers.get(
            "error_handling", "Exceções com mensagens descritivas"
        ),
        branch_pattern=answers.get("branch_pattern", "feature/*, bugfix/*, main"),
        commit_format=answers.get("commit_format", "Conventional Commits"),
        review_process=answers.get("review_process", "Pull Request com 1 aprovação"),
        test_strategy=answers.get("test_strategy", "Testes unitários"),
        test_coverage=answers.get("test_coverage", "80%"),
        test_tools=answers.get("test_tools", "pytest"),
        security_practices=answers.get(
            "security_practices", "Não expor secrets, validar inputs"
        ),
        env_vars=answers.get("env_vars", "Usar .env para configurações sensíveis"),
        agent_must=answers.get(
            "agent_must", "- Verificar arquivos antes de editar\n- Manter consistência"
        ),
        agent_must_not=answers.get(
            "agent_must_not",
            "- Não deletar arquivos sem confirmação\n- Não expor secrets",
        ),
        agent_priorities=answers.get(
            "agent_priorities", "1. Segurança\n2. Qualidade\n3. Performance"
        ),
        learned_rules=answers.get("learned_rules", "*Nenhuma regra aprendida ainda*"),
    )


def get_constitution_summary(constitution: str) -> Dict[str, Any]:
    """
    Extract summary information from a constitution.

    Args:
        constitution: Constitution content

    Returns:
        Dictionary with summary info
    """
    summary: Dict[str, Any] = {
        "has_stack": False,
        "has_conventions": False,
        "has_tests": False,
        "has_git": False,
        "has_security": False,
        "sections": [],
        "learned_rules_count": 0,
    }

    if (
        "Stack Tecnológico" in constitution
        or "Tech Stack" in constitution
        or "Linguagem" in constitution
    ):
        summary["has_stack"] = True
        summary["sections"].append("stack")

    if (
        "Convenções" in constitution
        or "Conventions" in constitution
        or "Nomenclatura" in constitution
        or "Naming Conventions" in constitution
    ):
        summary["has_conventions"] = True
        summary["sections"].append("conventions")

    if "Testes" in constitution or "test" in constitution.lower():
        summary["has_tests"] = True
        summary["sections"].append("tests")

    if "Git" in constitution or "Commit" in constitution:
        summary["has_git"] = True
        summary["sections"].append("git")

    if "Segurança" in constitution or "Security" in constitution or "🔐" in constitution:
        summary["has_security"] = True
        summary["sections"].append("security")

    if "Regras Aprendidas" in constitution:
        import re

        rules_section = constitution.split("Regras Aprendidas")[-1]
        rules = re.findall(r"^-\s+.+$", rules_section, re.MULTILINE)
        summary["learned_rules_count"] = len(rules)

    return summary


def validate_constitution(constitution: str) -> List[str]:
    """
    Validate a constitution for completeness.

    Args:
        constitution: Constitution content

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    if not constitution or len(constitution) < 100:
        issues.append("Constitution is too short or empty")
        return issues

    required_sections = ["Linguagem", "Stack", "Convenções"]
    for section in required_sections:
        if section.lower() not in constitution.lower():
            issues.append(f"Missing recommended section: {section}")

    if "Regras do Agente" not in constitution and "agent" not in constitution.lower():
        issues.append("Consider adding agent behavior rules")

    return issues
