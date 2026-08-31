import subprocess


def test_shell_boundary_returns_process_result():
    result = subprocess.run(["/bin/echo", "aura"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "aura"
