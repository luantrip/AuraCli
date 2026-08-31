"""Docker tools for the Ops agent via the official docker-py SDK.

Uses the Docker SDK (not CLI wrappers) for type-safe, platform-independent
container and image management. Covers: docker_ps, docker_images, docker_logs,
docker_exec, docker_build, docker_compose. docker-py must be installed.
"""

from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.ui import display_tool_call

logger = get_logger(__name__)
console = Console()

_docker_client = None
_docker_available = None


def _get_docker_client():
    """
    Get or create Docker client with lazy initialization.

    Returns:
        docker.DockerClient or None if Docker is unavailable
    """
    global _docker_client, _docker_available

    if _docker_available is False:
        return None

    if _docker_client is not None:
        return _docker_client

    import docker

    try:
        _docker_client = docker.from_env()
        _docker_client.ping()
        _docker_available = True
        logger.debug("Docker client initialized successfully")
        return _docker_client
    except Exception as e:
        _docker_available = False
        logger.warning(f"Docker daemon not available: {e}")
        return None


def is_docker_available() -> bool:
    """Check if Docker is available."""
    return _get_docker_client() is not None


def docker_ps(show_all: bool = False) -> Union[List[Dict[str, Any]], str]:
    """
    List Docker containers.

    Args:
        show_all: If True, list all containers (including stopped)

    Returns:
        List of container dictionaries or error message string
    """
    display_tool_call("docker_ps", {"all": show_all})
    logger.debug(f"Executing docker_ps: show_all={show_all}")

    client = _get_docker_client()
    if client is None:
        error_msg = (
            "Docker não disponível. Verifique se o Docker está instalado e rodando."
        )
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        containers = client.containers.list(all=show_all)

        if not containers:
            msg = "Nenhum container encontrado."
            console.print(f"[yellow]{msg}[/yellow]")
            return []

        results = []
        table = Table(title="🐳 Docker Containers")
        table.add_column("ID", style="cyan")
        table.add_column("Nome", style="green")
        table.add_column("Status")
        table.add_column("Imagem", style="blue")
        table.add_column("Portas", style="magenta")

        for container in containers:
            status = container.status
            status_styled = (
                f"[green]{status}[/green]"
                if status == "running"
                else f"[red]{status}[/red]"
            )

            ports = container.ports or {}
            port_mappings = []
            for container_port, host_bindings in ports.items():
                if host_bindings:
                    for binding in host_bindings:
                        host_port = binding.get("HostPort", "")
                        if host_port:
                            port_mappings.append(f"{host_port}->{container_port}")
                else:
                    port_mappings.append(container_port)
            ports_str = ", ".join(port_mappings[:3])  # Limit to 3 ports
            if len(port_mappings) > 3:
                ports_str += f" (+{len(port_mappings) - 3})"

            image_tags = container.image.tags if container.image.tags else []
            image_name = image_tags[0] if image_tags else container.image.short_id

            result = {
                "id": container.short_id,
                "name": container.name,
                "status": status,
                "image": image_name,
                "ports": ports,
                "created": container.attrs.get("Created", ""),
            }
            results.append(result)

            table.add_row(
                container.short_id,
                container.name,
                status_styled,
                image_name,
                ports_str,
            )

        console.print(table)
        summary = f"Total: {len(results)} container(s)"
        console.print(f"[green]{summary}[/green]")
        logger.info(f"Docker ps: {len(results)} containers")

        return results

    except Exception as e:
        error_msg = f"Error listing containers: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_images(
    name: Optional[str] = None, show_all: bool = False
) -> Union[List[Dict[str, Any]], str]:
    """
    List Docker images.

    Args:
        name: Filter by image name
        show_all: If True, show intermediate images

    Returns:
        List of image dictionaries or error message string
    """
    display_tool_call("docker_images", {"name": name, "all": show_all})
    logger.debug(f"Executing docker_images: name={name}, all={show_all}")

    client = _get_docker_client()
    if client is None:
        error_msg = (
            "Docker não disponível. Verifique se o Docker está instalado e rodando."
        )
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        images = client.images.list(name=name, all=show_all)

        if not images:
            msg = "Nenhuma imagem encontrada."
            console.print(f"[yellow]{msg}[/yellow]")
            return []

        results = []
        table = Table(title="🐳 Docker Images")
        table.add_column("Repositório", style="cyan")
        table.add_column("Tag", style="yellow")
        table.add_column("ID", style="dim")
        table.add_column("Tamanho", style="green")

        for image in images:
            size_bytes = image.attrs.get("Size", 0)
            if size_bytes >= 1024**3:
                size_str = f"{size_bytes / (1024**3):.1f} GB"
            elif size_bytes >= 1024**2:
                size_str = f"{size_bytes / (1024**2):.1f} MB"
            else:
                size_str = f"{size_bytes / 1024:.1f} KB"

            if image.tags:
                for tag in image.tags:
                    parts = tag.split(":")
                    repo = parts[0]
                    tag_name = parts[1] if len(parts) > 1 else "latest"

                    result = {
                        "id": image.short_id,
                        "repository": repo,
                        "tag": tag_name,
                        "size": size_bytes,
                        "size_human": size_str,
                        "created": image.attrs.get("Created", ""),
                    }
                    results.append(result)
                    table.add_row(repo, tag_name, image.short_id, size_str)
            else:
                result = {
                    "id": image.short_id,
                    "repository": "<none>",
                    "tag": "<none>",
                    "size": size_bytes,
                    "size_human": size_str,
                }
                results.append(result)
                table.add_row("<none>", "<none>", image.short_id, size_str)

        console.print(table)
        summary = f"Total: {len(results)} imagem(ns)"
        console.print(f"[green]{summary}[/green]")
        logger.info(f"Docker images: {len(results)} images")

        return results

    except Exception as e:
        error_msg = f"Error listing images: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_logs(
    container: str,
    tail: int = 100,
    follow: bool = False,
    timestamps: bool = False,
    since: Optional[str] = None,
) -> Union[str, List[str]]:
    """
    Get logs from a container.

    Args:
        container: Container name or ID
        tail: Number of lines to show from end
        follow: If True, stream logs (returns generator)
        timestamps: If True, include timestamps
        since: Show logs since timestamp (e.g., "2023-01-01", "10m", "1h")

    Returns:
        Log content as string or error message
    """
    display_tool_call(
        "docker_logs", {"container": container, "tail": tail, "follow": follow}
    )
    logger.debug(f"Executing docker_logs: container={container}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        try:
            container_obj = client.containers.get(container)
        except Exception:
            containers = client.containers.list(all=True)
            matches = [
                c
                for c in containers
                if c.name.startswith(container) or c.short_id.startswith(container)
            ]
            if not matches:
                error_msg = f"Container '{container}' not found."
                console.print(f"[red]{error_msg}[/red]")
                return error_msg
            container_obj = matches[0]

        logs = container_obj.logs(
            tail=tail,
            timestamps=timestamps,
            stream=follow,
            since=since,
        )

        if follow:
            console.print(f"[blue]Streaming logs de {container_obj.name}...[/blue]")
            return logs
        else:
            if isinstance(logs, bytes):
                log_content = logs.decode("utf-8", errors="replace")
            else:
                log_content = str(logs)

            if not log_content.strip():
                msg = f"Nenhum log encontrado para container '{container_obj.name}'."
                console.print(f"[yellow]{msg}[/yellow]")
                return msg

            console.print(
                Panel(
                    log_content,
                    title=f"Logs: {container_obj.name}",
                    border_style="blue",
                )
            )
            logger.info(f"Docker logs: container={container_obj.name}")
            return log_content

    except Exception as e:
        error_msg = f"Error fetching logs: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_exec(
    container: str,
    command: Union[str, List[str]],
    workdir: Optional[str] = None,
    user: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
    detach: bool = False,
) -> Union[Dict[str, Any], str]:
    """
    Execute a command inside a running container.

    Args:
        container: Container name or ID
        command: Command to execute (string or list)
        workdir: Working directory inside container
        user: User to run command as
        environment: Environment variables
        detach: If True, run in background

    Returns:
        Dict with exit_code and output, or error message
    """
    display_tool_call("docker_exec", {"container": container, "command": command})
    logger.debug(f"Executing docker_exec: container={container}, command={command}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        container_obj = client.containers.get(container)

        if container_obj.status != "running":
            error_msg = f"Container '{container}' não está rodando (status: {container_obj.status})"
            console.print(f"[red]{error_msg}[/red]")
            return error_msg

        if isinstance(command, str):
            cmd = command.split() if " " in command else [command]
        else:
            cmd = command

        result = container_obj.exec_run(
            cmd=cmd,
            workdir=workdir,
            user=user,
            environment=environment,
            detach=detach,
        )

        if detach:
            msg = f"Command running in background on container {container}"
            console.print(f"[green]{msg}[/green]")
            return {"status": "detached", "message": msg}

        output = (
            result.output.decode("utf-8", errors="replace") if result.output else ""
        )
        exit_code = result.exit_code

        result_dict = {
            "exit_code": exit_code,
            "output": output,
            "container": container_obj.name,
        }

        if exit_code == 0:
            console.print(
                Panel(
                    output or "(no output)",
                    title=f"Exec: {container_obj.name}",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    output or "(no output)",
                    title=f"Exec Failed (exit {exit_code}): {container_obj.name}",
                    border_style="red",
                )
            )

        logger.info(
            f"Docker exec: container={container_obj.name}, exit_code={exit_code}"
        )
        return result_dict

    except Exception as e:
        error_msg = f"Error executing command: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_build(
    path: str,
    tag: str,
    dockerfile: str = "Dockerfile",
    buildargs: Optional[Dict[str, str]] = None,
    nocache: bool = False,
    pull: bool = False,
) -> Union[Dict[str, Any], str]:
    """
    Build a Docker image.

    Args:
        path: Path to build context
        tag: Tag for the built image
        dockerfile: Dockerfile path (relative to context)
        buildargs: Build arguments
        nocache: If True, don't use cache
        pull: If True, always pull base image

    Returns:
        Dict with image info or error message
    """
    display_tool_call(
        "docker_build", {"path": path, "tag": tag, "dockerfile": dockerfile}
    )
    logger.debug(f"Executing docker_build: path={path}, tag={tag}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    import os

    if not os.path.exists(path):
        error_msg = f"Path not found: {path}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    dockerfile_path = os.path.join(path, dockerfile)
    if not os.path.exists(dockerfile_path):
        error_msg = f"Dockerfile not found: {dockerfile_path}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        console.print(f"[blue]🔨 Construindo imagem {tag}...[/blue]")

        image, build_logs = client.images.build(
            path=path,
            tag=tag,
            dockerfile=dockerfile,
            buildargs=buildargs or {},
            nocache=nocache,
            pull=pull,
            rm=True,  # Remove intermediate containers
        )

        for log in build_logs:
            if "stream" in log:
                stream_msg = log["stream"].strip()
                if stream_msg:
                    console.print(f"[dim]{stream_msg}[/dim]")
            elif "error" in log:
                error_msg = f"Build error: {log['error']}"
                console.print(f"[red]{error_msg}[/red]")
                return error_msg

        result = {
            "id": image.short_id,
            "tags": image.tags,
            "size": image.attrs.get("Size", 0),
        }

        success_msg = f"✅ Imagem {tag} construída com sucesso (ID: {image.short_id})"
        logger.info(success_msg)
        console.print(f"[green]{success_msg}[/green]")

        return result

    except Exception as e:
        error_msg = f"Error building image: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_run(
    image: str,
    command: Optional[Union[str, List[str]]] = None,
    name: Optional[str] = None,
    detach: bool = True,
    ports: Optional[Dict[str, int]] = None,
    volumes: Optional[Dict[str, Dict[str, str]]] = None,
    environment: Optional[Dict[str, str]] = None,
    network: Optional[str] = None,
    remove: bool = False,
) -> Union[Dict[str, Any], str]:
    """
    Run a new container.

    Args:
        image: Image to run
        command: Command to run in container
        name: Container name
        detach: If True, run in background
        ports: Port mappings {container_port: host_port}
        volumes: Volume mappings {host_path: {"bind": container_path, "mode": "rw"}}
        environment: Environment variables
        network: Network to connect to
        remove: If True, remove container when it exits

    Returns:
        Dict with container info or error message
    """
    display_tool_call("docker_run", {"image": image, "name": name, "detach": detach})
    logger.debug(f"Executing docker_run: image={image}, name={name}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        console.print(f"[blue]🚀 Iniciando container de {image}...[/blue]")

        container = client.containers.run(
            image=image,
            command=command,
            name=name,
            detach=detach,
            ports=ports,
            volumes=volumes,
            environment=environment,
            network=network,
            remove=remove,
        )

        if detach:
            result = {
                "id": container.short_id,
                "name": container.name,
                "status": container.status,
                "image": image,
            }
            success_msg = (
                f"✅ Container {container.name} iniciado (ID: {container.short_id})"
            )
        else:
            result = {
                "output": container.decode("utf-8", errors="replace")
                if isinstance(container, bytes)
                else str(container),
            }
            success_msg = "✅ Container started successfully"

        logger.info(success_msg)
        console.print(f"[green]{success_msg}[/green]")

        return result

    except Exception as e:
        error_msg = f"Error running container: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_stop(
    container: str,
    timeout: int = 10,
) -> Union[Dict[str, Any], str]:
    """
    Stop a running container.

    Args:
        container: Container name or ID
        timeout: Seconds to wait before killing

    Returns:
        Dict with status or error message
    """
    display_tool_call("docker_stop", {"container": container})
    logger.debug(f"Executing docker_stop: container={container}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        container_obj = client.containers.get(container)
        container_obj.stop(timeout=timeout)

        result = {
            "id": container_obj.short_id,
            "name": container_obj.name,
            "status": "stopped",
        }

        success_msg = f"✅ Container {container_obj.name} parado"
        logger.info(success_msg)
        console.print(f"[green]{success_msg}[/green]")

        return result

    except Exception as e:
        error_msg = f"Error stopping container: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_rm(
    container: str,
    force: bool = False,
    volumes: bool = False,
) -> Union[Dict[str, Any], str]:
    """
    Remove a container.

    Args:
        container: Container name or ID
        force: If True, force removal of running container
        volumes: If True, also remove volumes

    Returns:
        Dict with status or error message
    """
    display_tool_call("docker_rm", {"container": container, "force": force})
    logger.debug(f"Executing docker_rm: container={container}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        container_obj = client.containers.get(container)
        container_name = container_obj.name
        container_obj.remove(force=force, v=volumes)

        result = {
            "name": container_name,
            "status": "removed",
        }

        success_msg = f"✅ Container {container_name} removed"
        logger.info(success_msg)
        console.print(f"[green]{success_msg}[/green]")

        return result

    except Exception as e:
        error_msg = f"Error removing container: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_compose(
    action: str,
    file: str = "docker-compose.yml",
    project_name: Optional[str] = None,
    services: Optional[List[str]] = None,
) -> Union[Dict[str, Any], str]:
    """
    Execute docker-compose actions.

    Note: This function uses subprocess for docker-compose as the
    compose library has different API patterns.

    Args:
        action: Action to perform (up, down, restart, ps, logs, build)
        file: Compose file path
        project_name: Project name override
        services: Specific services to target

    Returns:
        Dict with result or error message
    """
    import os
    import subprocess

    display_tool_call("docker_compose", {"action": action, "file": file})
    logger.debug(f"Executing docker_compose: action={action}")

    if not os.path.exists(file):
        error_msg = f"Compose file not found: {file}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        cmd_base = None
        for compose_cmd in [["docker", "compose"], ["docker-compose"]]:
            try:
                test_result = subprocess.run(
                    [*compose_cmd, "version"],
                    capture_output=True,
                    timeout=5,
                )
                if test_result.returncode == 0:
                    cmd_base = compose_cmd
                    break
            except Exception:
                continue

        if cmd_base is None:
            error_msg = "Docker Compose not found. Install Docker Compose."
            console.print(f"[red]{error_msg}[/red]")
            return error_msg

        cmd = [*cmd_base, "-f", file]

        if project_name:
            cmd.extend(["-p", project_name])

        cmd.append(action)

        if action == "up":
            cmd.append("-d")  # Always detach for up

        if services:
            cmd.extend(services)

        console.print(f"[blue]🐳 Executando: {' '.join(cmd)}[/blue]")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            output = result.stdout or result.stderr or "Operação concluída"
            success_msg = f"✅ Docker Compose {action} executed successfully"
            logger.info(success_msg)
            console.print(f"[green]{success_msg}[/green]")
            if output.strip():
                console.print(
                    Panel(output, title=f"Compose {action}", border_style="green")
                )
            return {"status": "success", "action": action, "output": output}
        else:
            error_msg = f"Erro no docker-compose: {result.stderr}"
            logger.error(error_msg)
            console.print(f"[red]{error_msg}[/red]")
            return error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Timeout ao executar docker-compose"
        logger.error(error_msg)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg
    except Exception as e:
        error_msg = f"Error running docker-compose: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


def docker_inspect(
    container_or_image: str,
) -> Union[Dict[str, Any], str]:
    """
    Get detailed information about a container or image.

    Args:
        container_or_image: Container/image name or ID

    Returns:
        Dict with detailed info or error message
    """
    display_tool_call("docker_inspect", {"target": container_or_image})
    logger.debug(f"Executing docker_inspect: {container_or_image}")

    client = _get_docker_client()
    if client is None:
        error_msg = "Docker não disponível."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    try:
        try:
            obj = client.containers.get(container_or_image)
            obj_type = "container"
        except Exception:
            obj = client.images.get(container_or_image)
            obj_type = "image"

        info = obj.attrs

        console.print(
            Panel(
                f"Type: {obj_type}\n"
                f"ID: {info.get('Id', 'N/A')[:12]}\n"
                f"Created: {info.get('Created', 'N/A')}\n",
                title=f"Inspect: {container_or_image}",
                border_style="blue",
            )
        )

        return info

    except Exception as e:
        error_msg = f"Error inspecting: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        return error_msg
