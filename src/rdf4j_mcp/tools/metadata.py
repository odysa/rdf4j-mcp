"""Repository metadata tools for MCP."""

import json
from typing import Any

from mcp.types import TextContent, Tool

from ..backends.base import Backend


def get_metadata_tools() -> list[Tool]:
    """Return metadata tool definitions."""
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
            description="Get the currently selected default repository ID.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_named_graphs",
            description=(
                "List all named graphs in a repository. "
                "Returns the IRIs of all named graphs that contain data."
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
            name="graph_statistics",
            description=(
                "Get triple counts per named graph in a repository. "
                "Returns each named graph IRI with its statement count."
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
    ]


METADATA_TOOL_NAMES = {
    "list_repositories",
    "get_namespaces",
    "get_statistics",
    "select_repository",
    "get_current_repository",
    "list_named_graphs",
    "graph_statistics",
}


async def handle_metadata_tool(
    name: str, arguments: dict[str, Any], backend: Backend
) -> list[TextContent]:
    """Dispatch a metadata tool call to the appropriate handler."""
    if name == "list_repositories":
        return await handle_list_repositories(backend)
    elif name == "get_namespaces":
        return await handle_get_namespaces(backend, arguments)
    elif name == "get_statistics":
        return await handle_get_statistics(backend, arguments)
    elif name == "select_repository":
        return await handle_select_repository(backend, arguments)
    elif name == "get_current_repository":
        return await handle_get_current_repository(backend)
    elif name == "list_named_graphs":
        return await handle_list_named_graphs(backend, arguments)
    elif name == "graph_statistics":
        return await handle_graph_statistics(backend, arguments)
    else:
        raise ValueError(f"Unknown metadata tool: {name}")


async def handle_list_repositories(backend: Backend) -> list[TextContent]:
    """Handle list_repositories tool call."""
    repos = await backend.list_repositories()
    output = {
        "type": "repositories",
        "count": len(repos),
        "repositories": [
            {
                "id": r.id,
                "title": r.title,
                "uri": r.uri,
                "readable": r.readable,
                "writable": r.writable,
            }
            for r in repos
        ],
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_get_namespaces(backend: Backend, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_namespaces tool call."""
    repo_id = arguments.get("repository_id")
    namespaces = await backend.get_namespaces(repo_id)
    sparql_prefixes = "\n".join(
        [f"PREFIX {ns.prefix}: <{ns.namespace}>" for ns in namespaces if ns.prefix]
    )
    output = {
        "type": "namespaces",
        "count": len(namespaces),
        "namespaces": [{"prefix": ns.prefix, "namespace": ns.namespace} for ns in namespaces],
        "sparql_prefixes": sparql_prefixes,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_get_statistics(backend: Backend, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_statistics tool call."""
    repo_id = arguments.get("repository_id")
    stats = await backend.get_statistics(repo_id)
    output = {
        "type": "statistics",
        "total_statements": stats.total_statements,
        "total_classes": stats.total_classes,
        "total_properties": stats.total_properties,
        "total_subjects": stats.total_subjects,
        "total_objects": stats.total_objects,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_select_repository(
    backend: Backend, arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle select_repository tool call."""
    repo_id = arguments["repository_id"]
    await backend.select_repository(repo_id)
    output = {
        "type": "repository_selected",
        "repository_id": repo_id,
        "message": f"Repository '{repo_id}' is now the default.",
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_get_current_repository(backend: Backend) -> list[TextContent]:
    """Handle get_current_repository tool call."""
    current = await backend.get_current_repository()
    output = {
        "type": "current_repository",
        "repository_id": current,
        "message": f"Current repository: {current}" if current else "No repository selected",
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_list_named_graphs(
    backend: Backend, arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle list_named_graphs tool call."""
    repo_id = arguments.get("repository_id")
    query = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } } ORDER BY ?g"
    result = await backend.sparql_select(query, repo_id)
    graphs = [b.get("g", {}).get("value", "") for b in (result.bindings or [])]
    output = {
        "type": "named_graphs",
        "count": len(graphs),
        "graphs": graphs,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_graph_statistics(backend: Backend, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle graph_statistics tool call."""
    repo_id = arguments.get("repository_id")
    query = (
        "SELECT ?g (COUNT(*) AS ?triples) "
        "WHERE { GRAPH ?g { ?s ?p ?o } } "
        "GROUP BY ?g ORDER BY DESC(?triples)"
    )
    result = await backend.sparql_select(query, repo_id)
    graphs = [
        {
            "graph": b.get("g", {}).get("value", ""),
            "triples": int(b.get("triples", {}).get("value", "0")),
        }
        for b in (result.bindings or [])
    ]
    output = {
        "type": "graph_statistics",
        "count": len(graphs),
        "graphs": graphs,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]
