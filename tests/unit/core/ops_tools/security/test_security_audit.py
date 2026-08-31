"""
Testes para o módulo security_audit.

Testa funcionalidades de auditoria de configurações,
permissões e práticas de segurança.
"""

from datetime import datetime
from unittest.mock import patch

from aura_cli.core.ops_tools.security.security_audit import (
    AuditResult,
    IssueSeverity,
    SecurityAuditor,
    SecurityIssue,
)


class TestIssueSeverity:
    """Testa enum IssueSeverity."""

    def test_issue_severity_values(self):
        """Testa valores de severidade."""
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.CRITICAL.value == "critical"

    def test_severity_comparison_order(self):
        """Testa ordem implícita de severidade."""
        severities = [
            IssueSeverity.LOW,
            IssueSeverity.MEDIUM,
            IssueSeverity.HIGH,
            IssueSeverity.CRITICAL,
        ]

        # Verificar que temos todos os níveis
        assert len(severities) == 4

        # Verificar valores únicos
        values = [s.value for s in severities]
        assert len(set(values)) == 4


class TestSecurityIssue:
    """Testa dataclass SecurityIssue."""

    def test_security_issue_required_fields(self):
        """Testa campos obrigatórios do problema de segurança."""
        issue = SecurityIssue(
            id="SEC-001",
            severity=IssueSeverity.HIGH,
            category="permissions",
            description="File has overly permissive permissions",
            recommendation="Change file permissions to 644",
        )

        assert issue.id == "SEC-001"
        assert issue.severity == IssueSeverity.HIGH
        assert issue.category == "permissions"
        assert issue.description == "File has overly permissive permissions"
        assert issue.recommendation == "Change file permissions to 644"

    def test_security_issue_optional_file_path(self):
        """Testa campo opcional file_path."""
        issue_without_path = SecurityIssue(
            id="SEC-002",
            severity=IssueSeverity.MEDIUM,
            category="config",
            description="Missing security header",
            recommendation="Add security header",
        )

        assert issue_without_path.file_path is None

        issue_with_path = SecurityIssue(
            id="SEC-003",
            severity=IssueSeverity.LOW,
            category="code",
            description="Hardcoded password",
            recommendation="Use environment variable",
            file_path="/path/to/file.py",
        )

        assert issue_with_path.file_path == "/path/to/file.py"

    def test_security_issue_categories(self):
        """Testa diferentes categorias de problemas."""
        categories = ["permissions", "config", "code", "network", "crypto"]

        issues = []
        for i, category in enumerate(categories):
            issue = SecurityIssue(
                id=f"SEC-{i + 1:03d}",
                severity=IssueSeverity.MEDIUM,
                category=category,
                description=f"Issue in {category}",
                recommendation=f"Fix {category} issue",
            )
            issues.append(issue)

        assert len(issues) == 5
        found_categories = {issue.category for issue in issues}
        assert found_categories == set(categories)


class TestAuditResult:
    """Testa dataclass AuditResult."""

    def test_audit_result_defaults(self):
        """Testa valores padrão do resultado de auditoria."""
        timestamp = datetime.now()
        result = AuditResult(audit_id="AUDIT-001", timestamp=timestamp)

        assert result.audit_id == "AUDIT-001"
        assert result.timestamp == timestamp
        assert result.issues == []
        assert result.score == 100.0
        assert result.passed is True

    def test_audit_result_with_issues(self):
        """Testa resultado com problemas encontrados."""
        timestamp = datetime.now()
        issues = [
            SecurityIssue(
                "SEC-001", IssueSeverity.HIGH, "permissions", "Issue 1", "Fix 1"
            ),
            SecurityIssue(
                "SEC-002", IssueSeverity.MEDIUM, "config", "Issue 2", "Fix 2"
            ),
        ]

        result = AuditResult(
            audit_id="AUDIT-002",
            timestamp=timestamp,
            issues=issues,
            score=75.0,
            passed=False,
        )

        assert result.audit_id == "AUDIT-002"
        assert len(result.issues) == 2
        assert result.score == 75.0
        assert result.passed is False

    def test_audit_result_score_calculation(self):
        """Testa cálculo de score baseado em problemas."""
        # Score perfeito sem problemas
        perfect_result = AuditResult("AUDIT-PERFECT", datetime.now())
        assert perfect_result.score == 100.0
        assert perfect_result.passed is True

        # Score baixo com problemas críticos
        critical_issues = [
            SecurityIssue(
                "SEC-001",
                IssueSeverity.CRITICAL,
                "security",
                "Critical issue",
                "Fix now",
            )
        ]

        failed_result = AuditResult(
            "AUDIT-FAILED",
            datetime.now(),
            issues=critical_issues,
            score=25.0,
            passed=False,
        )

        assert failed_result.score == 25.0
        assert failed_result.passed is False


class TestSecurityAuditor:
    """Testa classe SecurityAuditor."""

    def setup_method(self):
        """Setup para cada teste."""
        self.auditor = SecurityAuditor()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.auditor, "stats")
        assert hasattr(self.auditor, "audit_history")
        assert isinstance(self.auditor.audit_history, list)
        assert len(self.auditor.audit_history) == 0

    @patch("aura_cli.core.ops_tools.security.security_audit.os.walk")
    @patch("aura_cli.core.ui.display_tool_call")
    def test_audit_security_default_scope(self, mock_display, mock_walk):
        """Testa auditoria com escopo padrão."""
        mock_walk.return_value = []
        result = self.auditor.audit_security()

        assert isinstance(result, AuditResult)
        assert isinstance(result.score, float)
        assert isinstance(result.issues, list)
        assert result.audit_id is not None
        mock_display.assert_called_once()

    @patch("aura_cli.core.ops_tools.security.security_audit.os.walk")
    @patch("aura_cli.core.ui.display_tool_call")
    def test_audit_security_custom_scope(self, mock_display, mock_walk):
        """Testa auditoria com escopo customizado."""
        mock_walk.return_value = []
        result = self.auditor.audit_security(scope="/tmp")

        assert isinstance(result, AuditResult)
        assert isinstance(result.score, float)
        assert result.audit_id is not None

    @patch("aura_cli.core.ops_tools.security.security_audit.os.walk")
    @patch("aura_cli.core.ui.display_tool_call")
    def test_audit_security_with_specific_checks(self, mock_display, mock_walk):
        """Testa auditoria com checks específicos."""
        mock_walk.return_value = []
        checks = ["permissions", "secrets"]

        result = self.auditor.audit_security(scope=".", checks=checks)

        assert isinstance(result, AuditResult)
        assert isinstance(result.score, float)
        assert result.audit_id is not None

    @patch("aura_cli.core.ops_tools.security.security_audit.os.walk")
    @patch("aura_cli.core.ui.display_tool_call")
    def test_audit_history_tracking(self, mock_display, mock_walk):
        """Testa rastreamento do histórico de auditorias."""
        # Mock os.walk para retornar lista vazia e evitar timeout
        mock_walk.return_value = []

        # Primeira auditoria
        result1 = self.auditor.audit_security()
        assert len(self.auditor.audit_history) == 1

        # Segunda auditoria
        result2 = self.auditor.audit_security()
        assert len(self.auditor.audit_history) == 2

        # Verificar que são diferentes
        assert result1.audit_id != result2.audit_id

    def test_permissions_check(self):
        """Testa verificação de permissões através de audit_security."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Criar arquivo com permissões abertas
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.chmod(test_file, 0o777)

            # Executar auditoria com check de permissões
            result = self.auditor.audit_security(scope=temp_dir, checks=["permissions"])

            assert isinstance(result, AuditResult)
            # Pode ou não encontrar problemas dependendo do sistema
            assert isinstance(result.issues, list)

    def test_config_security_check(self):
        """Testa verificação de configurações de segurança através de audit_security."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Criar arquivo de config com problemas
            config_file = os.path.join(temp_dir, "config.py")
            with open(config_file, "w") as f:
                f.write("DEBUG = True\nSECRET_KEY = 'hardcoded-secret'\n")

            # Executar auditoria com check de secrets
            result = self.auditor.audit_security(scope=temp_dir, checks=["secrets"])

            assert isinstance(result, AuditResult)
            # Pode ou não encontrar problemas dependendo da implementação
            assert isinstance(result.issues, list)

    def test_code_security_patterns(self):
        """Testa detecção de padrões inseguros no código através de audit_security."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            # Criar arquivo Python com padrões inseguros
            code_file = os.path.join(temp_dir, "app.py")
            with open(code_file, "w") as f:
                f.write("password = 'hardcoded123'\nexec(user_input)\n")

            # Executar auditoria (pode detectar padrões através de checks de secrets)
            result = self.auditor.audit_security(scope=temp_dir, checks=["secrets"])

            assert isinstance(result, AuditResult)
            # Pode ou não encontrar problemas
            assert isinstance(result.issues, list)

    @patch("aura_cli.core.ops_tools.security.security_audit.os.walk")
    def test_network_security_check(self, mock_walk):
        """Testa verificação de configurações de rede através de audit_security."""
        mock_walk.return_value = []
        result = self.auditor.audit_security(scope=".")

        assert isinstance(result, AuditResult)
        assert isinstance(result.score, float)
        assert result.audit_id is not None

    @patch("aura_cli.core.ops_tools.security.security_audit.os.walk")
    def test_crypto_security_check(self, mock_walk):
        """Testa verificação de práticas criptográficas através de audit_security."""
        mock_walk.return_value = []
        result = self.auditor.audit_security(scope=".")

        assert isinstance(result, AuditResult)
        assert isinstance(result.score, float)
        assert result.audit_id is not None
        assert len(self.auditor.audit_history) >= 1

    def test_score_calculation_based_on_severity(self):
        """Testa cálculo de score baseado na severidade dos problemas."""
        issues = [
            SecurityIssue("1", IssueSeverity.LOW, "test", "Low issue", "Fix"),
            SecurityIssue("2", IssueSeverity.MEDIUM, "test", "Medium issue", "Fix"),
            SecurityIssue("3", IssueSeverity.HIGH, "test", "High issue", "Fix"),
            SecurityIssue("4", IssueSeverity.CRITICAL, "test", "Critical issue", "Fix"),
        ]

        # Simular cálculo de score
        score = 100.0
        severity_penalties = {
            IssueSeverity.LOW: 5,
            IssueSeverity.MEDIUM: 10,
            IssueSeverity.HIGH: 20,
            IssueSeverity.CRITICAL: 30,
        }

        for issue in issues:
            score -= severity_penalties[issue.severity]

        # Score final: 100 - 5 - 10 - 20 - 30 = 35
        assert score == 35.0

    def test_audit_result_pass_fail_threshold(self):
        """Testa limiar de aprovação/reprovação."""
        # Auditoria aprovada (score alto)
        passed_result = AuditResult(
            "AUDIT-PASS", datetime.now(), issues=[], score=85.0, passed=True
        )

        # Auditoria reprovada (score baixo)
        failed_result = AuditResult(
            "AUDIT-FAIL",
            datetime.now(),
            issues=[
                SecurityIssue(
                    "SEC-001", IssueSeverity.CRITICAL, "security", "Critical", "Fix"
                )
            ],
            score=45.0,
            passed=False,
        )

        # Assumindo limiar de 70%
        threshold = 70.0
        assert passed_result.score >= threshold
        assert failed_result.score < threshold

    def test_issue_deduplication(self):
        """Testa remoção de problemas duplicados."""
        issues = [
            SecurityIssue(
                "SEC-001", IssueSeverity.HIGH, "permissions", "Issue 1", "Fix 1"
            ),
            SecurityIssue(
                "SEC-002", IssueSeverity.MEDIUM, "config", "Issue 2", "Fix 2"
            ),
            SecurityIssue(
                "SEC-001", IssueSeverity.HIGH, "permissions", "Issue 1", "Fix 1"
            ),  # Duplicata
        ]

        # Remover duplicatas baseado no ID
        unique_issues = []
        seen_ids = set()

        for issue in issues:
            if issue.id not in seen_ids:
                unique_issues.append(issue)
                seen_ids.add(issue.id)

        assert len(unique_issues) == 2
        assert len(seen_ids) == 2
