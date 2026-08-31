"""Tool chain system.

Provides sequential execution of multiple tools with data passing between them.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import uuid

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class ChainLink:
    """A single link in a tool execution chain."""

    id: str
    tool_name: str
    tool_func: Callable
    input_mapping: Callable[[Dict[str, Any]], Dict[str, Any]]
    output_mapping: Optional[Callable[[Any, Dict[str, Any]], Dict[str, Any]]] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class ToolChain:
    """Executes a sequence of tool calls as a pipeline."""

    chain_id: str
    name: str
    description: str
    links: List[ChainLink] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class ChainExecutor:
    """Tool chain executor."""

    def __init__(self):
        """Initialise the chain executor."""
        self.stats = get_stats()
        self.execution_history: List[Dict[str, Any]] = []

        logger.info("ChainExecutor initialized")

    def execute_chain(
        self, chain: ToolChain, initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a tool chain and return all results."""
        logger.info(f"Executando chain '{chain.name}' ({len(chain.links)} links)")

        context = {**chain.context, **(initial_context or {})}
        results = {}

        for i, link in enumerate(chain.links):
            if link.condition and not link.condition(context):
                logger.debug(
                    f"Link {i + 1} ({link.tool_name}) pulado devido a condição"
                )
                continue

            try:
                parameters = link.input_mapping(context)

                logger.debug(
                    f"Executando link {i + 1}/{len(chain.links)}: {link.tool_name}"
                )

                result = link.tool_func(**parameters)

                results[link.id] = {
                    "tool_name": link.tool_name,
                    "result": result,
                    "success": True,
                }

                if link.output_mapping:
                    context = link.output_mapping(result, context)
                else:
                    context[link.tool_name] = result
                    context["last_result"] = result

                logger.debug(f"Link {i + 1} ({link.tool_name}) executed successfully")

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"Link {i + 1} ({link.tool_name}) falhou: {error_msg}",
                    exc_info=True,
                )

                results[link.id] = {
                    "tool_name": link.tool_name,
                    "error": error_msg,
                    "success": False,
                }

                break

        execution_record = {
            "chain_id": chain.chain_id,
            "name": chain.name,
            "links_executed": len([r for r in results.values() if r.get("success")]),
            "total_links": len(chain.links),
            "success": all(r.get("success", False) for r in results.values()),
        }
        self.execution_history.append(execution_record)

        self.stats.track_tool_usage("chain_executor")

        logger.info(
            f"Chain '{chain.name}' concluída: "
            f"{execution_record['links_executed']}/{execution_record['total_links']} links"
        )

        return {
            "chain_id": chain.chain_id,
            "success": execution_record["success"],
            "results": results,
            "final_context": context,
        }

    def create_chain(
        self, name: str, description: str, links: List[Dict[str, Any]]
    ) -> ToolChain:
        """Create a new tool chain."""
        chain_id = str(uuid.uuid4())[:8]

        chain_links = []
        for link_data in links:
            link = ChainLink(
                id=link_data.get("id", str(uuid.uuid4())[:8]),
                tool_name=link_data["tool_name"],
                tool_func=link_data["tool_func"],
                input_mapping=link_data.get("input_mapping", lambda ctx: {}),
                output_mapping=link_data.get("output_mapping"),
                condition=link_data.get("condition"),
            )
            chain_links.append(link)

        chain = ToolChain(
            chain_id=chain_id, name=name, description=description, links=chain_links
        )

        logger.info(f"Chain '{name}' criada com {len(chain_links)} links")

        return chain

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Return the execution history as a list."""
        return self.execution_history.copy()
