"""Tests for MCP resource handlers."""

import json
from unittest.mock import AsyncMock

import pytest

from rdf4j_mcp.backends.base import (
    NamespaceInfo,
    RepositoryInfo,
    StatisticsInfo,
)
from rdf4j_mcp.resources.resources import (
    _read_namespaces,
    _read_repositories,
    _read_repository_resource,
    _read_schema,
    _read_statistics,
)


@pytest.fixture
def mock_backend():
    """Create a mock backend for resource tests."""
    backend = AsyncMock()
    backend.list_repositories = AsyncMock(
        return_value=[
            RepositoryInfo(
                id="test-repo",
                title="Test Repository",
                uri="http://localhost:8080/rdf4j-server/repositories/test-repo",
                readable=True,
                writable=True,
            ),
        ]
    )
    backend.get_namespaces = AsyncMock(
        return_value=[
            NamespaceInfo(prefix="rdf", namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
            NamespaceInfo(prefix="ex", namespace="http://example.org/"),
        ]
    )
    backend.get_statistics = AsyncMock(
        return_value=StatisticsInfo(
            total_statements=500,
            total_classes=15,
            total_properties=30,
            total_subjects=100,
            total_objects=200,
        )
    )
    backend.get_schema_summary = AsyncMock(
        return_value={
            "statistics": {
                "total_statements": 500,
                "total_classes": 15,
                "total_properties": 30,
            },
            "namespaces": [
                {"prefix": "rdf", "namespace": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
            ],
            "classes": [
                {
                    "class": {"value": "http://example.org/Person"},
                    "label": {"value": "Person"},
                }
            ],
            "properties": [
                {
                    "property": {"value": "http://example.org/name"},
                    "label": {"value": "name"},
                    "domain": {"value": "http://example.org/Person"},
                    "range": {"value": "http://www.w3.org/2001/XMLSchema#string"},
                }
            ],
        }
    )
    return backend


class TestReadRepositories:
    """Tests for the repositories resource."""

    async def test_read_repositories(self, mock_backend):
        result = await _read_repositories(mock_backend)
        assert str(result.uri) == "rdf4j://repositories"
        assert result.mimeType == "application/json"
        data = json.loads(result.text)
        assert data["type"] == "repositories"
        assert data["count"] == 1
        assert data["repositories"][0]["id"] == "test-repo"
        assert data["repositories"][0]["title"] == "Test Repository"

    async def test_read_empty_repositories(self, mock_backend):
        mock_backend.list_repositories.return_value = []
        result = await _read_repositories(mock_backend)
        data = json.loads(result.text)
        assert data["count"] == 0
        assert data["repositories"] == []


class TestReadSchema:
    """Tests for the schema resource."""

    async def test_read_schema(self, mock_backend):
        result = await _read_schema(
            mock_backend, "test-repo", "rdf4j://repository/test-repo/schema"
        )
        assert result.mimeType == "application/json"
        data = json.loads(result.text)
        assert data["type"] == "schema_summary"
        assert data["repository_id"] == "test-repo"
        assert data["statistics"]["total_statements"] == 500
        assert len(data["classes"]) == 1
        assert data["classes"][0]["iri"] == "http://example.org/Person"
        assert len(data["properties"]) == 1
        assert data["properties"][0]["iri"] == "http://example.org/name"

    async def test_read_schema_calls_backend(self, mock_backend):
        await _read_schema(mock_backend, "my-repo", "rdf4j://repository/my-repo/schema")
        mock_backend.get_schema_summary.assert_called_once_with("my-repo")


class TestReadNamespaces:
    """Tests for the namespaces resource."""

    async def test_read_namespaces(self, mock_backend):
        result = await _read_namespaces(
            mock_backend, "test-repo", "rdf4j://repository/test-repo/namespaces"
        )
        assert result.mimeType == "application/json"
        data = json.loads(result.text)
        assert data["type"] == "namespaces"
        assert data["repository_id"] == "test-repo"
        assert data["count"] == 2
        assert "PREFIX rdf:" in data["sparql_prefixes"]
        assert "PREFIX ex:" in data["sparql_prefixes"]

    async def test_read_namespaces_calls_backend(self, mock_backend):
        await _read_namespaces(mock_backend, "my-repo", "rdf4j://repository/my-repo/namespaces")
        mock_backend.get_namespaces.assert_called_once_with("my-repo")

    async def test_read_namespaces_empty_prefix(self, mock_backend):
        mock_backend.get_namespaces.return_value = [
            NamespaceInfo(prefix="", namespace="http://example.org/default/"),
        ]
        result = await _read_namespaces(
            mock_backend, "test-repo", "rdf4j://repository/test-repo/namespaces"
        )
        data = json.loads(result.text)
        assert data["count"] == 1
        # Empty prefix should not generate a PREFIX declaration
        assert data["sparql_prefixes"] == ""


class TestReadStatistics:
    """Tests for the statistics resource."""

    async def test_read_statistics(self, mock_backend):
        result = await _read_statistics(
            mock_backend, "test-repo", "rdf4j://repository/test-repo/statistics"
        )
        assert result.mimeType == "application/json"
        data = json.loads(result.text)
        assert data["type"] == "statistics"
        assert data["repository_id"] == "test-repo"
        assert data["total_statements"] == 500
        assert data["total_classes"] == 15
        assert data["total_properties"] == 30
        assert data["total_subjects"] == 100
        assert data["total_objects"] == 200

    async def test_read_statistics_calls_backend(self, mock_backend):
        await _read_statistics(mock_backend, "my-repo", "rdf4j://repository/my-repo/statistics")
        mock_backend.get_statistics.assert_called_once_with("my-repo")


class TestReadRepositoryResource:
    """Tests for the repository resource dispatcher."""

    async def test_dispatch_schema(self, mock_backend):
        result = await _read_repository_resource(
            mock_backend, "rdf4j://repository/test-repo/schema"
        )
        data = json.loads(result.text)
        assert data["type"] == "schema_summary"

    async def test_dispatch_namespaces(self, mock_backend):
        result = await _read_repository_resource(
            mock_backend, "rdf4j://repository/test-repo/namespaces"
        )
        data = json.loads(result.text)
        assert data["type"] == "namespaces"

    async def test_dispatch_statistics(self, mock_backend):
        result = await _read_repository_resource(
            mock_backend, "rdf4j://repository/test-repo/statistics"
        )
        data = json.loads(result.text)
        assert data["type"] == "statistics"

    async def test_dispatch_unknown_type(self, mock_backend):
        with pytest.raises(ValueError, match="Unknown resource type"):
            await _read_repository_resource(mock_backend, "rdf4j://repository/test-repo/unknown")

    async def test_dispatch_invalid_uri(self, mock_backend):
        with pytest.raises(ValueError, match="Invalid repository resource URI"):
            await _read_repository_resource(mock_backend, "rdf4j://repository/test-repo")
