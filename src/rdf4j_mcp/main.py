"""HTTP backend server entry point for RDF4J MCP.

This module provides a standalone HTTP server for running rdf4j-mcp as a
remote MCP server. Clients connect via SSE instead of stdio.

Usage:
    # Using uvicorn directly
    uvicorn rdf4j_mcp.main:app --host 0.0.0.0 --port 3000

    # Using the CLI
    rdf4j-mcp-server

    # With environment variables
    RDF4J_MCP_RDF4J_SERVER_URL=http://localhost:8080/rdf4j-server \
    RDF4J_MCP_DEFAULT_REPOSITORY=my-repo \
    rdf4j-mcp-server --port 3000

Environment Variables:
    RDF4J_MCP_RDF4J_SERVER_URL: RDF4J server URL (required for remote RDF4J)
    RDF4J_MCP_DEFAULT_REPOSITORY: Default repository ID
    RDF4J_MCP_QUERY_TIMEOUT: Query timeout in seconds (default: 30)
    RDF4J_MCP_DEFAULT_LIMIT: Default LIMIT for queries (default: 100)
    RDF4J_MCP_MAX_LIMIT: Maximum allowed LIMIT (default: 10000)
"""

import argparse
import logging
from contextlib import asynccontextmanager

from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .config import Settings, get_settings
from .server import RDF4JMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global server instance
_mcp_server: RDF4JMCPServer | None = None
_sse_transport: SseServerTransport | None = None


def get_mcp_server() -> RDF4JMCPServer:
    """Get the global MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = RDF4JMCPServer()
    return _mcp_server


def get_sse_transport() -> SseServerTransport:
    """Get the global SSE transport instance."""
    global _sse_transport
    if _sse_transport is None:
        _sse_transport = SseServerTransport("/messages/")
    return _sse_transport


async def handle_sse(request):
    """Handle SSE connections from MCP clients."""
    sse = get_sse_transport()
    server = get_mcp_server()

    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server._server.run(
            streams[0], streams[1], server._server.create_initialization_options()
        )
    return Response()


async def handle_health(request):
    """Health check endpoint."""
    settings = get_settings()
    server = get_mcp_server()

    health = {
        "status": "healthy",
        "service": "rdf4j-mcp",
        "rdf4j_server": settings.rdf4j_server_url,
        "repository": settings.default_repository,
        "backend_connected": server._backend is not None,
    }
    return JSONResponse(health)


async def handle_info(request):
    """Server info endpoint."""
    settings = get_settings()

    info = {
        "name": settings.server_name,
        "version": settings.server_version,
        "transport": "sse",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages/",
            "health": "/health",
            "info": "/info",
        },
        "rdf4j": {
            "server_url": settings.rdf4j_server_url,
            "default_repository": settings.default_repository,
        },
    }
    return JSONResponse(info)


@asynccontextmanager
async def lifespan(app):
    """Handle application startup and shutdown."""
    server = get_mcp_server()
    settings = get_settings()

    logger.info("Starting RDF4J MCP HTTP Server...")
    logger.info(f"RDF4J Server: {settings.rdf4j_server_url}")
    logger.info(f"Default Repository: {settings.default_repository or '(none)'}")

    await server.start()

    logger.info("Server ready. Endpoints:")
    logger.info("  SSE: /sse")
    logger.info("  Health: /health")
    logger.info("  Info: /info")

    yield

    await server.stop()
    logger.info("Server stopped.")


def create_app() -> Starlette:
    """Create the Starlette application."""
    sse = get_sse_transport()

    return Starlette(
        debug=False,
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Route("/health", endpoint=handle_health, methods=["GET"]),
            Route("/info", endpoint=handle_info, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        lifespan=lifespan,
    )


# ASGI app for uvicorn
app = create_app()


def main() -> None:
    """CLI entry point for the HTTP server."""
    import uvicorn

    default_settings = Settings()

    parser = argparse.ArgumentParser(
        description="RDF4J MCP HTTP Server - Remote MCP server for knowledge graph exploration"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to listen on (default: 3000)",
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
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Update settings if CLI args provided
    if args.server_url or args.repository:
        from .config import configure

        settings = Settings(
            rdf4j_server_url=args.server_url or default_settings.rdf4j_server_url,
            default_repository=args.repository or default_settings.default_repository,
        )
        configure(settings)

    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                 RDF4J MCP HTTP Server                         ║
╠═══════════════════════════════════════════════════════════════╣
║  SSE Endpoint:  http://{args.host}:{args.port}/sse{" " * (27 - len(str(args.port)))}║
║  Health Check:  http://{args.host}:{args.port}/health{" " * (24 - len(str(args.port)))}║
║  Server Info:   http://{args.host}:{args.port}/info{" " * (26 - len(str(args.port)))}║
╚═══════════════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        "rdf4j_mcp.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
