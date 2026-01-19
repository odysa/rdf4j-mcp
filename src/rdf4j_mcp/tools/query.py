"""SPARQL query tools for MCP."""

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..backends.base import Backend
from ..config import get_settings


def register_query_tools(server: Server, get_backend: Any) -> None:
    """Register SPARQL query tools with the MCP server.

    Args:
        server: The MCP server instance
        get_backend: Callable that returns the backend instance
    """

    @server.list_tools()
    async def list_query_tools() -> list[Tool]:
        """List available SPARQL query tools."""
        return [
            Tool(
                name="sparql_select",
                description=(
                    "Execute a SPARQL SELECT query and return results as JSON. "
                    "Use this for queries that return tabular data with variable bindings."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SPARQL SELECT query to execute",
                        },
                        "repository_id": {
                            "type": "string",
                            "description": "Repository ID (uses default if not specified)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (applied if query has no LIMIT)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="sparql_construct",
                description=(
                    "Execute a SPARQL CONSTRUCT or DESCRIBE query and return results as Turtle. "
                    "Use this for queries that return RDF triples/graphs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SPARQL CONSTRUCT or DESCRIBE query to execute",
                        },
                        "repository_id": {
                            "type": "string",
                            "description": "Repository ID (uses default if not specified)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="sparql_ask",
                description=(
                    "Execute a SPARQL ASK query and return a boolean result. "
                    "Use this for yes/no questions about the data."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SPARQL ASK query to execute",
                        },
                        "repository_id": {
                            "type": "string",
                            "description": "Repository ID (uses default if not specified)",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_query_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle SPARQL query tool calls."""
        backend: Backend = get_backend()
        settings = get_settings()

        if name == "sparql_select":
            return await _handle_sparql_select(backend, arguments, settings)
        elif name == "sparql_construct":
            return await _handle_sparql_construct(backend, arguments)
        elif name == "sparql_ask":
            return await _handle_sparql_ask(backend, arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")


async def _handle_sparql_select(
    backend: Backend,
    arguments: dict[str, Any],
    settings: Any,
) -> list[TextContent]:
    """Handle sparql_select tool call."""
    query = arguments["query"]
    repository_id: str | None = arguments.get("repository_id")
    limit = arguments.get("limit")

    # Apply default limit if query doesn't have one
    query_upper = query.upper()
    if "LIMIT" not in query_upper:
        effective_limit = min(limit or settings.default_limit, settings.max_limit)
        query = f"{query}\nLIMIT {effective_limit}"
    elif limit:
        # Warn that limit parameter is ignored
        pass

    result = await backend.sparql_select(query, repository_id)

    # Format results
    output = {
        "type": "select",
        "variables": result.variables or [],
        "bindings": result.bindings or [],
        "count": len(result.bindings or []),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_sparql_construct(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle sparql_construct tool call."""
    query = arguments["query"]
    repository_id: str | None = arguments.get("repository_id")

    result = await backend.sparql_construct(query, repository_id)

    # Return Turtle format
    output = f"# SPARQL CONSTRUCT/DESCRIBE Result\n# Format: Turtle\n\n{result.triples or ''}"

    return [TextContent(type="text", text=output)]


async def _handle_sparql_ask(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle sparql_ask tool call."""
    query = arguments["query"]
    repository_id: str | None = arguments.get("repository_id")

    result = await backend.sparql_ask(query, repository_id)

    output = {"type": "ask", "result": result.boolean}

    return [TextContent(type="text", text=json.dumps(output, indent=2))]
