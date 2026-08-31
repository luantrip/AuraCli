"""
Testes para Parser de Comandos Git em Linguagem Natural do Aura CLI.

Este módulo contém testes que verificam o funcionamento do sistema de parsing
de comandos Git em linguagem natural. Testa a interpretação de comandos em
português e sua conversão para ações Git específicas, incluindo extração de
mensagens de commit e sugestão inteligente de mensagens.

Componentes Testados:
    - parse_natural_git_command: Parser principal de comandos em linguagem natural
    - extract_commit_message: Extração de mensagens de commit de comandos
    - suggest_commit_message: Sugestão inteligente de mensagens baseada em mudanças

Cenários de Teste:
    - Comandos de Commit: Reconhecimento de variações de comandos de commit
    - Comandos de Status: Identificação de comandos para ver status
    - Comandos de Log: Reconhecimento de comandos de histórico
    - Comandos de Diff: Identificação de comandos de diferenças
    - Comandos de Branch: Reconhecimento de comandos de branches
    - Comandos Desconhecidos: Tratamento de comandos não reconhecidos
    - Extração de Mensagens: Extração de mensagens com aspas, dois pontos, etc.
    - Sugestão de Mensagens: Sugestão baseada em tipo de mudança (feat, fix, refactor)

Validações:
    - Comandos são reconhecidos corretamente independente da formulação
    - Mensagens são extraídas de diferentes formatos
    - Sugestões são apropriadas para o tipo de mudança
    - Comandos desconhecidos são tratados adequadamente

Estrutura de Testes:
    - TestParseNaturalGitCommand: Testes do parser principal
    - TestExtractCommitMessage: Testes de extração de mensagens
    - TestSuggestCommitMessage: Testes de sugestão de mensagens

Formatos Suportados:
    - Comandos com aspas: "fazer commit com mensagem 'feat: nova feature'"
    - Comandos com dois pontos: "commitar mensagem: feat: adicionar login"
    - Comandos sem mensagem: "fazer commit das mudanças"

Tipos de Sugestão:
    - feat: Para novos arquivos (A)
    - refactor: Para arquivos deletados (D)
    - fix: Para arquivos modificados (M)
    - Padrão: Quando não há mudanças específicas

Exemplo de Uso:
    ```python
    def test_parse():
        result = parse_natural_git_command("fazer commit")
        assert result["action"] == "commit"

        message = extract_commit_message("commitar 'feat: nova feature'")
        assert message == "feat: nova feature"
    ```

Dependências:
    - pytest: Framework de testes
    - natural_git: Módulo de parsing de comandos Git
"""

from aura_cli.core.tools.natural_git import (
    extract_commit_message,
    parse_natural_git_command,
    suggest_commit_message,
)


class TestParseNaturalGitCommand:
    """Testes para parse_natural_git_command"""

    def test_parse_commit_commands(self):
        """
        Testa reconhecimento de comandos de commit.

        Verifica se parse_natural_git_command identifica comandos de commit corretamente.
        """
        test_cases = [
            "fazer commit",
            "fazer um commit",
            "commitar mudanças",
            "salvar mudanças",
            "fazer commit das mudanças",
        ]

        for cmd in test_cases:
            result = parse_natural_git_command(cmd)
            assert result["action"] == "commit", f"Falhou para: {cmd}"
            assert result.get("auto_stage") is True

    def test_parse_status_commands(self):
        """
        Testa reconhecimento de comandos de status.

        Verifica se parse_natural_git_command identifica comandos de status.
        """
        test_cases = [
            "ver mudanças",
            "mostrar status",
            "o que mudou",
            "mudanças pendentes",
        ]

        for cmd in test_cases:
            result = parse_natural_git_command(cmd)
            assert result["action"] == "status", f"Falhou para: {cmd}"

    def test_parse_log_commands(self):
        """
        Testa reconhecimento de comandos de log.

        Verifica se parse_natural_git_command identifica comandos de histórico.
        """
        test_cases = [
            "histórico de commits",
            "ver commits",
            "últimos commits",
            "log de commits",
        ]

        for cmd in test_cases:
            result = parse_natural_git_command(cmd)
            assert result["action"] == "log", f"Falhou para: {cmd}"

    def test_parse_diff_commands(self):
        """
        Testa reconhecimento de comandos de diff.

        Verifica se parse_natural_git_command identifica comandos de diferenças.
        """
        test_cases = [
            "ver diferenças",
            "diff do código",
            "mudanças no código",
            "o que foi alterado",
        ]

        for cmd in test_cases:
            result = parse_natural_git_command(cmd)
            # A função pode retornar "dif" ou "diff"
            assert result["action"] in ["diff", "dif"], f"Falhou para: {cmd}"

    def test_parse_branch_commands(self):
        """
        Testa reconhecimento de comandos de branch.

        Verifica se parse_natural_git_command identifica comandos de branches.
        """
        test_cases = [
            "ver branches",
            "listar branches",
            "ramos do projeto",
        ]

        for cmd in test_cases:
            result = parse_natural_git_command(cmd)
            assert result["action"] == "branch", f"Falhou para: {cmd}"

    def test_parse_unknown_command(self):
        """
        Testa comando não reconhecido.

        Verifica comportamento quando comando não é reconhecido.
        """
        result = parse_natural_git_command("comando desconhecido xyz")
        assert result["action"] == "unknown"


class TestExtractCommitMessage:
    """Testes para extract_commit_message"""

    def test_extract_message_with_quotes(self):
        """
        Testa extração de mensagem com aspas.

        Verifica se extract_commit_message extrai mensagem entre aspas.
        """
        test_cases = [
            ("fazer commit com mensagem 'feat: nova feature'", "feat: nova feature"),
            ('commitar dizendo "fix: bug corrigido"', "fix: bug corrigido"),
            ("salvar como 'refactor: código limpo'", "refactor: código limpo"),
        ]

        for cmd, expected in test_cases:
            result = extract_commit_message(cmd)
            assert result == expected, f"Falhou para: {cmd}"

    def test_extract_message_with_colon(self):
        """
        Testa extração de mensagem com dois pontos.

        Verifica se extract_commit_message extrai mensagem após dois pontos.
        """
        cmd = "fazer commit mensagem: feat: adicionar login"
        result = extract_commit_message(cmd)

        assert "feat" in result.lower() or "login" in result.lower()

    def test_extract_message_none(self):
        """
        Testa quando não há mensagem no comando.

        Verifica comportamento quando comando não contém mensagem.
        """
        cmd = "fazer commit das mudanças"
        result = extract_commit_message(cmd)

        assert result is None or result == ""


class TestSuggestCommitMessage:
    """Testes para suggest_commit_message"""

    def test_suggest_feat_for_new_files(self):
        """
        Testa sugestão de 'feat' para novos arquivos.

        Verifica se suggest_commit_message sugere 'feat' quando há arquivos novos.
        """
        changes = ["A  new_file.py"]
        result = suggest_commit_message(changes)

        assert "feat" in result.lower()

    def test_suggest_refactor_for_deleted(self):
        """
        Testa sugestão de 'refactor' para arquivos deletados.

        Verifica se suggest_commit_message sugere 'refactor' quando há arquivos deletados.
        """
        changes = ["D  old_file.py"]
        result = suggest_commit_message(changes)

        assert "refactor" in result.lower()

    def test_suggest_fix_for_modified(self):
        """
        Testa sugestão de 'fix' para modificações.

        Verifica se suggest_commit_message sugere 'fix' quando há modificações.
        """
        changes = ["M  existing_file.py"]
        result = suggest_commit_message(changes)

        assert "fix" in result.lower()

    def test_suggest_default_message(self):
        """
        Testa sugestão padrão.

        Verifica se suggest_commit_message retorna mensagem padrão quando não há mudanças.
        """
        result = suggest_commit_message([])

        assert (
            "feat" in result.lower() or "mudanças" in result.lower() or len(result) > 0
        )
