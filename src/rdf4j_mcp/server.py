"""FastMCP server for RDF4J integration."""

from fastmcp import FastMCP

mcp = FastMCP("rdf4j-mcp")

# Import modules to register tools, resources, and prompts
from . import tools  # noqa: F401, E402
from . import resources  # noqa: F401, E402
from . import prompts  # noqa: F401, E402
