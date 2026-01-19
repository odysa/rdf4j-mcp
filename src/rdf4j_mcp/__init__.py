"""RDF4J MCP Server - Knowledge graph exploration and SPARQL querying via MCP."""

from .server import create_server, main

__version__ = "0.1.0"
__all__ = ["create_server", "main", "__version__"]
