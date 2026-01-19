"""MCP Prompts for RDF4J."""

from typing import Any

from mcp.server import Server
from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent

from ..backends.base import Backend


def register_prompts(server: Server, get_backend: Any) -> None:
    """Register MCP prompts with the server.

    Args:
        server: The MCP server instance
        get_backend: Callable that returns the backend instance
    """

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="explore_knowledge_graph",
                description=(
                    "Guided exploration of a knowledge graph. "
                    "Provides context about the schema and suggests exploration paths."
                ),
                arguments=[
                    PromptArgument(
                        name="repository_id",
                        description="Repository to explore (optional, uses default)",
                        required=False,
                    ),
                    PromptArgument(
                        name="focus_area",
                        description="Specific class or concept to focus on (optional)",
                        required=False,
                    ),
                ],
            ),
            Prompt(
                name="write_sparql_query",
                description=(
                    "Help write a SPARQL query from a natural language description. "
                    "Provides schema context to assist with query construction."
                ),
                arguments=[
                    PromptArgument(
                        name="question",
                        description="Natural language question to answer with SPARQL",
                        required=True,
                    ),
                    PromptArgument(
                        name="repository_id",
                        description="Repository to query (optional, uses default)",
                        required=False,
                    ),
                ],
            ),
            Prompt(
                name="explain_ontology",
                description=(
                    "Explain the structure and meaning of an ontology or schema. "
                    "Describes classes, properties, and their relationships."
                ),
                arguments=[
                    PromptArgument(
                        name="repository_id",
                        description="Repository containing the ontology (optional)",
                        required=False,
                    ),
                    PromptArgument(
                        name="focus_class",
                        description="Specific class IRI to explain (optional)",
                        required=False,
                    ),
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
        """Get a prompt by name."""
        backend: Backend = get_backend()
        args = arguments or {}

        if name == "explore_knowledge_graph":
            return await _get_explore_prompt(backend, args)
        elif name == "write_sparql_query":
            return await _get_sparql_prompt(backend, args)
        elif name == "explain_ontology":
            return await _get_explain_prompt(backend, args)
        else:
            raise ValueError(f"Unknown prompt: {name}")


async def _get_explore_prompt(
    backend: Backend,
    arguments: dict[str, str],
) -> GetPromptResult:
    """Generate the explore_knowledge_graph prompt."""
    repo_id = arguments.get("repository_id")
    focus_area = arguments.get("focus_area")

    # Get schema summary
    summary = await backend.get_schema_summary(repo_id)
    stats = summary["statistics"]
    namespaces = summary["namespaces"]
    classes = summary["classes"][:15]
    properties = summary["properties"][:15]

    # Format schema context
    ns_text = "\n".join([f"  - {ns['prefix']}: <{ns['namespace']}>" for ns in namespaces[:10]])
    classes_text = "\n".join(
        [
            f"  - {c.get('class', {}).get('value', 'Unknown')}"
            + (f" ({c.get('label', {}).get('value', '')})" if c.get("label") else "")
            for c in classes
        ]
    )
    props_text = "\n".join(
        [
            f"  - {p.get('property', {}).get('value', 'Unknown')}"
            + (f" ({p.get('label', {}).get('value', '')})" if p.get("label") else "")
            for p in properties
        ]
    )

    focus_text = ""
    if focus_area:
        focus_text = f"\nThe user wants to focus on: {focus_area}\n"

    prompt_text = f"""You are helping explore a knowledge graph. Here is the current schema context:

## Statistics
- Total statements: {stats["total_statements"]}
- Total classes: {stats["total_classes"]}
- Total properties: {stats["total_properties"]}

## Namespaces
{ns_text}

## Main Classes
{classes_text}

## Main Properties
{props_text}
{focus_text}
## Available Tools
You can use these tools to explore:
- `sparql_select` - Query for specific data
- `sparql_construct` - Get RDF subgraphs
- `describe_resource` - Get all info about a specific IRI
- `search_classes` - Find classes by pattern
- `search_properties` - Find properties by pattern
- `find_instances` - Find instances of a class
- `get_schema_summary` - Get ontology overview

## Exploration Suggestions
1. Start by understanding the main classes and their relationships
2. Use `describe_resource` to explore specific instances
3. Look for patterns in how classes are connected via properties
4. Check for hierarchies using rdfs:subClassOf relationships

What would you like to explore?"""

    return GetPromptResult(
        description="Knowledge graph exploration context",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            ),
        ],
    )


async def _get_sparql_prompt(
    backend: Backend,
    arguments: dict[str, str],
) -> GetPromptResult:
    """Generate the write_sparql_query prompt."""
    question = arguments.get("question", "")
    repo_id = arguments.get("repository_id")

    # Get schema context
    summary = await backend.get_schema_summary(repo_id)
    namespaces = summary["namespaces"]
    classes = summary["classes"][:20]
    properties = summary["properties"][:20]

    # Format prefixes
    prefixes = "\n".join(
        [f"PREFIX {ns['prefix']}: <{ns['namespace']}>" for ns in namespaces if ns["prefix"]][:15]
    )

    # Format classes
    classes_text = "\n".join(
        [
            f"  - <{c.get('class', {}).get('value', '')}>"
            + (f" # {c.get('label', {}).get('value', '')}" if c.get("label") else "")
            for c in classes
        ]
    )

    # Format properties
    props_text = "\n".join(
        [
            f"  - <{p.get('property', {}).get('value', '')}>"
            + (f" # {p.get('label', {}).get('value', '')}" if p.get("label") else "")
            + (f" domain: {p.get('domain', {}).get('value', '')}" if p.get("domain") else "")
            + (f" range: {p.get('range', {}).get('value', '')}" if p.get("range") else "")
            for p in properties
        ]
    )

    prompt_text = f"""Help me write a SPARQL query to answer this question:

"{question}"

## Available Prefixes
```sparql
{prefixes}
```

## Available Classes
{classes_text}

## Available Properties
{props_text}

## Guidelines
1. Use the prefixes above when possible
2. Use OPTIONAL for non-required fields
3. Add FILTER for text searches or constraints
4. Use LIMIT to avoid overwhelming results
5. Consider using ORDER BY for sorted results

Please write a SPARQL SELECT query that answers the question.
Explain your reasoning and any assumptions made."""

    return GetPromptResult(
        description="SPARQL query writing assistance",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            ),
        ],
    )


async def _get_explain_prompt(
    backend: Backend,
    arguments: dict[str, str],
) -> GetPromptResult:
    """Generate the explain_ontology prompt."""
    repo_id = arguments.get("repository_id")
    focus_class = arguments.get("focus_class")

    # Get schema summary
    summary = await backend.get_schema_summary(repo_id)
    stats = summary["statistics"]
    namespaces = summary["namespaces"]
    classes = summary["classes"]
    properties = summary["properties"]

    focus_text = ""
    if focus_class:
        # Get detailed info about the focus class
        class_query = f"""
        SELECT ?property ?range ?label
        WHERE {{
            {{ ?property rdfs:domain <{focus_class}> . OPTIONAL {{ ?property rdfs:range ?range }} }}
            UNION
            {{ <{focus_class}> ?property ?range }}
            OPTIONAL {{ ?property rdfs:label ?label }}
        }}
        LIMIT 50
        """
        try:
            class_result = await backend.sparql_select(class_query, repo_id)
            if class_result.bindings:
                props = "\n".join(
                    [
                        f"  - {b.get('property', {}).get('value', 'Unknown')}"
                        for b in class_result.bindings[:20]
                    ]
                )
                focus_text = f"""
## Focus Class: {focus_class}
Properties related to this class:
{props}
"""
        except Exception:
            focus_text = f"\n## Focus Class: {focus_class}\n"

    # Format overall summary
    ns_text = "\n".join([f"  - {ns['prefix']}: <{ns['namespace']}>" for ns in namespaces[:10]])
    classes_text = "\n".join(
        [
            f"  - {c.get('class', {}).get('value', 'Unknown')}"
            + (f": {c.get('comment', {}).get('value', '')[:100]}" if c.get("comment") else "")
            for c in classes[:25]
        ]
    )
    props_text = "\n".join(
        [
            f"  - {p.get('property', {}).get('value', 'Unknown')}"
            + (f" (domain: {p.get('domain', {}).get('value', 'Any')})" if p.get("domain") else "")
            + (f" -> {p.get('range', {}).get('value', 'Any')}" if p.get("range") else "")
            for p in properties[:25]
        ]
    )

    prompt_text = f"""Please explain this ontology/schema:

## Overview
- Total statements: {stats["total_statements"]}
- Total classes: {stats["total_classes"]}
- Total properties: {stats["total_properties"]}

## Namespaces Used
{ns_text}

## Classes
{classes_text}

## Properties
{props_text}
{focus_text}
Please provide:
1. A high-level summary of what this ontology represents
2. The main concepts (classes) and how they relate
3. Key properties and what they connect
4. Any patterns or design choices you notice
5. Suggestions for how to query this data effectively"""

    return GetPromptResult(
        description="Ontology explanation",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            ),
        ],
    )
