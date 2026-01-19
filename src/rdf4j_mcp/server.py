"""Main MCP server for RDF4J."""

import argparse
import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .backends.base import Backend
from .backends.local import LocalBackend
from .backends.remote import RemoteBackend
from .config import BackendType, Settings, configure, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RDF4JMCPServer:
    """MCP Server for RDF4J knowledge graph operations."""

    def __init__(self, settings: Settings | None = None):
        """Initialize the server.

        Args:
            settings: Server settings (uses defaults if not provided)
        """
        if settings:
            configure(settings)
        self._settings = get_settings()
        self._backend: Backend | None = None
        self._server = Server(self._settings.server_name)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP handlers."""
        # Register all tools
        self._register_tools()

        # Register resources
        from .resources import register_resources

        register_resources(self._server, self._get_backend)

        # Register prompts
        from .prompts import register_prompts

        register_prompts(self._server, self._get_backend)

    def _register_tools(self) -> None:
        """Register all tools with the server."""

        @self._server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return [
                # SPARQL Query Tools
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
                                "description": "Repository ID (optional, uses default if not specified)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (applied if query has no LIMIT)",
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
                                "description": "Repository ID (optional, uses default if not specified)",
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
                                "description": "Repository ID (optional, uses default if not specified)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                # Exploration Tools
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
                    description=("Find instances of a class. Returns instance IRIs with labels."),
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
                # Metadata Tools
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
                                "description": "Repository ID (optional, uses default if not specified)",
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
                                "description": "Repository ID (optional, uses default if not specified)",
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
            ]

        @self._server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            import json

            backend = self._get_backend()
            settings = self._settings

            # SPARQL Query Tools
            if name == "sparql_select":
                return await self._handle_sparql_select(backend, arguments, settings)
            elif name == "sparql_construct":
                return await self._handle_sparql_construct(backend, arguments)
            elif name == "sparql_ask":
                return await self._handle_sparql_ask(backend, arguments)

            # Exploration Tools
            elif name == "describe_resource":
                return await self._handle_describe_resource(backend, arguments)
            elif name == "search_classes":
                return await self._handle_search_classes(backend, arguments)
            elif name == "search_properties":
                return await self._handle_search_properties(backend, arguments)
            elif name == "find_instances":
                return await self._handle_find_instances(backend, arguments)
            elif name == "get_schema_summary":
                return await self._handle_get_schema_summary(backend, arguments)

            # Metadata Tools
            elif name == "list_repositories":
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

            elif name == "get_namespaces":
                repo_id = arguments.get("repository_id")
                namespaces = await backend.get_namespaces(repo_id)
                sparql_prefixes = "\n".join(
                    [f"PREFIX {ns.prefix}: <{ns.namespace}>" for ns in namespaces if ns.prefix]
                )
                output = {
                    "type": "namespaces",
                    "count": len(namespaces),
                    "namespaces": [
                        {"prefix": ns.prefix, "namespace": ns.namespace} for ns in namespaces
                    ],
                    "sparql_prefixes": sparql_prefixes,
                }
                return [TextContent(type="text", text=json.dumps(output, indent=2))]

            elif name == "get_statistics":
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

            elif name == "select_repository":
                repo_id = arguments["repository_id"]
                await backend.select_repository(repo_id)
                output = {
                    "type": "repository_selected",
                    "repository_id": repo_id,
                    "message": f"Repository '{repo_id}' is now the default.",
                }
                return [TextContent(type="text", text=json.dumps(output, indent=2))]

            elif name == "get_current_repository":
                current = await backend.get_current_repository()
                output = {
                    "type": "current_repository",
                    "repository_id": current,
                    "message": f"Current repository: {current}"
                    if current
                    else "No repository selected",
                }
                return [TextContent(type="text", text=json.dumps(output, indent=2))]

            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _handle_sparql_select(
        self, backend: Backend, arguments: dict[str, Any], settings: Settings
    ) -> list[TextContent]:
        """Handle sparql_select tool."""
        import json

        query = arguments["query"]
        repo_id = arguments.get("repository_id")
        limit = arguments.get("limit")

        query_upper = query.upper()
        if "LIMIT" not in query_upper:
            effective_limit = min(limit or settings.default_limit, settings.max_limit)
            query = f"{query}\nLIMIT {effective_limit}"

        result = await backend.sparql_select(query, repo_id)
        output = {
            "type": "select",
            "variables": result.variables or [],
            "bindings": result.bindings or [],
            "count": len(result.bindings or []),
        }
        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    async def _handle_sparql_construct(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle sparql_construct tool."""
        query = arguments["query"]
        repo_id = arguments.get("repository_id")
        result = await backend.sparql_construct(query, repo_id)
        output = f"# SPARQL CONSTRUCT/DESCRIBE Result\n# Format: Turtle\n\n{result.triples or ''}"
        return [TextContent(type="text", text=output)]

    async def _handle_sparql_ask(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle sparql_ask tool."""
        import json

        query = arguments["query"]
        repo_id = arguments.get("repository_id")
        result = await backend.sparql_ask(query, repo_id)
        output = {"type": "ask", "result": result.boolean}
        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    async def _handle_describe_resource(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle describe_resource tool."""
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

    async def _handle_search_classes(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle search_classes tool."""
        import json

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

    async def _handle_search_properties(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle search_properties tool."""
        import json

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

    async def _handle_find_instances(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle find_instances tool."""
        import json

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

    async def _handle_get_schema_summary(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle get_schema_summary tool."""
        import json

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

    def _get_backend(self) -> Backend:
        """Get the backend instance, creating if needed."""
        if self._backend is None:
            raise RuntimeError("Backend not initialized. Call start() first.")
        return self._backend

    async def _create_backend(self) -> Backend:
        """Create and connect to the backend."""
        settings = self._settings

        if settings.backend_type == BackendType.LOCAL:
            backend = LocalBackend(
                store_path=settings.local_store_path,
                store_format=settings.local_store_format,
            )
        else:
            backend = RemoteBackend(
                server_url=settings.rdf4j_server_url,
                default_repository=settings.default_repository,
            )

        await backend.connect()
        return backend

    async def start(self) -> None:
        """Start the server."""
        self._backend = await self._create_backend()
        logger.info(f"RDF4J MCP Server started with {self._settings.backend_type.value} backend")

    async def stop(self) -> None:
        """Stop the server."""
        if self._backend:
            await self._backend.close()
            self._backend = None
        logger.info("RDF4J MCP Server stopped")

    async def run_stdio(self) -> None:
        """Run the server using stdio transport."""
        await self.start()
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self._server.run(
                    read_stream,
                    write_stream,
                    self._server.create_initialization_options(),
                )
        finally:
            await self.stop()


def create_server(settings: Settings | None = None) -> RDF4JMCPServer:
    """Create a new RDF4J MCP server instance.

    Args:
        settings: Server settings (uses defaults if not provided)

    Returns:
        RDF4JMCPServer instance
    """
    return RDF4JMCPServer(settings)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="RDF4J MCP Server - Knowledge graph exploration via MCP"
    )
    parser.add_argument(
        "--backend",
        choices=["local", "remote"],
        default="local",
        help="Backend type (default: local)",
    )
    parser.add_argument(
        "--server-url",
        default="http://localhost:8080/rdf4j-server",
        help="RDF4J server URL (for remote backend)",
    )
    parser.add_argument(
        "--repository",
        help="Default repository ID",
    )
    parser.add_argument(
        "--store-path",
        help="Path to local RDF file (for local backend)",
    )
    parser.add_argument(
        "--store-format",
        default="turtle",
        help="Format of local RDF file (default: turtle)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    settings = Settings(
        backend_type=BackendType(args.backend),
        rdf4j_server_url=args.server_url,
        default_repository=args.repository,
        local_store_path=args.store_path,
        local_store_format=args.store_format,
    )

    server = create_server(settings)

    try:
        asyncio.run(server.run_stdio())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
        sys.exit(0)


if __name__ == "__main__":
    main()
