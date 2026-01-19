"""Resource definitions for the RDF4J MCP server."""

from .server import mcp


@mcp.resource("config://version")
def get_version() -> str:
    """Get the current server version."""
    from . import __version__

    return __version__


@mcp.resource("config://info")
def get_info() -> dict:
    """Get server information."""
    from . import __version__

    return {
        "name": "rdf4j-mcp",
        "version": __version__,
        "description": "MCP server for RDF4J integration",
    }
