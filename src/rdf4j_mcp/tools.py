"""Tool definitions for the RDF4J MCP server."""

from .server import mcp


@mcp.tool
def echo(message: str) -> str:
    """Echo a message back to the caller.

    Args:
        message: The message to echo back.

    Returns:
        The same message that was provided.
    """
    return message


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The sum of a and b.
    """
    return a + b
