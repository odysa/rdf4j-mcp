"""SPARQL query validation tool for MCP."""

import json
from typing import Any

from mcp.types import TextContent, Tool
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.parser import parseUpdate


def get_validate_tools() -> list[Tool]:
    """Return SPARQL validation tool definitions."""
    return [
        Tool(
            name="sparql_validate",
            description=(
                "Parse and validate a SPARQL query without executing it. "
                "Returns the query type (SELECT/CONSTRUCT/ASK/DESCRIBE/UPDATE), "
                "projected variables, and any parse errors with location info."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SPARQL query to validate",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


VALIDATE_TOOL_NAMES = {"sparql_validate"}


async def handle_validate_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch a validate tool call to the appropriate handler."""
    if name == "sparql_validate":
        return await handle_sparql_validate(arguments)
    else:
        raise ValueError(f"Unknown validate tool: {name}")


# Map rdflib algebra names to user-facing query types
_QUERY_TYPE_MAP = {
    "SelectQuery": "SELECT",
    "ConstructQuery": "CONSTRUCT",
    "DescribeQuery": "DESCRIBE",
    "AskQuery": "ASK",
}


async def handle_sparql_validate(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle sparql_validate tool call."""
    query = arguments["query"]

    # Try parsing as a standard query (SELECT/CONSTRUCT/ASK/DESCRIBE) first
    result = _try_parse_query(query)
    if result is not None:
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # Try parsing as an UPDATE query
    result = _try_parse_update(query)
    if result is not None:
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # Both parsers failed -- return the query-parser error (more common case)
    return [TextContent(type="text", text=json.dumps(_parse_query_error(query), indent=2))]


def _try_parse_query(query: str) -> dict[str, Any] | None:
    """Try to parse as SELECT/CONSTRUCT/ASK/DESCRIBE. Return result dict or None."""
    try:
        prepared = prepareQuery(query)
    except Exception:
        return None

    algebra = prepared.algebra
    query_type = _QUERY_TYPE_MAP.get(algebra.name, algebra.name)

    result: dict[str, Any] = {"valid": True, "query_type": query_type}

    if query_type == "SELECT" and hasattr(algebra, "PV"):
        result["variables"] = [f"?{v}" for v in algebra.PV]

    return result


def _try_parse_update(query: str) -> dict[str, Any] | None:
    """Try to parse as a SPARQL UPDATE. Return result dict or None."""
    try:
        parsed = parseUpdate(query)
    except Exception:
        return None

    operations = []
    for req in parsed.request:
        operations.append(req.name)

    return {
        "valid": True,
        "query_type": "UPDATE",
        "operations": operations,
    }


def _parse_query_error(query: str) -> dict[str, Any]:
    """Return a structured error from attempting to parse as a query."""
    try:
        prepareQuery(query)
    except Exception as e:
        return {"valid": False, "error": str(e)}
    # Should not reach here since we call this after a known failure
    return {"valid": False, "error": "Unknown parse error"}
