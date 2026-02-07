"""MCP Tools for RDF4J operations."""

import logging
from collections.abc import Callable
from typing import Any

from mcp.server import Server
from mcp.types import CallToolResult, TextContent, Tool

from ..backends.base import Backend
from ..config import get_settings
from ..exceptions import RDF4JError
from .explore import EXPLORE_TOOL_NAMES, get_explore_tools, handle_explore_tool
from .metadata import METADATA_TOOL_NAMES, get_metadata_tools, handle_metadata_tool
from .query import QUERY_TOOL_NAMES, get_query_tools, handle_query_tool
from .update import UPDATE_TOOL_NAMES, get_update_tools, handle_update_tool
from .validate import VALIDATE_TOOL_NAMES, get_validate_tools, handle_validate_tool

logger = logging.getLogger(__name__)


def register_all_tools(server: Server, get_backend: Callable[[], Backend]) -> None:
    """Register all tools with the MCP server.

    Collects tool definitions from all modules and registers a single
    list_tools handler and a single call_tool dispatcher.

    Args:
        server: The MCP server instance
        get_backend: Callable that returns the backend instance
    """

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return (
            get_query_tools()
            + get_explore_tools()
            + get_metadata_tools()
            + get_update_tools()
            + get_validate_tools()
        )

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent] | CallToolResult:
        backend = get_backend()
        settings = get_settings()

        try:
            if name in QUERY_TOOL_NAMES:
                return await handle_query_tool(name, arguments, backend, settings)
            elif name in EXPLORE_TOOL_NAMES:
                return await handle_explore_tool(name, arguments, backend)
            elif name in METADATA_TOOL_NAMES:
                return await handle_metadata_tool(name, arguments, backend)
            elif name in UPDATE_TOOL_NAMES:
                return await handle_update_tool(name, arguments, backend, settings)
            elif name in VALIDATE_TOOL_NAMES:
                return await handle_validate_tool(name, arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
        except RDF4JError as exc:
            logger.warning("Tool '%s' failed: %s", name, exc)
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {exc}")],
                isError=True,
            )


__all__ = ["register_all_tools"]
