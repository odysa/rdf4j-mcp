"""SPARQL UPDATE tool for MCP."""

import json
import re
from typing import Any

from mcp.types import TextContent, Tool

from ..backends.base import Backend
from ..config import Settings

# Dangerous SPARQL Update operations that could destroy data
_DANGEROUS_OPS = re.compile(
    r"\b(DROP|CLEAR|CREATE|LOAD|COPY|MOVE|ADD)\b",
    re.IGNORECASE,
)

# Allowed SPARQL Update operations
_ALLOWED_OPS = re.compile(
    r"\b(INSERT\s+DATA|DELETE\s+DATA|INSERT|DELETE|WITH)\b",
    re.IGNORECASE,
)


def get_update_tools() -> list[Tool]:
    """Return SPARQL UPDATE tool definitions."""
    return [
        Tool(
            name="sparql_update",
            description=(
                "Execute a SPARQL UPDATE query to modify data in the repository. "
                "Supports INSERT DATA, DELETE DATA, and INSERT/DELETE WHERE patterns. "
                "Dangerous operations (DROP, CLEAR, CREATE, LOAD, COPY, MOVE, ADD) are blocked. "
                "Requires read_only=False in server configuration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SPARQL UPDATE query to execute",
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


UPDATE_TOOL_NAMES = {"sparql_update"}


async def handle_update_tool(
    name: str, arguments: dict[str, Any], backend: Backend, settings: Settings
) -> list[TextContent]:
    """Dispatch an update tool call to the appropriate handler."""
    if name == "sparql_update":
        return await handle_sparql_update(backend, arguments, settings)
    else:
        raise ValueError(f"Unknown update tool: {name}")


async def handle_sparql_update(
    backend: Backend,
    arguments: dict[str, Any],
    settings: Settings,
) -> list[TextContent]:
    """Handle sparql_update tool call."""
    if settings.read_only:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Server is in read-only mode. "
                        "Set RDF4J_MCP_READ_ONLY=false to enable updates."
                    }
                ),
            )
        ]

    query = arguments["query"]
    repo_id = arguments.get("repository_id")

    # Check for dangerous operations
    if _DANGEROUS_OPS.search(query):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Dangerous operation detected. "
                        "DROP, CLEAR, CREATE, LOAD, COPY, MOVE, and ADD are not allowed."
                    }
                ),
            )
        ]

    # Verify the query contains at least one allowed operation
    if not _ALLOWED_OPS.search(query):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "No valid update operation found. "
                        "Supported: INSERT DATA, DELETE DATA, INSERT/DELETE WHERE."
                    }
                ),
            )
        ]

    result = await backend.sparql_update(query, repo_id)
    return [
        TextContent(
            type="text",
            text=json.dumps({"status": result}),
        )
    ]
