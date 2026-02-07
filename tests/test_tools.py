"""Tests for MCP tool handlers."""

import json
from unittest.mock import AsyncMock

import pytest

from rdf4j_mcp.backends.base import (
    NamespaceInfo,
    QueryResult,
    RepositoryInfo,
    StatisticsInfo,
)
from rdf4j_mcp.config import Settings
from rdf4j_mcp.tools.explore import (
    handle_describe_resource,
    handle_find_instances,
    handle_get_schema_summary,
    handle_search_classes,
    handle_search_properties,
)
from rdf4j_mcp.tools.metadata import (
    handle_get_current_repository,
    handle_get_namespaces,
    handle_get_statistics,
    handle_list_repositories,
    handle_select_repository,
)
from rdf4j_mcp.tools.query import (
    handle_query_tool,
    handle_sparql_ask,
    handle_sparql_construct,
    handle_sparql_select,
)


@pytest.fixture
def mock_backend():
    """Create a mock backend with standard return values."""
    backend = AsyncMock()
    backend.sparql_select = AsyncMock(
        return_value=QueryResult(
            type="select",
            variables=["s", "p"],
            bindings=[
                {
                    "s": {"type": "uri", "value": "http://example.org/alice"},
                    "p": {"type": "uri", "value": "http://example.org/name"},
                }
            ],
        )
    )
    backend.sparql_construct = AsyncMock(
        return_value=QueryResult(
            type="construct",
            triples=(
                "<http://example.org/alice> "
                "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
                "<http://example.org/Person> ."
            ),
        )
    )
    backend.sparql_ask = AsyncMock(return_value=QueryResult(type="ask", boolean=True))
    backend.describe_resource = AsyncMock(
        return_value=QueryResult(
            type="construct",
            triples=(
                "<http://example.org/alice> "
                "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
                "<http://example.org/Person> ."
            ),
        )
    )
    backend.search_classes = AsyncMock(
        return_value=QueryResult(
            type="select",
            variables=["class", "label", "comment"],
            bindings=[
                {
                    "class": {"type": "uri", "value": "http://example.org/Person"},
                    "label": {"type": "literal", "value": "Person"},
                }
            ],
        )
    )
    backend.search_properties = AsyncMock(
        return_value=QueryResult(
            type="select",
            variables=["property", "label", "domain", "range"],
            bindings=[
                {
                    "property": {"type": "uri", "value": "http://example.org/name"},
                    "label": {"type": "literal", "value": "name"},
                    "domain": {"type": "uri", "value": "http://example.org/Person"},
                    "range": {"type": "uri", "value": "http://www.w3.org/2001/XMLSchema#string"},
                }
            ],
        )
    )
    backend.find_instances = AsyncMock(
        return_value=QueryResult(
            type="select",
            variables=["instance", "label"],
            bindings=[
                {
                    "instance": {"type": "uri", "value": "http://example.org/alice"},
                    "label": {"type": "literal", "value": "Alice"},
                }
            ],
        )
    )
    backend.list_repositories = AsyncMock(
        return_value=[
            RepositoryInfo(
                id="test-repo",
                title="Test Repository",
                uri="http://localhost:8080/rdf4j-server/repositories/test-repo",
                readable=True,
                writable=True,
            ),
            RepositoryInfo(
                id="other-repo",
                title="Other Repository",
                uri="http://localhost:8080/rdf4j-server/repositories/other-repo",
                readable=True,
                writable=False,
            ),
        ]
    )
    backend.get_namespaces = AsyncMock(
        return_value=[
            NamespaceInfo(prefix="rdf", namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
            NamespaceInfo(prefix="rdfs", namespace="http://www.w3.org/2000/01/rdf-schema#"),
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
    backend.select_repository = AsyncMock()
    backend.get_current_repository = AsyncMock(return_value="test-repo")
    backend.get_schema_summary = AsyncMock(
        return_value={
            "statistics": {
                "total_statements": 500,
                "total_classes": 15,
                "total_properties": 30,
            },
            "namespaces": [
                {"prefix": "rdf", "namespace": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
                {"prefix": "ex", "namespace": "http://example.org/"},
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
                }
            ],
        }
    )
    return backend


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        rdf4j_server_url="http://localhost:8080/rdf4j-server",
        default_repository="test-repo",
        default_limit=100,
        max_limit=10000,
    )


# --- Query tool tests ---


class TestSparqlSelect:
    """Tests for sparql_select handler."""

    async def test_basic_select(self, mock_backend, settings):
        result = await handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s a <http://example.org/Person> }"},
            settings,
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "select"
        assert data["count"] == 1
        assert data["variables"] == ["s", "p"]
        assert len(data["bindings"]) == 1

    async def test_select_adds_limit_when_missing(self, mock_backend, settings):
        await handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s ?p ?o }"},
            settings,
        )
        called_query = mock_backend.sparql_select.call_args[0][0]
        # Pagination requests limit+1 rows to detect has_more
        assert "LIMIT 101" in called_query

    async def test_select_respects_explicit_limit_in_query(self, mock_backend, settings):
        query = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 50"
        await handle_sparql_select(
            mock_backend,
            {"query": query},
            settings,
        )
        called_query = mock_backend.sparql_select.call_args[0][0]
        # Should not add another LIMIT
        assert called_query == query

    async def test_select_with_custom_limit_arg(self, mock_backend, settings):
        await handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s ?p ?o }", "limit": 25},
            settings,
        )
        called_query = mock_backend.sparql_select.call_args[0][0]
        # Pagination requests limit+1 rows to detect has_more
        assert "LIMIT 26" in called_query

    async def test_select_limit_capped_by_max(self, mock_backend, settings):
        settings.max_limit = 50
        await handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s ?p ?o }", "limit": 999},
            settings,
        )
        called_query = mock_backend.sparql_select.call_args[0][0]
        # Pagination requests limit+1 rows to detect has_more
        assert "LIMIT 51" in called_query

    async def test_select_with_repository_id(self, mock_backend, settings):
        await handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s ?p ?o }", "repository_id": "other-repo"},
            settings,
        )
        mock_backend.sparql_select.assert_called_once()
        assert mock_backend.sparql_select.call_args[0][1] == "other-repo"

    async def test_select_with_empty_bindings(self, mock_backend, settings):
        mock_backend.sparql_select.return_value = QueryResult(
            type="select", variables=["s"], bindings=None
        )
        result = await handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s ?p ?o }"},
            settings,
        )
        data = json.loads(result[0].text)
        assert data["count"] == 0
        assert data["bindings"] == []


class TestSparqlConstruct:
    """Tests for sparql_construct handler."""

    async def test_basic_construct(self, mock_backend):
        result = await handle_sparql_construct(
            mock_backend,
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
        )
        assert len(result) == 1
        assert "Turtle" in result[0].text
        assert "alice" in result[0].text

    async def test_construct_with_repository_id(self, mock_backend):
        await handle_sparql_construct(
            mock_backend,
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", "repository_id": "my-repo"},
        )
        mock_backend.sparql_construct.assert_called_once()
        assert mock_backend.sparql_construct.call_args[0][1] == "my-repo"

    async def test_construct_empty_result(self, mock_backend):
        mock_backend.sparql_construct.return_value = QueryResult(type="construct", triples=None)
        result = await handle_sparql_construct(
            mock_backend,
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"},
        )
        assert len(result) == 1
        assert "Turtle" in result[0].text


class TestSparqlAsk:
    """Tests for sparql_ask handler."""

    async def test_ask_true(self, mock_backend):
        result = await handle_sparql_ask(
            mock_backend,
            {"query": "ASK { ?s a <http://example.org/Person> }"},
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "ask"
        assert data["result"] is True

    async def test_ask_false(self, mock_backend):
        mock_backend.sparql_ask.return_value = QueryResult(type="ask", boolean=False)
        result = await handle_sparql_ask(
            mock_backend,
            {"query": "ASK { ?s a <http://example.org/Nonexistent> }"},
        )
        data = json.loads(result[0].text)
        assert data["result"] is False

    async def test_ask_with_repository_id(self, mock_backend):
        await handle_sparql_ask(
            mock_backend,
            {"query": "ASK { ?s ?p ?o }", "repository_id": "other-repo"},
        )
        mock_backend.sparql_ask.assert_called_once()
        assert mock_backend.sparql_ask.call_args[0][1] == "other-repo"


class TestQueryToolDispatch:
    """Tests for the query tool dispatcher."""

    async def test_dispatch_sparql_select(self, mock_backend, settings):
        result = await handle_query_tool(
            "sparql_select",
            {"query": "SELECT ?s WHERE { ?s ?p ?o }"},
            mock_backend,
            settings,
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "select"

    async def test_dispatch_sparql_construct(self, mock_backend, settings):
        result = await handle_query_tool(
            "sparql_construct",
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"},
            mock_backend,
            settings,
        )
        assert len(result) == 1
        assert "Turtle" in result[0].text

    async def test_dispatch_sparql_ask(self, mock_backend, settings):
        result = await handle_query_tool(
            "sparql_ask",
            {"query": "ASK { ?s ?p ?o }"},
            mock_backend,
            settings,
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "ask"

    async def test_dispatch_unknown_tool(self, mock_backend, settings):
        with pytest.raises(ValueError, match="Unknown query tool"):
            await handle_query_tool("unknown_tool", {}, mock_backend, settings)


# --- Explore tool tests ---


class TestDescribeResource:
    """Tests for describe_resource handler."""

    async def test_basic_describe(self, mock_backend):
        result = await handle_describe_resource(
            mock_backend,
            {"iri": "http://example.org/alice"},
        )
        assert len(result) == 1
        text = result[0].text
        assert "Resource Summary" in text
        assert "http://example.org/alice" in text

    async def test_describe_with_incoming(self, mock_backend):
        result = await handle_describe_resource(
            mock_backend,
            {"iri": "http://example.org/alice", "include_incoming": True},
        )
        # Should call sparql_construct for incoming triples
        assert mock_backend.sparql_construct.called
        text = result[0].text
        assert "Incoming triples" in text

    async def test_describe_without_incoming(self, mock_backend):
        mock_backend.sparql_construct.reset_mock()
        result = await handle_describe_resource(
            mock_backend,
            {"iri": "http://example.org/alice", "include_incoming": False},
        )
        text = result[0].text
        assert "Incoming triples" not in text

    async def test_describe_shows_types(self, mock_backend):
        mock_backend.sparql_select.return_value = QueryResult(
            type="select",
            variables=["type"],
            bindings=[
                {"type": {"type": "uri", "value": "http://example.org/Person"}},
            ],
        )
        result = await handle_describe_resource(
            mock_backend,
            {"iri": "http://example.org/alice", "include_incoming": False},
        )
        text = result[0].text
        assert "Person" in text

    async def test_describe_with_repository_id(self, mock_backend):
        await handle_describe_resource(
            mock_backend,
            {"iri": "http://example.org/alice", "repository_id": "other-repo"},
        )
        mock_backend.describe_resource.assert_called_once_with(
            "http://example.org/alice", "other-repo"
        )


class TestSearchClasses:
    """Tests for search_classes handler."""

    async def test_basic_search(self, mock_backend):
        result = await handle_search_classes(mock_backend, {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "classes"
        assert data["count"] == 1
        assert data["classes"][0]["iri"] == "http://example.org/Person"
        assert data["classes"][0]["label"] == "Person"

    async def test_search_with_pattern(self, mock_backend):
        await handle_search_classes(mock_backend, {"pattern": "Pers"})
        mock_backend.search_classes.assert_called_once_with("Pers", 100, None)

    async def test_search_with_limit(self, mock_backend):
        await handle_search_classes(mock_backend, {"limit": 10})
        mock_backend.search_classes.assert_called_once_with(None, 10, None)

    async def test_search_with_repository_id(self, mock_backend):
        await handle_search_classes(mock_backend, {"repository_id": "other-repo"})
        mock_backend.search_classes.assert_called_once_with(None, 100, "other-repo")

    async def test_search_empty_results(self, mock_backend):
        mock_backend.search_classes.return_value = QueryResult(
            type="select", variables=["class"], bindings=[]
        )
        result = await handle_search_classes(mock_backend, {})
        data = json.loads(result[0].text)
        assert data["count"] == 0
        assert data["classes"] == []


class TestSearchProperties:
    """Tests for search_properties handler."""

    async def test_basic_search(self, mock_backend):
        result = await handle_search_properties(mock_backend, {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "properties"
        assert data["count"] == 1
        assert data["properties"][0]["iri"] == "http://example.org/name"

    async def test_search_with_pattern(self, mock_backend):
        await handle_search_properties(mock_backend, {"pattern": "nam"})
        mock_backend.search_properties.assert_called_once_with("nam", None, None, 100, None)

    async def test_search_with_domain(self, mock_backend):
        await handle_search_properties(mock_backend, {"domain": "http://example.org/Person"})
        mock_backend.search_properties.assert_called_once_with(
            None, "http://example.org/Person", None, 100, None
        )

    async def test_search_with_range(self, mock_backend):
        await handle_search_properties(
            mock_backend, {"range": "http://www.w3.org/2001/XMLSchema#string"}
        )
        mock_backend.search_properties.assert_called_once_with(
            None, None, "http://www.w3.org/2001/XMLSchema#string", 100, None
        )

    async def test_search_includes_domain_range_in_output(self, mock_backend):
        result = await handle_search_properties(mock_backend, {})
        data = json.loads(result[0].text)
        prop = data["properties"][0]
        assert prop["domain"] == "http://example.org/Person"
        assert prop["range"] == "http://www.w3.org/2001/XMLSchema#string"


class TestFindInstances:
    """Tests for find_instances handler."""

    async def test_basic_find(self, mock_backend):
        result = await handle_find_instances(
            mock_backend,
            {"class_iri": "http://example.org/Person"},
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "instances"
        assert data["class"] == "http://example.org/Person"
        assert data["count"] == 1
        assert data["instances"][0]["iri"] == "http://example.org/alice"
        assert data["instances"][0]["label"] == "Alice"

    async def test_find_with_limit(self, mock_backend):
        await handle_find_instances(
            mock_backend,
            {"class_iri": "http://example.org/Person", "limit": 5},
        )
        mock_backend.find_instances.assert_called_once_with("http://example.org/Person", 5, None)

    async def test_find_with_repository_id(self, mock_backend):
        await handle_find_instances(
            mock_backend,
            {"class_iri": "http://example.org/Person", "repository_id": "other-repo"},
        )
        mock_backend.find_instances.assert_called_once_with(
            "http://example.org/Person", 100, "other-repo"
        )


class TestGetSchemaSummary:
    """Tests for get_schema_summary handler."""

    async def test_basic_summary(self, mock_backend):
        result = await handle_get_schema_summary(mock_backend, {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "schema_summary"
        assert data["statistics"]["total_statements"] == 500
        assert data["statistics"]["total_classes"] == 15
        assert len(data["namespaces"]) == 2
        assert len(data["top_classes"]) == 1
        assert len(data["top_properties"]) == 1

    async def test_summary_with_repository_id(self, mock_backend):
        await handle_get_schema_summary(mock_backend, {"repository_id": "other-repo"})
        mock_backend.get_schema_summary.assert_called_once_with("other-repo")

    async def test_summary_limits_classes_and_properties(self, mock_backend):
        """Schema summary truncates to 20 classes and 20 properties."""
        many_classes = [{"class": {"value": f"http://example.org/Class{i}"}} for i in range(30)]
        many_props = [{"property": {"value": f"http://example.org/prop{i}"}} for i in range(30)]
        mock_backend.get_schema_summary.return_value = {
            "statistics": {"total_statements": 1, "total_classes": 30, "total_properties": 30},
            "namespaces": [],
            "classes": many_classes,
            "properties": many_props,
        }
        result = await handle_get_schema_summary(mock_backend, {})
        data = json.loads(result[0].text)
        assert len(data["top_classes"]) == 20
        assert len(data["top_properties"]) == 20


# --- Metadata tool tests ---


class TestListRepositories:
    """Tests for list_repositories handler."""

    async def test_list_repos(self, mock_backend):
        result = await handle_list_repositories(mock_backend)
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "repositories"
        assert data["count"] == 2
        assert data["repositories"][0]["id"] == "test-repo"
        assert data["repositories"][0]["readable"] is True
        assert data["repositories"][1]["id"] == "other-repo"
        assert data["repositories"][1]["writable"] is False

    async def test_list_empty_repos(self, mock_backend):
        mock_backend.list_repositories.return_value = []
        result = await handle_list_repositories(mock_backend)
        data = json.loads(result[0].text)
        assert data["count"] == 0
        assert data["repositories"] == []


class TestGetNamespaces:
    """Tests for get_namespaces handler."""

    async def test_basic_namespaces(self, mock_backend):
        result = await handle_get_namespaces(mock_backend, {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "namespaces"
        assert data["count"] == 3
        assert any(ns["prefix"] == "rdf" for ns in data["namespaces"])
        assert "PREFIX rdf:" in data["sparql_prefixes"]
        assert "PREFIX ex:" in data["sparql_prefixes"]

    async def test_namespaces_with_repository_id(self, mock_backend):
        await handle_get_namespaces(mock_backend, {"repository_id": "other-repo"})
        mock_backend.get_namespaces.assert_called_once_with("other-repo")

    async def test_namespaces_skips_empty_prefix(self, mock_backend):
        mock_backend.get_namespaces.return_value = [
            NamespaceInfo(prefix="", namespace="http://example.org/default/"),
            NamespaceInfo(prefix="ex", namespace="http://example.org/"),
        ]
        result = await handle_get_namespaces(mock_backend, {})
        data = json.loads(result[0].text)
        # Empty prefix should be in the list but not in sparql_prefixes
        assert data["count"] == 2
        assert "PREFIX :" not in data["sparql_prefixes"]
        assert "PREFIX ex:" in data["sparql_prefixes"]


class TestGetStatistics:
    """Tests for get_statistics handler."""

    async def test_basic_statistics(self, mock_backend):
        result = await handle_get_statistics(mock_backend, {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "statistics"
        assert data["total_statements"] == 500
        assert data["total_classes"] == 15
        assert data["total_properties"] == 30
        assert data["total_subjects"] == 100
        assert data["total_objects"] == 200

    async def test_statistics_with_repository_id(self, mock_backend):
        await handle_get_statistics(mock_backend, {"repository_id": "other-repo"})
        mock_backend.get_statistics.assert_called_once_with("other-repo")


class TestSelectRepository:
    """Tests for select_repository handler."""

    async def test_select_repo(self, mock_backend):
        result = await handle_select_repository(mock_backend, {"repository_id": "new-repo"})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "repository_selected"
        assert data["repository_id"] == "new-repo"
        assert "new-repo" in data["message"]
        mock_backend.select_repository.assert_called_once_with("new-repo")


class TestGetCurrentRepository:
    """Tests for get_current_repository handler."""

    async def test_get_current(self, mock_backend):
        result = await handle_get_current_repository(mock_backend)
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "current_repository"
        assert data["repository_id"] == "test-repo"
        assert "test-repo" in data["message"]

    async def test_get_current_none(self, mock_backend):
        mock_backend.get_current_repository.return_value = None
        result = await handle_get_current_repository(mock_backend)
        data = json.loads(result[0].text)
        assert data["repository_id"] is None
        assert "No repository selected" in data["message"]
