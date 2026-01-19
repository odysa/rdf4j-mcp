"""Prompt definitions for the RDF4J MCP server."""

from .server import mcp


@mcp.prompt
def summarize(text: str) -> str:
    """Generate a prompt asking for a summary.

    Args:
        text: The text to summarize.

    Returns:
        A prompt requesting summarization of the text.
    """
    return f"Please summarize the following text:\n\n{text}"


@mcp.prompt
def explain(topic: str) -> str:
    """Generate a prompt asking for an explanation.

    Args:
        topic: The topic to explain.

    Returns:
        A prompt requesting an explanation of the topic.
    """
    return f"Please explain the following topic in detail:\n\n{topic}"
