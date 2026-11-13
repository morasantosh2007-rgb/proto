"""Tool router for coordinating execution of registered tools."""

import logging
from typing import Any, Dict, List, Optional
from jarvis.tools.base import ToolRegistry, ToolResult

logger = logging.getLogger("jarvis.brain.router")


class ToolRouter:
    """Dispatches tool calls with validation, dry-run support, and result aggregation."""

    def __init__(self, registry: Optional[ToolRegistry] = None, dry_run: bool = False):
        self.registry = registry or ToolRegistry.get_instance()
        self.dry_run = dry_run

    def execute_calls(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute a sequential list of tool calls, verifying each step."""
        results: List[ToolResult] = []
        for call in tool_calls:
            name = call.get("name", "")
            params = call.get("parameters", {})
            logger.info(f"Routing tool call: {name} (dry_run={self.dry_run})")
            tool = self.registry.get_tool(name)
            if not tool:
                results.append(
                    ToolResult(
                        success=False,
                        message=f"Unknown tool '{name}'",
                        data={"name": name},
                    )
                )
                continue

            try:
                res = tool.execute(params, dry_run=self.dry_run)
                results.append(res)
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                results.append(
                    ToolResult(
                        success=False,
                        message=f"Failed to execute {name}: {str(e)}",
                        error=str(e),
                    )
                )

        return results
