"""Health and monitoring tools for the Ops agent.

Covers HTTP/HTTPS health checks (with status-code classification), TCP port
probing, system resource reporting (CPU/RAM/disk via psutil) and process
listing. All network operations respect configurable timeouts.
"""

import socket
from typing import Optional

import psutil
import requests
from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.ui import display_tool_call

logger = get_logger(__name__)
console = Console()


def check_service_health(url: str, timeout: int = 5) -> str:
    """Check HTTP/HTTPS service health."""
    display_tool_call("check_service_health", {"url": url, "timeout": timeout})
    logger.debug(f"Verificando saúde do serviço: {url}")

    try:
        response = requests.get(url, timeout=timeout)
        status_code = response.status_code

        if 200 <= status_code < 300:
            health_status = "✅ Healthy"
            color = "green"
        elif 300 <= status_code < 400:
            health_status = "!️ Redirect"
            color = "yellow"
        elif 400 <= status_code < 500:
            health_status = "❌ Client Error"
            color = "red"
        else:
            health_status = "❌ Server Error"
            color = "red"

        result = f"{health_status} - Status: {status_code} - Response Time: {response.elapsed.total_seconds():.2f}s"
        console.print(f"[{color}]{result}[/{color}]")
        logger.info(f"Serviço {url}: {health_status}")
        return result

    except requests.exceptions.Timeout:
        error_msg = f"Timeout ao verificar {url}"
        logger.warning(error_msg)
        return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = f"Erro de conexão com {url}"
        logger.warning(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error checking health: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def check_port(host: str, port: int, timeout: int = 3) -> str:
    """Checks whether a TCP port is open on a host. Use to verify if a service is running and reachable.

    Args:
        host: Hostname or IP address to check.
        port: Port number to test.
        timeout: Connection timeout in seconds (default: 3).
    """
    display_tool_call("check_port", {"host": host, "port": port, "timeout": timeout})
    logger.debug(f"Verificando porta {port} em {host}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            status_msg = f"✅ Porta {port} está aberta em {host}"
            console.print(f"[green]{status_msg}[/green]")
            logger.info(status_msg)
            return status_msg
        else:
            status_msg = f"❌ Porta {port} está fechada em {host}"
            console.print(f"[red]{status_msg}[/red]")
            logger.warning(status_msg)
            return status_msg

    except Exception as e:
        error_msg = f"Error checking port: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def system_resources() -> str:
    """Display system resources (CPU, RAM, Disk)."""
    display_tool_call("system_resources", {})
    logger.debug("Verificando recursos do sistema")

    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        table = Table(title="System Resources", show_header=True)
        table.add_column("Recurso", style="cyan")
        table.add_column("Uso", style="yellow")
        table.add_column("Disponível", style="green")

        table.add_row("CPU", f"{cpu_percent}%", f"{100 - cpu_percent}%")
        table.add_row(
            "RAM",
            f"{memory.percent}% ({memory.used / (1024**3):.2f} GB)",
            f"{memory.available / (1024**3):.2f} GB",
        )
        table.add_row(
            "Disk",
            f"{disk.percent}% ({disk.used / (1024**3):.2f} GB)",
            f"{disk.free / (1024**3):.2f} GB",
        )

        console.print(table)
        logger.info(
            f"Recursos: CPU={cpu_percent}%, RAM={memory.percent}%, Disk={disk.percent}%"
        )
        return "Recursos do sistema exibidos"

    except Exception as e:
        error_msg = f"Error fetching resources: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def process_info(name: Optional[str] = None) -> str:
    """Lists running processes with PID, CPU%, and memory%. Filter by name to find a specific service.

    Args:
        name: Process name to filter by (None = show all processes).
    """
    display_tool_call("process_info", {"name": name})
    logger.debug(f"Obtendo informações de processos: name={name}")

    try:
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                pinfo = proc.info
                if name is None or name.lower() in pinfo["name"].lower():
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not processes:
            return f"Nenhum processo encontrado{' com nome ' + name if name else ''}."

        table = Table(title="Process Info", show_header=True)
        table.add_column("PID", style="cyan")
        table.add_column("Nome", style="green")
        table.add_column("CPU %", style="yellow")
        table.add_column("RAM %", style="yellow")

        for proc in processes[:20]:  # Limita a 20 processos
            table.add_row(
                str(proc["pid"]),
                proc["name"],
                f"{proc['cpu_percent']:.1f}",
                f"{proc['memory_percent']:.1f}",
            )

        console.print(table)
        logger.info(f"Listados {len(processes)} processos")
        return f"Informações de {len(processes)} processos exibidas"

    except Exception as e:
        error_msg = f"Error fetching process information: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg
