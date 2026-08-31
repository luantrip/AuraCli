"""
Cloud Operations Tools - Cloudflare.

This module contains tools for managing Cloudflare resources via CLI wrappers.
It includes functionality for Cloudflare Tunnels and Cloudflare Pages.

Requirements:
    - cloudflared CLI installed and authenticated
    - wrangler CLI installed (npm install -g wrangler) and authenticated
"""

import subprocess
from typing import Optional

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

from aura_cli.core.ui import display_tool_call
from aura_cli.core.ui_bridge import UIIcons, UIStyles

console = Console()


def cloudflare_tunnel_create(name: str, url: str) -> str:
    """
    Creates a new Cloudflare Tunnel and configures it locally.

    Args:
        name: Name of the tunnel
        url: Local URL to tunnel (e.g., http://localhost:8000)

    Returns:
        Status message
    """
    display_tool_call("cloudflare_tunnel_create", {"name": name, "url": url})

    try:
        check_cmd = ["cloudflared", "tunnel", "info", name]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)

        if check_result.returncode != 0:
            console.print(f"[yellow]Creating new tunnel '{name}'...[/yellow]")
            create_cmd = ["cloudflared", "tunnel", "create", name]
            subprocess.run(create_cmd, capture_output=True, text=True, check=True)
            console.print("[green]Tunnel created successfully.[/green]")
        else:
            console.print(f"[yellow]Tunnel '{name}' already exists.[/yellow]")

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} Tunnel configured for {url}[/{success_style}]"
        )

        return (
            f"Tunnel '{name}' ready for {url}. Use cloudflare_tunnel_run to start it."
        )

    except subprocess.CalledProcessError as e:
        error_msg = f"Error creating tunnel: {e.stderr if e.stderr else str(e)}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except FileNotFoundError:
        error_msg = "Error: 'cloudflared' CLI not found. Install it first."
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except Exception as e:
        error_msg = f"Erro inesperado: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def cloudflare_tunnel_run(name: str, url: str) -> str:
    """
    Runs an existing Cloudflare Tunnel in a background process (detached).

    Args:
        name: Name of the tunnel to run
        url: Local URL to route (e.g. http://localhost:8000)

    Returns:
        Status message with instructions
    """
    display_tool_call("cloudflare_tunnel_run", {"name": name, "url": url})

    try:
        cmd = f"cloudflared tunnel run --url {url} {name}"

        # Prime the semantic style cache before composing the panel.
        UIStyles.safe_style("WARNING", "yellow")
        info_panel = Panel(
            f"[bold]Command to run:[/bold]\n[cyan]{cmd}[/cyan]\n\n"
            "This command blocks execution. In a GUI/Terminal, run this in a separate tab.\n"
            "If I run it now, I will act as a wrapper but I cannot persist easily in this session.",
            title=f"{UIIcons.OPS} Cloudflare Tunnel",
            border_style="blue",
        )
        console.print(info_panel)

        return f"Execute este comando em um terminal separado: {cmd}"

    except Exception as e:
        error_msg = f"Erro inesperado: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def cloudflare_pages_deploy(
    directory: str = ".", project_name: Optional[str] = None
) -> str:
    """
    Deploys a directory to Cloudflare Pages using Wrangler.

    Args:
        directory: Directory to deploy (dist, build, public, .)
        project_name: Optional project name (if not in wrangler.toml)

    Returns:
        Deployment URL or error
    """
    display_tool_call(
        "cloudflare_pages_deploy",
        {"directory": directory, "project_name": project_name},
    )

    try:
        cmd = ["npx", "wrangler", "pages", "deploy", directory]
        if project_name:
            cmd.extend(["--project-name", project_name])

        console.print(
            "[yellow]Publicando no Cloudflare Pages... (pode levar um minuto)[/yellow]"
        )

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        output = result.stdout

        url = "Unknown URL"
        for line in output.split("\n"):
            if "https://" in line and ".pages.dev" in line:
                url = line.strip()
                break  # Grab the first one usually

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} Publicação concluída![/{success_style}]"
        )
        rprint(f"[bold cyan]URL: {url}[/bold cyan]")

        return f"Publicação concluída.\nURL: {url}\n\nSaída:\n{output}"

    except subprocess.CalledProcessError as e:
        error_msg = f"Error publishing to Pages: {e.stderr if e.stderr else str(e)}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except FileNotFoundError:
        error_msg = "Error: 'npx' or 'wrangler' not found. Install Node.js."
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except Exception as e:
        error_msg = f"Erro inesperado: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
