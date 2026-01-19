"""Knowledge graph exploration tools for MCP."""

import json
from typing import Any, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from ..backends.base import Backend


def register_explore_tools(server: Server, get_backend: Any) -> None:
    """Register knowledge graph exploration tools with the MCP server.

    Args:
        server: The MCP server instance
        get_backend: Callable that returns the backend instance
    """

    @server.list_tools()
    async def list_explore_tools() -> list[Tool]:
        """List available exploration tools."""
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
                            "description": "Include triples where resource is object (default: true)",
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
                description=(
                    "Find instances of a class. "
                    "Returns instance IRIs with labels."
                ),
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

    @server.call_tool()
    async def handle_explore_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle exploration tool calls."""
        backend: Backend = get_backend()

        if name == "describe_resource":
            return await _handle_describe_resource(backend, arguments)
        elif name == "search_classes":
            return await _handle_search_classes(backend, arguments)
        elif name == "search_properties":
            return await _handle_search_properties(backend, arguments)
        elif name == "find_instances":
            return await _handle_find_instances(backend, arguments)
        elif name == "get_schema_summary":
            return await _handle_get_schema_summary(backend, arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")


async def _handle_describe_resource(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle describe_resource tool call."""
    iri = arguments["iri"]
    repository_id: Optional[str] = arguments.get("repository_id")
    include_incoming = arguments.get("include_incoming", True)

    # Get outgoing triples (resource as subject)
    result = await backend.describe_resource(iri, repository_id)
    turtle = result.triples or ""

    # Get incoming triples if requested
    incoming_text = ""
    if include_incoming:
        incoming_query = f"""
        CONSTRUCT {{ ?s ?p <{iri}> }}
        WHERE {{ ?s ?p <{iri}> }}
        """
        incoming_result = await backend.sparql_construct(incoming_query, repository_id)
        if incoming_result.triples:
            incoming_text = f"\n# Incoming triples (resource as object):\n{incoming_result.triples}"

    # Create summary
    summary_query = f"""
    SELECT ?type (COUNT(?p) as ?propCount)
    WHERE {{
        <{iri}> a ?type .
        OPTIONAL {{ <{iri}> ?p ?o }}
    }}
    GROUP BY ?type
    """
    summary_result = await backend.sparql_select(summary_query, repository_id)

    summary_lines = ["# Resource Summary"]
    summary_lines.append(f"# IRI: {iri}")
    if summary_result.bindings:
        types = [b.get("type", {}).get("value", "Unknown") for b in summary_result.bindings]
        summary_lines.append(f"# Types: {', '.join(types)}")

    output = "\n".join(summary_lines) + f"\n\n{turtle}{incoming_text}"

    return [TextContent(type="text", text=output)]


async def _handle_search_classes(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle search_classes tool call."""
    pattern: Optional[str] = arguments.get("pattern")
    limit = arguments.get("limit", 100)
    repository_id: Optional[str] = arguments.get("repository_id")

    result = await backend.search_classes(pattern, limit, repository_id)

    output = {
        "type": "classes",
        "pattern": pattern,
        "count": len(result.bindings or []),
        "classes": _format_class_results(result.bindings or []),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_search_properties(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle search_properties tool call."""
    pattern: Optional[str] = arguments.get("pattern")
    domain: Optional[str] = arguments.get("domain")
    range_: Optional[str] = arguments.get("range")
    limit = arguments.get("limit", 100)
    repository_id: Optional[str] = arguments.get("repository_id")

    result = await backend.search_properties(pattern, domain, range_, limit, repository_id)

    output = {
        "type": "properties",
        "pattern": pattern,
        "domain_filter": domain,
        "range_filter": range_,
        "count": len(result.bindings or []),
        "properties": _format_property_results(result.bindings or []),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_find_instances(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle find_instances tool call."""
    class_iri = arguments["class_iri"]
    limit = arguments.get("limit", 100)
    repository_id: Optional[str] = arguments.get("repository_id")

    result = await backend.find_instances(class_iri, limit, repository_id)

    output = {
        "type": "instances",
        "class": class_iri,
        "count": len(result.bindings or []),
        "instances": _format_instance_results(result.bindings or []),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


async def _handle_get_schema_summary(
    backend: Backend,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_schema_summary tool call."""
    repository_id: Optional[str] = arguments.get("repository_id")

    summary = await backend.get_schema_summary(repository_id)

    # Format for output
    output = {
        "type": "schema_summary",
        "statistics": summary["statistics"],
        "namespaces": summary["namespaces"],
        "top_classes": _format_class_results(summary["classes"][:20]),
        "top_properties": _format_property_results(summary["properties"][:20]),
    }

    return [TextContent(type="text", text=json.dumps(output, indent=2))]


def _format_class_results(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format class query results."""
    classes = []
    for b in bindings:
        cls = {
            "iri": b.get("class", {}).get("value", ""),
        }
        if "label" in b:
            cls["label"] = b["label"].get("value", "")
        if "comment" in b:
            cls["comment"] = b["comment"].get("value", "")
        classes.append(cls)
    return classes


def _format_property_results(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format property query results."""
    properties = []
    for b in bindings:
        prop = {
            "iri": b.get("property", {}).get("value", ""),
        }
        if "label" in b:
            prop["label"] = b["label"].get("value", "")
        if "domain" in b:
            prop["domain"] = b["domain"].get("value", "")
        if "range" in b:
            prop["range"] = b["range"].get("value", "")
        properties.append(prop)
    return properties


def _format_instance_results(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format instance query results."""
    instances = []
    for b in bindings:
        inst = {
            "iri": b.get("instance", {}).get("value", ""),
        }
        if "label" in b:
            inst["label"] = b["label"].get("value", "")
        instances.append(inst)
    return instances
