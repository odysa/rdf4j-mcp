"""Repository metadata tools for MCP."""

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..backends.base import Backend


def register_metadata_tools(server: Server, get_backend: Any) -> None:
    """Register repository metadata tools with the MCP server.

    Args:
        server: The MCP server instance
        get_backend: Callable that returns the backend instance
    """

    @server.list_tools()
    async def list_metadata_tools() -> list[Tool]:
        """List available metadata tools."""
        return [
            Tool(
                name="list_repositories",
                description=(
                    "List all available RDF repositories. "
                    "Returns repository IDs, titles, and access permissions."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_namespaces",
                description=(
                    "Get namespace prefix mappings for a repository. "
                    "Returns prefix-namespace pairs for use in SPARQL queries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repository_id": {
                            "type": "string",
                            "description": "Repository ID (uses default if not specified)",
                        },
                    },
                },
            ),
            Tool(
                name="get_statistics",
                description=(
                    "Get statistics about a repository including triple counts, "
                    "class counts, property counts, and more."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repository_id": {
                            "type": "string",
                            "description": "Repository ID (uses default if not specified)",
                        },
                    },
                },
            ),
            Tool(
                name="select_repository",
                description=(
                    "Select a repository to use as the default for subsequent operations. "
                    "This persists until another repository is selected."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repository_id": {
                            "type": "string",
                            "description": "Repository ID to select",
                        },
                    },
                    "required": ["repository_id"],
                },
            ),
            Tool(
                name="get_current_repository",
                description=("Get the currently selected default repository ID."),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def handle_metadata_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle metadata tool calls."""
        backend: Backend = get_backend()

        if name == "list_repositories":
            return await _handle_list_repositories(backend)
        elif name == "get_namespaces":
            return await _handle_get_namespaces(backend, arguments)
        elif name == "get_statistics":
            return await _handle_get_statistics(backend, arguments)
        elif name == "select_repository":
            return await _handle_select_repository(backend, arguments)
        elif name == "get_current_repository":
            return await _handle_get_current_repository(backend)
        else:
            raise ValueError(f"Unknown tool: {name}")


async def _handle_list_repositories(backend: Backend) -> list[TextContent]:
    """Handle list_repositories tool call."""
    repos = await backend.list_repositories()

    output = {
        "type": "repositories",
        "count": len(repos),
        "repositories": [
            {
                "id": repo.id,
                "title": repo.title,
                "uri": repo.uri,
                "readable": repo.readable,
                "writable": repo.writable,
            }
            for repo in repos
        ],
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_get_namespaces(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_namespaces tool call."""
    repository_id: str | None = arguments.get("repository_id")

    namespaces = await backend.get_namespaces(repository_id)

    output = {
        "type": "namespaces",
        "count": len(namespaces),
        "namespaces": [{"prefix": ns.prefix, "namespace": ns.namespace} for ns in namespaces],
        "sparql_prefixes": _format_sparql_prefixes(namespaces),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_get_statistics(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_statistics tool call."""
    repository_id: str | None = arguments.get("repository_id")

    stats = await backend.get_statistics(repository_id)

    output = {
        "type": "statistics",
        "total_statements": stats.total_statements,
        "total_classes": stats.total_classes,
        "total_properties": stats.total_properties,
        "total_subjects": stats.total_subjects,
        "total_objects": stats.total_objects,
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_select_repository(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle select_repository tool call."""
    repository_id = arguments["repository_id"]

    await backend.select_repository(repository_id)

    output = {
        "type": "repository_selected",
        "repository_id": repository_id,
        "message": f"Repository '{repository_id}' is now the default.",
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_get_current_repository(backend: Backend) -> list[TextContent]:
    """Handle get_current_repository tool call."""
    current = await backend.get_current_repository()

    output = {
        "type": "current_repository",
        "repository_id": current,
        "message": f"Current repository: {current}" if current else "No repository selected",
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


def _format_sparql_prefixes(namespaces: list[Any]) -> str:
    """Format namespaces as SPARQL PREFIX declarations."""
    lines = []
    for ns in namespaces:
        if ns.prefix:
            lines.append(f"PREFIX {ns.prefix}: <{ns.namespace}>")
    return "\n".join(lines)
