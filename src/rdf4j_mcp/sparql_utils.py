"""SPARQL input validation and escaping utilities."""

import re

from rdf4j_mcp.exceptions import SPARQLInjectionError


def validate_iri(iri: str) -> str:
    """Validate and return an IRI.

    Raises SPARQLInjectionError if the IRI contains dangerous characters.
    """
    if not iri:
        raise SPARQLInjectionError("IRI cannot be empty")
    # Reject characters that could break out of <> IRI syntax or inject SPARQL
    dangerous_chars = [">", "<", '"', "{", "}", "|", "^", "`", "\\"]
    for char in dangerous_chars:
        if char in iri:
            raise SPARQLInjectionError(f"IRI contains invalid character: {char!r}")
    # Reject control characters and unescaped whitespace
    if re.search(r"[\x00-\x20]", iri):
        raise SPARQLInjectionError("IRI contains control characters or whitespace")
    return iri


def escape_sparql_string(value: str) -> str:
    """Escape a string for safe use in SPARQL string literals."""
    # Escape backslashes first, then other special chars
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    value = value.replace("'", "\\'")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")
    value = value.replace("\t", "\\t")
    return value


def escape_regex_pattern(pattern: str) -> str:
    """Escape a pattern for safe use in SPARQL REGEX function."""
    # First escape regex metacharacters that could alter the pattern meaning
    regex_meta = r"\.[]{}()*+?^$|"
    escaped = []
    for char in pattern:
        if char in regex_meta:
            escaped.append("\\" + char)
        else:
            escaped.append(char)
    result = "".join(escaped)
    # Then escape for SPARQL string context
    return escape_sparql_string(result)


def validate_limit(limit: int, max_limit: int = 10000) -> int:
    """Validate a LIMIT value."""
    if not isinstance(limit, int) or limit < 0:
        raise ValueError(f"Limit must be a non-negative integer, got: {limit}")
    if limit > max_limit:
        raise ValueError(f"Limit {limit} exceeds maximum allowed limit {max_limit}")
    return limit
