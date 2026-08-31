"""Security audit for Aura CLI.

Provides auditing of configurations, permissions and
security practices.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import uuid

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class IssueSeverity(Enum):
    """Severity level of a security issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityIssue:
    """A security issue found during an audit."""

    id: str
    severity: IssueSeverity
    category: str
    description: str
    recommendation: str
    file_path: Optional[str] = None


@dataclass
class AuditResult:
    """Result of a security audit."""

    audit_id: str
    timestamp: datetime
    issues: List[SecurityIssue] = field(default_factory=list)
    score: float = 100.0
    passed: bool = True


class SecurityAuditor:
    """Runs security audits on project files and configuration."""

    def __init__(self):
        """Initialise the security auditor."""
        self.stats = get_stats()
        self.audit_history: List[AuditResult] = []

        logger.info("SecurityAuditor initialized")

    def audit_security(
        self, scope: str = ".", checks: Optional[List[str]] = None
    ) -> AuditResult:
        """Run a security audit and return an AuditResult."""
        import uuid

        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        audit_id = str(uuid.uuid4())[:8]

        display_tool_call("audit_security", {"scope": scope, "checks": checks})

        issues = []

        if checks is None or "permissions" in checks:
            perm_issues = self._check_permissions(scope)
            issues.extend(perm_issues)

        if checks is None or "secrets" in checks:
            secret_issues = self._check_secrets(scope)
            issues.extend(secret_issues)

        if checks is None or "dependencies" in checks:
            dep_issues = self._check_dependencies(scope)
            issues.extend(dep_issues)

        score = self._calculate_score(issues)
        passed = score >= 70.0  # Threshold de 70%

        result = AuditResult(
            audit_id=audit_id,
            timestamp=datetime.now(),
            issues=issues,
            score=score,
            passed=passed,
        )

        self.audit_history.append(result)

        if passed:
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Auditoria concluída: Score {score:.1f}/100[/{UIStyles.SUCCESS}]"
            )
        else:
            console.print(
                f"[{UIStyles.WARNING}]{UIIcons.WARNING} "
                f"Auditoria concluída: Score {score:.1f}/100 "
                f"({len(issues)} problemas encontrados)[/{UIStyles.WARNING}]"
            )

        self.stats.track_tool_usage("security_audit")

        return result

    def _check_permissions(self, scope: str) -> List[SecurityIssue]:
        """Check file and directory permission settings."""
        issues = []
        import os
        import stat

        for root, _, files in os.walk(scope):
            for file in files:
                file_path = os.path.join(root, file)

                try:
                    file_stat = os.stat(file_path)
                    mode = file_stat.st_mode

                    if mode & stat.S_IWOTH:
                        import uuid

                        issue = SecurityIssue(
                            id=str(uuid.uuid4())[:8],
                            severity=IssueSeverity.MEDIUM,
                            category="permissions",
                            description=f"Arquivo {file_path} tem permissões de escrita para outros",
                            recommendation="Remova permissões de escrita para outros: chmod o-w",
                            file_path=file_path,
                        )
                        issues.append(issue)
                except Exception:
                    continue

        return issues

    def _check_secrets(self, scope: str) -> List[SecurityIssue]:
        """Check for exposed secrets in the given scope."""
        issues = []
        import os
        import re

        secret_patterns = [
            (r'api[_-]?key\s*[:=]\s*["\']([^"\']+)["\']', "API Key"),
            (r'password\s*[:=]\s*["\']([^"\']+)["\']', "Password"),
            (r'secret\s*[:=]\s*["\']([^"\']+)["\']', "Secret"),
            (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private Key"),
        ]

        for root, dirs, files in os.walk(scope):
            dirs[:] = [
                d for d in dirs if d not in [".git", "__pycache__", "node_modules"]
            ]

            for file in files:
                if not file.endswith(
                    (".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env")
                ):
                    continue

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                        for pattern, secret_type in secret_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                import uuid

                                issue = SecurityIssue(
                                    id=str(uuid.uuid4())[:8],
                                    severity=IssueSeverity.HIGH,
                                    category="secrets",
                                    description=f"Possível {secret_type} exposto em {file_path}",
                                    recommendation="Mova secrets para variáveis de ambiente ou secret manager",
                                    file_path=file_path,
                                )
                                issues.append(issue)
                                break  # Um problema por arquivo
                except Exception:
                    continue

        return issues

    def _check_dependencies(self, scope: str) -> List[SecurityIssue]:
        """Check for vulnerable or outdated dependencies."""
        issues: List[SecurityIssue] = []

        requirements_file = os.path.join(scope, "requirements.txt")
        pyproject_file = os.path.join(scope, "pyproject.toml")

        has_requirements = os.path.exists(requirements_file)
        has_pyproject = os.path.exists(pyproject_file)

        if not has_requirements and not has_pyproject:
            return issues

        pip_audit_bin = shutil.which("pip-audit")

        if pip_audit_bin:
            issues.extend(
                self._run_pip_audit(
                    pip_audit_bin,
                    scope,
                    requirements_file if has_requirements else None,
                )
            )
        else:
            # pip-audit unavailable — warn and run basic heuristic analysis
            logger.debug(
                "pip-audit not found — falling back to heuristic dependency check"
            )
            issues.append(
                SecurityIssue(
                    id=uuid.uuid4().hex[:8],
                    severity=IssueSeverity.LOW,
                    category="dependencies",
                    description=(
                        "pip-audit não está instalado. "
                        "Não foi possível verificar CVEs nas dependências."
                    ),
                    recommendation="Instale pip-audit: pip install pip-audit",
                )
            )
            if has_requirements:
                issues.extend(self._heuristic_requirements_check(requirements_file))

        return issues

    def _run_pip_audit(
        self,
        pip_audit_bin: str,
        scope: str,
        requirements_file: Optional[str],
    ) -> List[SecurityIssue]:
        """Run pip-audit and convert the JSON output to SecurityIssues."""
        issues: List[SecurityIssue] = []

        cmd = [pip_audit_bin, "--format", "json", "--progress-spinner", "off"]
        if requirements_file:
            cmd += ["-r", requirements_file]
        else:
            # Audita o ambiente virtualenv/projeto atual
            cmd += ["--local"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=scope,
            )
            # pip-audit exits 1 when vulnerabilities are found — not an error
            raw = result.stdout or result.stderr
            if not raw.strip():
                logger.debug(
                    "pip-audit produced no output (exit %d)", result.returncode
                )
                return issues

            data = json.loads(raw)
        except subprocess.TimeoutExpired:
            logger.warning("pip-audit timed out after 120s")
            issues.append(
                SecurityIssue(
                    id=uuid.uuid4().hex[:8],
                    severity=IssueSeverity.LOW,
                    category="dependencies",
                    description="pip-audit excedeu o timeout de 120s — auditoria de dependências incompleta.",
                    recommendation="Execute pip-audit manualmente para um relatório completo.",
                )
            )
            return issues
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("pip-audit output parse error: %s", exc)
            return issues

        # pip-audit JSON schema: {"dependencies": [{"name": ..., "version": ..., "vulns": [...]}]}
        for dep in data.get("dependencies", []):
            for vuln in dep.get("vulns", []):
                aliases = vuln.get("aliases", [])
                vuln_id = vuln.get("id", "UNKNOWN")
                fix_versions = vuln.get("fix_versions", [])
                description = vuln.get("description", "")

                # Determine severity from CVE aliases when possible (best-effort)
                severity = self._severity_from_vuln_id(vuln_id, aliases)

                fix_hint = (
                    f"Atualize para {dep['name']}>={fix_versions[0]}"
                    if fix_versions
                    else f"Verifique o advisory {vuln_id} para uma versão corrigida"
                )

                issues.append(
                    SecurityIssue(
                        id=uuid.uuid4().hex[:8],
                        severity=severity,
                        category="dependencies",
                        description=(
                            f"{dep['name']}=={dep['version']} — {vuln_id}: {description[:200]}"
                        ),
                        recommendation=fix_hint,
                    )
                )

        return issues

    @staticmethod
    def _severity_from_vuln_id(vuln_id: str, aliases: List[str]) -> "IssueSeverity":
        """Derive severity level from a vulnerability ID."""
        all_ids = [vuln_id, *aliases]
        for vid in all_ids:
            vid_upper = vid.upper()
            if vid_upper.startswith("CVE-"):
                return IssueSeverity.HIGH
            if vid_upper.startswith("PYSEC-"):
                return IssueSeverity.HIGH
            if vid_upper.startswith("GHSA-"):
                return IssueSeverity.MEDIUM
        return IssueSeverity.MEDIUM

    @staticmethod
    def _heuristic_requirements_check(requirements_file: str) -> List[SecurityIssue]:
        """Heuristic check for requirements file issues."""
        issues: List[SecurityIssue] = []
        unpinned: List[str] = []

        try:
            with open(requirements_file, encoding="utf-8", errors="ignore") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line or line.startswith(("#", "-")):
                        continue
                    # Strip extras like package[extra]>=1.0
                    pkg = re.split(r"[\[>=<!@;]", line)[0].strip()
                    if pkg and not re.search(r"[>=<!~]", line):
                        unpinned.append(pkg)
        except OSError:
            return issues

        if unpinned:
            issues.append(
                SecurityIssue(
                    id=uuid.uuid4().hex[:8],
                    severity=IssueSeverity.LOW,
                    category="dependencies",
                    description=(
                        f"{len(unpinned)} pacote(s) sem versão pinada em requirements.txt: "
                        + ", ".join(unpinned[:10])
                        + (" ..." if len(unpinned) > 10 else "")
                    ),
                    recommendation=(
                        "Pinar versões (pkg==x.y.z) permite auditoria reprodutível de CVEs. "
                        "Use pip freeze > requirements.txt para capturar versões exatas."
                    ),
                )
            )

        return issues

    def _calculate_score(self, issues: List[SecurityIssue]) -> float:
        """Calculate a security score (0-100) from a list of issues."""
        if not issues:
            return 100.0

        penalties = {
            IssueSeverity.CRITICAL: 20.0,
            IssueSeverity.HIGH: 10.0,
            IssueSeverity.MEDIUM: 5.0,
            IssueSeverity.LOW: 2.0,
        }

        total_penalty = sum(penalties.get(issue.severity, 0) for issue in issues)

        score = max(0.0, 100.0 - total_penalty)

        return score

    def get_audit_history(self) -> List[Dict[str, Any]]:
        """Return past audit results."""
        return [
            {
                "audit_id": r.audit_id,
                "timestamp": r.timestamp.isoformat(),
                "score": r.score,
                "passed": r.passed,
                "issues_count": len(r.issues),
            }
            for r in self.audit_history
        ]


# Factory function for singleton pattern
_audit_instance: Optional["SecurityAuditor"] = None


def get_security_audit() -> "SecurityAuditor":
    """
    Get or create SecurityAuditor instance (singleton).

    Returns:
        SecurityAuditor instance
    """
    global _audit_instance
    if _audit_instance is None:
        _audit_instance = SecurityAuditor()
    return _audit_instance
