"""Typed exceptions for the RDF4J MCP server."""


class RDF4JError(Exception):
    """Base exception for RDF4J MCP errors."""

    pass


class RDF4JConnectionError(RDF4JError):
    """Failed to connect to RDF4J server."""

    pass


class QueryTimeoutError(RDF4JError):
    """SPARQL query timed out."""

    pass


class RepositoryNotFoundError(RDF4JError):
    """Repository not found on the RDF4J server."""

    pass


class SPARQLSyntaxError(RDF4JError):
    """SPARQL query has syntax errors."""

    pass


class SPARQLInjectionError(RDF4JError):
    """Potential SPARQL injection detected."""

    pass
