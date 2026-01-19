"""MCP Resources for RDF4J."""

import json
from typing import Any

from mcp.server import Server
from mcp.types import Resource, TextResourceContents

from ..backends.base import Backend


def register_resources(server: Server, get_backend: Any) -> None:
    """Register MCP resources with the server.

    Args:
        server: The MCP server instance
        get_backend: Callable that returns the backend instance
    """

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available resources."""
        backend: Backend = get_backend()
        resources = [
            Resource(
                uri="rdf4j://repositories",
                name="Repository List",
                description="List of all available RDF repositories",
                mimeType="application/json",
            ),
        ]

        # Add repository-specific resources
        try:
            repos = await backend.list_repositories()
            for repo in repos:
                resources.extend([
                    Resource(
                        uri=f"rdf4j://repository/{repo.id}/schema",
                        name=f"{repo.title} - Schema",
                        description=f"Schema summary for repository '{repo.id}'",
                        mimeType="application/json",
                    ),
                    Resource(
                        uri=f"rdf4j://repository/{repo.id}/namespaces",
                        name=f"{repo.title} - Namespaces",
                        description=f"Namespace prefixes for repository '{repo.id}'",
                        mimeType="application/json",
                    ),
                    Resource(
                        uri=f"rdf4j://repository/{repo.id}/statistics",
                        name=f"{repo.title} - Statistics",
                        description=f"Statistics for repository '{repo.id}'",
                        mimeType="application/json",
                    ),
                ])
        except Exception:
            # If we can't list repositories, just return base resources
            pass

        return resources

    @server.read_resource()
    async def read_resource(uri: str) -> TextResourceContents:
        """Read a resource by URI."""
        backend: Backend = get_backend()

        if uri == "rdf4j://repositories":
            return await _read_repositories(backend)
        elif uri.startswith("rdf4j://repository/"):
            return await _read_repository_resource(backend, uri)
        else:
            raise ValueError(f"Unknown resource URI: {uri}")


async def _read_repositories(backend: Backend) -> TextResourceContents:
    """Read the repositories list resource."""
    repos = await backend.list_repositories()

    content = {
        "type": "repositories",
        "count": len(repos),
        "repositories": [
            {
                "id": repo.id,
                "title": repo.title,
                "uri": repo.uri,
                "readable": repo.readable,
                "writable": repo.writable,
            }
            for repo in repos
        ],
    }

    return TextResourceContents(
        uri="rdf4j://repositories",
        mimeType="application/json",
        text=json.dumps(content, indent=2),
    )


async def _read_repository_resource(backend: Backend, uri: str) -> TextResourceContents:
    """Read a repository-specific resource."""
    # Parse URI: rdf4j://repository/{repo_id}/{resource_type}
    parts = uri.replace("rdf4j://repository/", "").split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repository resource URI: {uri}")

    repo_id, resource_type = parts

    if resource_type == "schema":
        return await _read_schema(backend, repo_id, uri)
    elif resource_type == "namespaces":
        return await _read_namespaces(backend, repo_id, uri)
    elif resource_type == "statistics":
        return await _read_statistics(backend, repo_id, uri)
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")


async def _read_schema(backend: Backend, repo_id: str, uri: str) -> TextResourceContents:
    """Read schema summary resource."""
    summary = await backend.get_schema_summary(repo_id)

    content = {
        "type": "schema_summary",
        "repository_id": repo_id,
        "statistics": summary["statistics"],
        "namespaces": summary["namespaces"],
        "classes": [
            {
                "iri": c.get("class", {}).get("value", ""),
                "label": c.get("label", {}).get("value", "") if "label" in c else None,
            }
            for c in summary["classes"][:50]
        ],
        "properties": [
            {
                "iri": p.get("property", {}).get("value", ""),
                "label": p.get("label", {}).get("value", "") if "label" in p else None,
                "domain": p.get("domain", {}).get("value", "") if "domain" in p else None,
                "range": p.get("range", {}).get("value", "") if "range" in p else None,
            }
            for p in summary["properties"][:50]
        ],
    }

    return TextResourceContents(
        uri=uri,
        mimeType="application/json",
        text=json.dumps(content, indent=2),
    )


async def _read_namespaces(backend: Backend, repo_id: str, uri: str) -> TextResourceContents:
    """Read namespaces resource."""
    namespaces = await backend.get_namespaces(repo_id)

    sparql_prefixes = []
    for ns in namespaces:
        if ns.prefix:
            sparql_prefixes.append(f"PREFIX {ns.prefix}: <{ns.namespace}>")

    content = {
        "type": "namespaces",
        "repository_id": repo_id,
        "count": len(namespaces),
        "namespaces": [
            {"prefix": ns.prefix, "namespace": ns.namespace}
            for ns in namespaces
        ],
        "sparql_prefixes": "\n".join(sparql_prefixes),
    }

    return TextResourceContents(
        uri=uri,
        mimeType="application/json",
        text=json.dumps(content, indent=2),
    )


async def _read_statistics(backend: Backend, repo_id: str, uri: str) -> TextResourceContents:
    """Read statistics resource."""
    stats = await backend.get_statistics(repo_id)

    content = {
        "type": "statistics",
        "repository_id": repo_id,
        "total_statements": stats.total_statements,
        "total_classes": stats.total_classes,
        "total_properties": stats.total_properties,
        "total_subjects": stats.total_subjects,
        "total_objects": stats.total_objects,
    }

    return TextResourceContents(
        uri=uri,
        mimeType="application/json",
        text=json.dumps(content, indent=2),
    )
