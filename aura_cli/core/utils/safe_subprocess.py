"""
Safe subprocess execution with timeout and output limits.

Provides secure process execution with:
- Configurable timeout
- Output size limits (prevents memory overflow)
- Process group isolation
- Non-blocking I/O
"""

import contextlib
from dataclasses import dataclass
import os
import platform
import signal
import subprocess
import time
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

IS_WINDOWS = platform.system() == "Windows"
if not IS_WINDOWS:
    import fcntl

MAX_BYTES_PER_READ = 1024
SLEEP_BETWEEN_READS = 0.1


@dataclass
class SubprocessResult:
    """Result of subprocess execution."""

    timeout: bool
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return not self.timeout and self.exit_code == 0


def _set_nonblocking(reader) -> None:
    """Set file descriptor to non-blocking mode."""
    if IS_WINDOWS:
        return

    fd = reader.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


class SafeSubprocess:
    """
    Safe subprocess executor with timeout and output limits.

    Executes commands in isolated process groups with configurable
    timeout and output size limits for security and reliability.
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_output_size: int = 65536,
        env: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize subprocess executor.

        Args:
            timeout_seconds: Maximum execution time before kill
            max_output_size: Maximum bytes to capture from stdout/stderr
            env: Environment variables for subprocess
        """
        if timeout_seconds < 0:
            raise ValueError("timeout_seconds must be non-negative")
        if max_output_size < 0:
            raise ValueError("max_output_size must be non-negative")
        self.timeout_seconds = timeout_seconds
        self.max_output_size = max_output_size
        self.env = env

    def _run_windows(
        self,
        process: Any,
        timeout: int,
        max_output: int,
        input_data: Optional[str] = None,
    ) -> "SubprocessResult":
        """Windows-specific process execution (no non-blocking I/O)."""
        try:
            encoded_input = (
                input_data.encode("utf-8") if input_data is not None else None
            )
            stdout_data, stderr_data = process.communicate(
                input=encoded_input, timeout=timeout
            )
            exit_code = process.poll()
            is_timeout = False
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_data, stderr_data = process.communicate()
            exit_code = process.poll()
            is_timeout = True

        stdout = stdout_data.decode("utf-8", errors="replace") if stdout_data else ""
        stderr = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""
        return SubprocessResult(
            timeout=is_timeout,
            exit_code=exit_code if exit_code is not None else -1,
            stdout=stdout[:max_output],
            stderr=stderr[:max_output],
        )

    def _drain_stream(
        self, stream: Any, chunks: list, bytes_read: int, max_output: int
    ) -> int:
        """Read available bytes without exceeding the capture limit."""
        try:
            data = stream.read(MAX_BYTES_PER_READ)
            if data and bytes_read < max_output:
                remaining = max_output - bytes_read
                captured = data[:remaining]
                chunks.append(captured)
                bytes_read += len(captured)
        except (BlockingIOError, TypeError) as _e:
            logger.debug(f"Ignorado: {_e}")
        return bytes_read

    def _run_with_input(
        self,
        process: Any,
        input_data: str,
        timeout: int,
        max_output: int,
    ) -> "SubprocessResult":
        """Run a process that needs bounded, non-interactive stdin."""
        encoded_input = input_data.encode("utf-8")
        timed_out = False
        try:
            stdout_data, stderr_data = process.communicate(
                input=encoded_input, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            with contextlib.suppress(ProcessLookupError, PermissionError):
                process_group_id = os.getpgid(process.pid)
                os.killpg(process_group_id, signal.SIGKILL)
            stdout_data, stderr_data = process.communicate()

        exit_code = process.poll()
        stdout = stdout_data.decode("utf-8", errors="replace") if stdout_data else ""
        stderr = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""
        return SubprocessResult(
            timeout=timed_out,
            exit_code=exit_code if exit_code is not None else -1,
            stdout=stdout[:max_output],
            stderr=stderr[:max_output],
        )

    def _run_posix(
        self,
        process: Any,
        timeout: int,
        max_output: int,
        input_data: Optional[str] = None,
    ) -> "SubprocessResult":
        """Collect POSIX process output while enforcing timeout and limits."""
        if input_data is not None:
            return self._run_with_input(process, input_data, timeout, max_output)

        _set_nonblocking(process.stdout)
        _set_nonblocking(process.stderr)

        try:
            process_group_id = os.getpgid(process.pid)
        except ProcessLookupError:
            process_group_id = process.pid

        deadline = time.monotonic() + timeout
        stdout_chunks: List[bytes] = []
        stderr_chunks: List[bytes] = []
        stdout_bytes_read = 0
        stderr_bytes_read = 0
        exit_code = process.poll()
        timed_out = False

        while exit_code is None:
            stdout_bytes_read = self._drain_stream(
                process.stdout, stdout_chunks, stdout_bytes_read, max_output
            )
            stderr_bytes_read = self._drain_stream(
                process.stderr, stderr_chunks, stderr_bytes_read, max_output
            )

            exit_code = process.poll()
            if exit_code is not None:
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(process_group_id, signal.SIGKILL)
                break
            time.sleep(min(SLEEP_BETWEEN_READS, remaining))

        try:
            stdout_read = process.stdout.read()
            if stdout_read and stdout_bytes_read < max_output:
                remaining = max_output - stdout_bytes_read
                stdout_chunks.append(stdout_read[:remaining])
        except (BlockingIOError, TypeError, ValueError, AttributeError) as _e:
            logger.debug(f"Ignorado: {_e}")

        try:
            stderr_read = process.stderr.read()
            if stderr_read and stderr_bytes_read < max_output:
                remaining = max_output - stderr_bytes_read
                stderr_chunks.append(stderr_read[:remaining])
        except (BlockingIOError, TypeError, ValueError, AttributeError) as _e:
            logger.debug(f"Ignorado: {_e}")

        if exit_code is None:
            exit_code = process.poll()
        is_timeout = timed_out

        # Close pipes to prevent ResourceWarning
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        if exit_code is None:
            process.wait()

        stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")

        return SubprocessResult(
            timeout=is_timeout,
            exit_code=exit_code if exit_code is not None else -1,
            stdout=stdout,
            stderr=stderr,
        )

    def run(
        self,
        args: List[str],
        timeout_seconds: Optional[int] = None,
        max_output_size: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
    ) -> "SubprocessResult":
        """
        Execute command with safety limits.

        Args:
            args: Command and arguments as list
            timeout_seconds: Override default timeout
            max_output_size: Override default output limit
            env: Override default environment
            cwd: Working directory for command

        Returns:
            SubprocessResult with execution details
        """
        timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        max_output = (
            self.max_output_size if max_output_size is None else max_output_size
        )
        if timeout < 0:
            raise ValueError("timeout_seconds must be non-negative")
        if max_output < 0:
            raise ValueError("max_output_size must be non-negative")
        process_env = self.env if env is None else env

        try:
            process = subprocess.Popen(
                args,
                env=process_env,
                cwd=cwd,
                stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                bufsize=MAX_BYTES_PER_READ,
            )
        except FileNotFoundError:
            return SubprocessResult(
                timeout=False,
                exit_code=127,
                stdout="",
                stderr=f"Command not found: {args[0]}",
            )
        except PermissionError:
            return SubprocessResult(
                timeout=False,
                exit_code=126,
                stdout="",
                stderr=f"Permission denied: {args[0]}",
            )

        if IS_WINDOWS:
            return self._run_windows(process, timeout, max_output, input_data)
        return self._run_posix(process, timeout, max_output, input_data)

    def run_shell(
        self,
        command: str,
        timeout_seconds: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> SubprocessResult:
        """
        Execute shell command string with security validation.

        Validates the command before execution with _is_safe_command()
        para prevenir command injection.

        Args:
            command: Shell command string
            timeout_seconds: Override default timeout
            cwd: Working directory for command

        Returns:
            SubprocessResult with execution details

        Raises:
            SecurityError: If command fails validation
        """
        from aura_cli.core.exceptions import SecurityError
        from aura_cli.core.logger import get_logger
        from aura_cli.core.tools.shell import _is_safe_command

        logger = get_logger(__name__)

        if not _is_safe_command(command):
            reason = "Command contains dangerous patterns or blocked commands"
            logger.warning(f"Unsafe command blocked: {command[:50]}...")
            raise SecurityError(command=command, reason=reason)

        logger.debug(f"Executing safe command: {command[:50]}...")

        if IS_WINDOWS:
            return self.run(
                ["cmd", "/c", command],
                timeout_seconds=timeout_seconds,
                cwd=cwd,
            )

        shell = os.environ.get("SHELL", "/bin/sh")
        return self.run(
            [shell, "-c", command],
            timeout_seconds=timeout_seconds,
            cwd=cwd,
        )


_default_executor: Optional[SafeSubprocess] = None


def get_safe_subprocess() -> SafeSubprocess:
    """Get default SafeSubprocess instance."""
    global _default_executor
    if _default_executor is None:
        _default_executor = SafeSubprocess()
    return _default_executor


def safe_run(
    args: List[str],
    timeout_seconds: int = 30,
    max_output_size: int = 65536,
    cwd: Optional[str] = None,
) -> SubprocessResult:
    """
    Convenience function for safe subprocess execution.

    Args:
        args: Command and arguments as list
        timeout_seconds: Maximum execution time
        max_output_size: Maximum output bytes
        cwd: Working directory

    Returns:
        SubprocessResult with execution details
    """
    executor = SafeSubprocess(
        timeout_seconds=timeout_seconds,
        max_output_size=max_output_size,
    )
    return executor.run(args, cwd=cwd)


def safe_shell(
    command: str,
    timeout_seconds: int = 30,
    cwd: Optional[str] = None,
) -> SubprocessResult:
    """
    Convenience function for safe shell command execution.

    Args:
        command: Shell command string
        timeout_seconds: Maximum execution time
        cwd: Working directory

    Returns:
        SubprocessResult with execution details
    """
    return get_safe_subprocess().run_shell(command, timeout_seconds, cwd)
