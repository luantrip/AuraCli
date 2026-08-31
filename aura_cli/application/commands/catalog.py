"""Single source of truth for slash commands (TUI suggestions + autocomplete)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SlashCommand:
    name: str
    description_pt: str
    description_en: str = ""
    aliases: Tuple[str, ...] = ()
    subcommands: Tuple[str, ...] = ()
    tui_handler: bool = False
    tui_only: bool = False
    cli_only: bool = False


def _en(pt: str, en: str = "") -> str:
    return en or pt


SLASH_COMMANDS: List[SlashCommand] = [
    SlashCommand("/help", "Mostrar ajuda", "Show help", tui_handler=True),
    SlashCommand("/clear", "Limpar histórico do chat", "Clear chat", tui_handler=True),
    SlashCommand("/cls", "Limpar chat (alias)", "Clear chat (alias)", tui_handler=True),
    SlashCommand(
        "/keyboard",
        "Mostrar atalhos de teclado",
        "Show keyboard shortcuts",
        aliases=("/keys", "/shortcuts"),
        tui_handler=True,
    ),
    SlashCommand(
        "/back", "Voltar à CLI legada", "Return to legacy CLI", tui_handler=True
    ),
    SlashCommand("/exit", "Sair do Aura CLI", "Exit application", tui_handler=True),
    SlashCommand("/quit", "Sair (alias)", "Quit (alias)", tui_handler=True),
    SlashCommand(
        "/settings",
        "Abrir configurações (TUI nativo)",
        "Open settings",
        tui_handler=True,
        tui_only=True,
    ),
    SlashCommand(
        "/sessions",
        "Histórico de sessões salvas",
        "Browse saved sessions",
        aliases=("/session-history",),
        tui_handler=True,
        tui_only=True,
    ),
    SlashCommand(
        "/history",
        "No TUI: histórico de comandos do input",
        "Command input history",
        tui_handler=True,
    ),
    SlashCommand(
        "/constitution",
        "Criar constituição do projeto",
        "Constitution wizard",
        aliases=("/constituicao",),
        tui_handler=True,
        tui_only=True,
    ),
    SlashCommand(
        "/tools",
        "Abrir ferramentas opcionais",
        "Optional tool launchers",
        aliases=("/tools-menu",),
        tui_handler=True,
    ),
    SlashCommand("/tool", "Detalhes de ferramenta", "Tool details"),
    SlashCommand(
        "/agi",
        "Iniciar agente AGI",
        "AGI agent",
        subcommands=("task", "status", "stop"),
    ),
    SlashCommand(
        "/ops", "Agente DevOps", "Ops agent", subcommands=("list", "run", "status")
    ),
    SlashCommand(
        "/model",
        "Gerenciar modelos de IA",
        "Model settings",
        subcommands=("list", "set", "info"),
    ),
    SlashCommand(
        "/consolidate",
        "Consolidar regras aprendidas",
        "Consolidate rules",
        tui_handler=True,
    ),
    SlashCommand(
        "/welcome",
        "Boas-vindas e comandos rápidos",
        "Show welcome message",
        tui_handler=True,
    ),
    SlashCommand(
        "/todo",
        "Lista de tarefas",
        "Todo list",
        subcommands=("add", "done", "list", "clear"),
    ),
    SlashCommand("/init", "Inicializar contexto do projeto", "Initialize project"),
    SlashCommand(
        "/context",
        "Abrir workspace e contexto do projeto",
        "Open project workspace and context",
        tui_handler=True,
    ),
    SlashCommand(
        "/files",
        "Abrir gerenciador de arquivos externo",
        "Open external file manager",
        tui_handler=True,
    ),
    SlashCommand("/notebook", "Status do notebook", "Notebook status"),
    SlashCommand("/theme", "Mudar tema", "Change theme"),
    SlashCommand(
        "/dev", "Status de LLM local", "Local LLM status", subcommands=("status",)
    ),
    SlashCommand("/extensions", "Listar extensões", "List extensions"),
    SlashCommand("/interface", "Modo TUI", "TUI mode"),
    SlashCommand("/tui", "Modo TUI (alias)", "TUI mode (alias)"),
    SlashCommand("/cost", "Custo estimado", "Estimated cost"),
    SlashCommand(
        "/dashboard",
        "Dashboards",
        "Dashboards",
        subcommands=("tool_history", "memory", "graph", "infra", "extensions", "help"),
    ),
    SlashCommand("/memory", "Memória", "Memory"),
    SlashCommand(
        "/workflow",
        "Workflows",
        "Workflows",
        subcommands=("list", "run", "create", "delete", "info"),
    ),
    SlashCommand(
        "/auto-run",
        "Alternar execução sem confirmação",
        "Toggle auto-run",
        aliases=("/autorun",),
    ),
    SlashCommand(
        "/cache",
        "Cache (stats/clear)",
        "Cache management",
        subcommands=("stats", "clear"),
    ),
    SlashCommand(
        "/config",
        "Configuração do sistema",
        "System config",
        subcommands=("show", "set", "reset"),
    ),
    SlashCommand(
        "/checkpoint",
        "Pontos de restauração da conversa",
        "Conversation checkpoints",
        subcommands=("init", "create", "list", "restore", "hard"),
        tui_handler=True,
    ),
    SlashCommand(
        "/tangent",
        "Conversas paralelas",
        "Parallel conversations",
        subcommands=("tail",),
        tui_handler=True,
    ),
    SlashCommand(
        "/session",
        "Gerencia sessões (save, load, list, delete, info)",
        "Session management",
        subcommands=("save", "load", "list", "delete", "info"),
        cli_only=True,
    ),
    SlashCommand(
        "/resume",
        "Retomar uma sessão por ID, prefixo ou nome",
        "Resume a session by ID, prefix, or name",
        cli_only=True,
    ),
]


def _all_names() -> List[str]:
    names: List[str] = []
    for cmd in SLASH_COMMANDS:
        names.append(cmd.name)
        names.extend(cmd.aliases)
    return names


def command_names(*, tui: bool = True, cli: bool = True) -> List[str]:
    out: List[str] = []
    for cmd in SLASH_COMMANDS:
        if tui and cmd.cli_only:
            continue
        if cli and cmd.tui_only:
            continue
        out.append(cmd.name)
        if tui:
            out.extend(cmd.aliases)
    return sorted(set(out))


def slash_command_pairs(locale: str = "pt") -> List[Tuple[str, str]]:
    use_en = locale.lower().startswith("en")
    pairs: List[Tuple[str, str]] = []
    for cmd in SLASH_COMMANDS:
        desc = (
            cmd.description_en if use_en and cmd.description_en else cmd.description_pt
        )
        pairs.append((cmd.name, desc))
        for alias in cmd.aliases:
            pairs.append((alias, desc))
    return pairs


def command_dict_for_autocomplete(locale: str = "pt") -> Dict[str, dict]:
    use_en = locale.lower().startswith("en")
    result: Dict[str, dict] = {}
    for cmd in SLASH_COMMANDS:
        desc = (
            cmd.description_en if use_en and cmd.description_en else cmd.description_pt
        )
        entry = {"desc": desc, "subcommands": list(cmd.subcommands)}
        result[cmd.name] = entry
        for alias in cmd.aliases:
            result[alias] = entry
    return result


def tui_handled_commands() -> List[str]:
    names: List[str] = []
    for cmd in SLASH_COMMANDS:
        if cmd.tui_handler:
            names.append(cmd.name)
            names.extend(cmd.aliases)
    return names
