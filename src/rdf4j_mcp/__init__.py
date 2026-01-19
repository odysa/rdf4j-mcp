"""RDF4J MCP Server - FastMCP-based Model Context Protocol server."""

from .server import mcp

__version__ = "0.1.0"
__all__ = ["mcp", "main"]


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()
