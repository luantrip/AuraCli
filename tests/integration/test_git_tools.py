import subprocess


def test_git_repository_boundary_is_available():
    result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "true"
