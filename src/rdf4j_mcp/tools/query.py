"""SPARQL query tools for MCP."""

import json
import re
from typing import Any

from mcp.types import TextContent, Tool

from ..backends.base import Backend
from ..config import Settings

# Basic IRI validation pattern
_IRI_PATTERN = re.compile(r"^https?://[^\s<>\"{}|\\^`]+$")


def _validate_iri(iri: str) -> None:
    """Validate that a string is a plausible HTTP(S) IRI."""
    if not _IRI_PATTERN.match(iri):
        raise ValueError(f"Invalid IRI: {iri}")


def _inject_from_clause(query: str, named_graph: str) -> str:
    """Inject a FROM <named_graph> clause into a SPARQL query.

    Inserts the clause after SELECT/CONSTRUCT/DESCRIBE/ASK keywords
    and before the WHERE clause (or the opening brace).
    """
    # Match the first occurrence of WHERE or opening brace
    pattern = re.compile(
        r"(SELECT\b.*?|CONSTRUCT\b.*?|DESCRIBE\b.*?|ASK\b)\s*(WHERE\s*\{|\{)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(query)
    if match:
        insert_pos = match.start(2)
        return f"{query[:insert_pos]}FROM <{named_graph}>\n{query[insert_pos:]}"
    # Fallback: append before the query (shouldn't normally happen)
    return query


def get_query_tools() -> list[Tool]:
    """Return SPARQL query tool definitions."""
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
                    "offset": {
                        "type": "integer",
                        "description": "Number of results to skip for pagination (default: 0)",
                    },
                    "named_graph": {
                        "type": "string",
                        "description": "IRI of a named graph to restrict the query to (optional)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="sparql_construct",
            description=(
                "Execute a SPARQL CONSTRUCT or DESCRIBE query, return Turtle."
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
                    "named_graph": {
                        "type": "string",
                        "description": "IRI of a named graph to restrict the query to (optional)",
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
                    "named_graph": {
                        "type": "string",
                        "description": "IRI of a named graph to restrict the query to (optional)",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


QUERY_TOOL_NAMES = {"sparql_select", "sparql_construct", "sparql_ask"}


async def handle_query_tool(
    name: str, arguments: dict[str, Any], backend: Backend, settings: Settings
) -> list[TextContent]:
    """Dispatch a query tool call to the appropriate handler."""
    if name == "sparql_select":
        return await handle_sparql_select(backend, arguments, settings)
    elif name == "sparql_construct":
        return await handle_sparql_construct(backend, arguments)
    elif name == "sparql_ask":
        return await handle_sparql_ask(backend, arguments)
    else:
        raise ValueError(f"Unknown query tool: {name}")


async def handle_sparql_select(
    backend: Backend,
    arguments: dict[str, Any],
    settings: Settings,
) -> list[TextContent]:
    """Handle sparql_select tool call."""
    query = arguments["query"]
    repo_id = arguments.get("repository_id")
    limit = arguments.get("limit")
    offset = arguments.get("offset", 0)
    named_graph = arguments.get("named_graph")

    if named_graph:
        _validate_iri(named_graph)
        query = _inject_from_clause(query, named_graph)

    query_upper = query.upper()
    has_explicit_limit = "LIMIT" in query_upper
    has_explicit_offset = "OFFSET" in query_upper

    if not has_explicit_limit:
        effective_limit = min(limit or settings.default_limit, settings.max_limit)
        # Request one extra row to detect whether more results exist
        query = f"{query}\nLIMIT {effective_limit + 1}"
    else:
        effective_limit = None

    if offset and not has_explicit_offset:
        query = f"{query}\nOFFSET {offset}"

    result = await backend.sparql_select(query, repo_id)
    bindings = result.bindings or []

    # Determine pagination state
    has_more = False
    if effective_limit is not None and len(bindings) > effective_limit:
        has_more = True
        bindings = bindings[:effective_limit]

    output: dict[str, Any] = {
        "type": "select",
        "variables": result.variables or [],
        "bindings": bindings,
        "count": len(bindings),
        "offset": offset,
        "limit": effective_limit if effective_limit is not None else len(bindings),
        "has_more": has_more,
    }
    if has_more:
        output["next_offset"] = offset + len(bindings)

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_sparql_construct(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle sparql_construct tool call."""
    query = arguments["query"]
    repo_id = arguments.get("repository_id")
    named_graph = arguments.get("named_graph")

    if named_graph:
        _validate_iri(named_graph)
        query = _inject_from_clause(query, named_graph)

    result = await backend.sparql_construct(query, repo_id)
    output = f"# SPARQL CONSTRUCT/DESCRIBE Result\n# Format: Turtle\n\n{result.triples or ''}"
    return [TextContent(type="text", text=output)]


async def handle_sparql_ask(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle sparql_ask tool call."""
    query = arguments["query"]
    repo_id = arguments.get("repository_id")
    named_graph = arguments.get("named_graph")

    if named_graph:
        _validate_iri(named_graph)
        query = _inject_from_clause(query, named_graph)

    result = await backend.sparql_ask(query, repo_id)
    output = {"type": "ask", "result": result.boolean}
    return [TextContent(type="text", text=json.dumps(output, indent=2))]
