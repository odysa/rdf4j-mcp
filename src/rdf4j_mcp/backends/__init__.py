"""Backend implementations for RDF4J MCP Server."""

from .base import Backend
from .remote import RemoteBackend

__all__ = ["Backend", "RemoteBackend"]
