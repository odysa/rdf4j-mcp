"""Main MCP server for RDF4J."""

import argparse
import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from .backends.base import Backend
from .backends.remote import RemoteBackend
from .config import Settings, configure, get_settings
from .tools.explore import (
    handle_describe_resource,
    handle_get_schema_summary,
    handle_search_classes,
)
from .tools.query import handle_sparql_ask, handle_sparql_construct, handle_sparql_select

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
        from .tools import register_all_tools

        register_all_tools(self._server, self._get_backend)

        # Register resources
        from .resources import register_resources

        register_resources(self._server, self._get_backend)

        # Register prompts
        from .prompts import register_prompts

        register_prompts(self._server, self._get_backend)

    # Thin wrappers for backward compatibility with tests
    async def _handle_sparql_select(
        self, backend: Backend, arguments: dict[str, Any], settings: Settings
    ) -> list[TextContent]:
        return await handle_sparql_select(backend, arguments, settings)

    async def _handle_sparql_construct(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        return await handle_sparql_construct(backend, arguments)

    async def _handle_sparql_ask(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        return await handle_sparql_ask(backend, arguments)

    async def _handle_describe_resource(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        return await handle_describe_resource(backend, arguments)

    async def _handle_search_classes(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        return await handle_search_classes(backend, arguments)

    async def _handle_get_schema_summary(
        self, backend: Backend, arguments: dict[str, Any]
    ) -> list[TextContent]:
        return await handle_get_schema_summary(backend, arguments)

    def _get_backend(self) -> Backend:
        """Get the backend instance, creating if needed."""
        if self._backend is None:
            raise RuntimeError("Backend not initialized. Call start() first.")
        return self._backend

    async def _create_backend(self) -> Backend:
        """Create and connect to the backend."""
        settings = self._settings

        backend = RemoteBackend(
            server_url=settings.rdf4j_server_url,
            default_repository=settings.default_repository,
            cache_ttl=settings.cache_ttl,
            query_timeout=settings.query_timeout,
        )

        await backend.connect()
        return backend

    async def start(self) -> None:
        """Start the server."""
        self._backend = await self._create_backend()
        logger.info(f"RDF4J MCP Server started, connected to {self._settings.rdf4j_server_url}")

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

    def run_http(self, host: str = "0.0.0.0", port: int = 3000) -> None:
        """Run the server using HTTP/SSE transport.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to listen on (default: 3000)
        """
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await self._server.run(
                    streams[0], streams[1], self._server.create_initialization_options()
                )
            return Response()

        async def handle_health(request):
            return Response("OK", media_type="text/plain")

        async def lifespan(app):
            """Handle startup and shutdown."""
            await self.start()
            logger.info(f"HTTP server running on http://{host}:{port}")
            logger.info(f"SSE endpoint: http://{host}:{port}/sse")
            yield
            await self.stop()

        starlette_app = Starlette(
            debug=False,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Route("/health", endpoint=handle_health, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ],
            lifespan=lifespan,
        )

        uvicorn.run(starlette_app, host=host, port=port, log_level="info")


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
    # Load settings from env vars first
    default_settings = Settings()

    parser = argparse.ArgumentParser(
        description="RDF4J MCP Server - Knowledge graph exploration via MCP"
    )
    parser.add_argument(
        "--server-url",
        default=None,
        help=f"RDF4J server URL (default: {default_settings.rdf4j_server_url})",
    )
    parser.add_argument(
        "--repository",
        default=None,
        help="Default repository ID",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport type: stdio (default) or http",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for HTTP transport (default: 3000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # CLI args override env vars only if explicitly provided
    settings = Settings(
        rdf4j_server_url=args.server_url or default_settings.rdf4j_server_url,
        default_repository=args.repository or default_settings.default_repository,
    )

    server = create_server(settings)

    try:
        if args.transport == "http":
            server.run_http(host=args.host, port=args.port)
        else:
            asyncio.run(server.run_stdio())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
        sys.exit(0)


if __name__ == "__main__":
    main()
