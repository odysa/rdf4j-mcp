"""Knowledge graph exploration tools for MCP."""

import json
from typing import Any

from mcp.types import TextContent, Tool

from ..backends.base import Backend


def get_explore_tools() -> list[Tool]:
    """Return exploration tool definitions."""
    return [
        Tool(
            name="describe_resource",
            description=(
                "Get all triples about a resource (subject or object). "
                "Returns Turtle format with human-readable summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "iri": {
                        "type": "string",
                        "description": "The IRI of the resource to describe",
                    },
                    "repository_id": {
                        "type": "string",
                        "description": "Repository ID (optional)",
                    },
                    "include_incoming": {
                        "type": "boolean",
                        "description": "Include triples where resource is object",
                        "default": True,
                    },
                },
                "required": ["iri"],
            },
        ),
        Tool(
            name="search_classes",
            description=(
                "Find classes in the ontology. Can filter by name pattern. "
                "Returns class IRIs with labels and comments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to filter class names (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                        "default": 100,
                    },
                    "repository_id": {
                        "type": "string",
                        "description": "Repository ID (optional)",
                    },
                },
            },
        ),
        Tool(
            name="search_properties",
            description=(
                "Find properties in the ontology. Can filter by pattern, domain, or range. "
                "Returns property IRIs with labels, domains, and ranges."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to filter property names (optional)",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain class IRI (optional)",
                    },
                    "range": {
                        "type": "string",
                        "description": "Filter by range class IRI (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                        "default": 100,
                    },
                    "repository_id": {
                        "type": "string",
                        "description": "Repository ID (optional)",
                    },
                },
            },
        ),
        Tool(
            name="find_instances",
            description="Find instances of a class. Returns instance IRIs with labels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "class_iri": {
                        "type": "string",
                        "description": "The IRI of the class to find instances of",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                        "default": 100,
                    },
                    "repository_id": {
                        "type": "string",
                        "description": "Repository ID (optional)",
                    },
                },
                "required": ["class_iri"],
            },
        ),
        Tool(
            name="get_schema_summary",
            description=(
                "Get an overview of the ontology schema including statistics, "
                "main classes, properties, and namespaces."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repository_id": {
                        "type": "string",
                        "description": "Repository ID (optional)",
                    },
                },
            },
        ),
    ]


EXPLORE_TOOL_NAMES = {
    "describe_resource",
    "search_classes",
    "search_properties",
    "find_instances",
    "get_schema_summary",
}


async def handle_explore_tool(
    name: str, arguments: dict[str, Any], backend: Backend
) -> list[TextContent]:
    """Dispatch an explore tool call to the appropriate handler."""
    if name == "describe_resource":
        return await handle_describe_resource(backend, arguments)
    elif name == "search_classes":
        return await handle_search_classes(backend, arguments)
    elif name == "search_properties":
        return await handle_search_properties(backend, arguments)
    elif name == "find_instances":
        return await handle_find_instances(backend, arguments)
    elif name == "get_schema_summary":
        return await handle_get_schema_summary(backend, arguments)
    else:
        raise ValueError(f"Unknown explore tool: {name}")


async def handle_describe_resource(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle describe_resource tool call."""
    iri = arguments["iri"]
    repo_id = arguments.get("repository_id")
    include_incoming = arguments.get("include_incoming", True)

    result = await backend.describe_resource(iri, repo_id)
    turtle = result.triples or ""

    incoming_text = ""
    if include_incoming:
        incoming_query = f"CONSTRUCT {{ ?s ?p <{iri}> }} WHERE {{ ?s ?p <{iri}> }}"
        incoming_result = await backend.sparql_construct(incoming_query, repo_id)
        if incoming_result.triples:
            incoming_text = f"\n# Incoming triples:\n{incoming_result.triples}"

    summary_query = f"""
        SELECT ?type WHERE {{ <{iri}> a ?type }}
        """
    summary_result = await backend.sparql_select(summary_query, repo_id)
    types = [b.get("type", {}).get("value", "") for b in (summary_result.bindings or [])]

    summary_lines = [
        "# Resource Summary",
        f"# IRI: {iri}",
        f"# Types: {', '.join(types) if types else 'Unknown'}",
    ]
    output = "\n".join(summary_lines) + f"\n\n{turtle}{incoming_text}"
    return [TextContent(type="text", text=output)]


async def handle_search_classes(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle search_classes tool call."""
    pattern = arguments.get("pattern")
    limit = arguments.get("limit", 100)
    repo_id = arguments.get("repository_id")

    result = await backend.search_classes(pattern, limit, repo_id)
    classes = [
        {
            "iri": b.get("class", {}).get("value", ""),
            **({"label": b["label"].get("value", "")} if "label" in b else {}),
            **({"comment": b["comment"].get("value", "")} if "comment" in b else {}),
        }
        for b in (result.bindings or [])
    ]
    output = {
        "type": "classes",
        "pattern": pattern,
        "count": len(classes),
        "classes": classes,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_search_properties(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle search_properties tool call."""
    pattern = arguments.get("pattern")
    domain = arguments.get("domain")
    range_ = arguments.get("range")
    limit = arguments.get("limit", 100)
    repo_id = arguments.get("repository_id")

    result = await backend.search_properties(pattern, domain, range_, limit, repo_id)
    properties = [
        {
            "iri": b.get("property", {}).get("value", ""),
            **({"label": b["label"].get("value", "")} if "label" in b else {}),
            **({"domain": b["domain"].get("value", "")} if "domain" in b else {}),
            **({"range": b["range"].get("value", "")} if "range" in b else {}),
        }
        for b in (result.bindings or [])
    ]
    output = {
        "type": "properties",
        "pattern": pattern,
        "count": len(properties),
        "properties": properties,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_find_instances(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle find_instances tool call."""
    class_iri = arguments["class_iri"]
    limit = arguments.get("limit", 100)
    repo_id = arguments.get("repository_id")

    result = await backend.find_instances(class_iri, limit, repo_id)
    instances = [
        {
            "iri": b.get("instance", {}).get("value", ""),
            **({"label": b["label"].get("value", "")} if "label" in b else {}),
        }
        for b in (result.bindings or [])
    ]
    output = {
        "type": "instances",
        "class": class_iri,
        "count": len(instances),
        "instances": instances,
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def handle_get_schema_summary(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_schema_summary tool call."""
    repo_id = arguments.get("repository_id")
    summary = await backend.get_schema_summary(repo_id)

    output = {
        "type": "schema_summary",
        "statistics": summary["statistics"],
        "namespaces": summary["namespaces"],
        "top_classes": [
            {
                "iri": c.get("class", {}).get("value", ""),
                **({"label": c["label"].get("value", "")} if "label" in c else {}),
            }
            for c in summary["classes"][:20]
        ],
        "top_properties": [
            {
                "iri": p.get("property", {}).get("value", ""),
                **({"label": p["label"].get("value", "")} if "label" in p else {}),
            }
            for p in summary["properties"][:20]
        ],
    }
    return [TextContent(type="text", text=json.dumps(output, indent=2))]
