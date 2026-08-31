"""Tests for security pattern scanner."""

from aura_cli.core.quality.security_scanner import scan_security


def test_hardcoded_secret():
    source = 'password = "super_secret_123"\n'
    results = scan_security(source)
    assert any(r["rule"] == "hardcoded-secret" for r in results)


def test_hardcoded_api_key():
    source = "api_key = 'sk-abc123def456'\n"
    results = scan_security(source)
    assert any(r["rule"] == "hardcoded-secret" for r in results)


def test_unsafe_eval():
    source = """
user_input = input()
result = eval(user_input)
"""
    results = scan_security(source)
    assert any(r["rule"] == "unsafe-eval" for r in results)


def test_safe_eval_with_literal():
    source = """
result = eval("1 + 2")
"""
    results = scan_security(source)
    assert not any(r["rule"] == "unsafe-eval" for r in results)


def test_sql_injection():
    source = """
query = f"SELECT * FROM users WHERE id = {user_id}"
"""
    results = scan_security(source)
    assert any(r["rule"] == "sql-injection" for r in results)


def test_subprocess_shell_true():
    source = """
import subprocess
subprocess.run(cmd, shell=True)
"""
    results = scan_security(source)
    assert any(r["rule"] == "shell-injection" for r in results)


def test_subprocess_shell_false_ok():
    source = """
import subprocess
subprocess.run(cmd, shell=False)
"""
    results = scan_security(source)
    assert not any(r["rule"] == "shell-injection" for r in results)


def test_insecure_http():
    source = """
url = "http://example.com/api"
"""
    results = scan_security(source)
    assert any(r["rule"] == "insecure-http" for r in results)


def test_localhost_http_ok():
    source = """
url = "http://localhost:8080/api"
"""
    results = scan_security(source)
    assert not any(r["rule"] == "insecure-http" for r in results)


def test_https_ok():
    source = """
url = "https://example.com/api"
"""
    results = scan_security(source)
    assert not any(r["rule"] == "insecure-http" for r in results)


def test_comment_ignored():
    source = '# password = "not_a_real_secret"\n'
    results = scan_security(source)
    assert not any(r["rule"] == "hardcoded-secret" for r in results)


def test_exec_with_variable():
    source = """
code = get_code()
exec(code)
"""
    results = scan_security(source)
    assert any(r["rule"] == "unsafe-eval" for r in results)


def test_severity_levels():
    source = """
api_key = "abc123"
result = eval(user_input)
query = f"SELECT * FROM t WHERE id = {x}"
url = "http://example.com"
"""
    results = scan_security(source)
    severities = {r["rule"]: r["severity"] for r in results}
    assert severities.get("hardcoded-secret") == "high"
    assert severities.get("sql-injection") == "critical"
    assert severities.get("insecure-http") == "medium"
