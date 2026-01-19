"""FastMCP server for RDF4J integration."""

from fastmcp import FastMCP

mcp = FastMCP("rdf4j-mcp")

# Import modules to register tools, resources, and prompts
from . import prompts, resources, tools

__all__ = ["mcp", "prompts", "resources", "tools"]
