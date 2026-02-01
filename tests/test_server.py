"""Tests for the MCP server."""

from unittest.mock import AsyncMock, patch

import pytest

from rdf4j_mcp.backends.base import (
    NamespaceInfo,
    QueryResult,
    RepositoryInfo,
    StatisticsInfo,
)
from rdf4j_mcp.config import Settings
from rdf4j_mcp.server import RDF4JMCPServer, ReadonlyError, create_server


class TestServerCreation:
    """Test server creation and initialization."""

    def test_create_server_default(self):
        """Test creating server with default settings."""
        server = create_server()
        assert server is not None
        assert server._settings.rdf4j_server_url == "http://localhost:8080/rdf4j-server"

    def test_create_server_custom_settings(self):
        """Test creating server with custom settings."""
        settings = Settings(
            rdf4j_server_url="http://custom:9999/rdf4j",
            query_timeout=60,
            default_limit=50,
        )
        server = create_server(settings)
        assert server._settings.rdf4j_server_url == "http://custom:9999/rdf4j"
        assert server._settings.query_timeout == 60
        assert server._settings.default_limit == 50


class TestServerWithMockedBackend:
    """Test server operations with mocked backend."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        backend = AsyncMock()
        backend.connect = AsyncMock()
        backend.close = AsyncMock()
        backend.list_repositories = AsyncMock(
            return_value=[
                RepositoryInfo(
                    id="test-repo",
                    title="Test Repository",
                    uri="http://localhost:8080/rdf4j-server/repositories/test-repo",
                    readable=True,
                    writable=True,
                )
            ]
        )
        backend.get_current_repository = AsyncMock(return_value="test-repo")
        backend.select_repository = AsyncMock()
        backend.get_namespaces = AsyncMock(
            return_value=[
                NamespaceInfo(
                    prefix="rdf", namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                ),
                NamespaceInfo(prefix="rdfs", namespace="http://www.w3.org/2000/01/rdf-schema#"),
            ]
        )
        backend.get_statistics = AsyncMock(
            return_value=StatisticsInfo(
                total_statements=100,
                total_classes=10,
                total_properties=20,
                total_subjects=50,
                total_objects=80,
            )
        )
        backend.sparql_select = AsyncMock(
            return_value=QueryResult(
                type="select",
                variables=["s"],
                bindings=[{"s": {"type": "uri", "value": "http://example.org/alice"}}],
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
                variables=["class", "label"],
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
                variables=["property", "label"],
                bindings=[
                    {
                        "property": {"type": "uri", "value": "http://example.org/name"},
                        "label": {"type": "literal", "value": "name"},
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
        backend.get_schema_summary = AsyncMock(
            return_value={
                "statistics": {
                    "total_statements": 100,
                    "total_classes": 10,
                    "total_properties": 20,
                },
                "namespaces": [
                    {"prefix": "rdf", "namespace": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
                ],
                "classes": [
                    {"class": {"value": "http://example.org/Person"}, "label": {"value": "Person"}}
                ],
                "properties": [
                    {"property": {"value": "http://example.org/name"}, "label": {"value": "name"}}
                ],
            }
        )
        return backend

    @pytest.fixture
    async def server_with_mock(self, mock_backend):
        """Create server with mocked backend."""
        settings = Settings(
            rdf4j_server_url="http://localhost:8080/rdf4j-server",
            default_repository="test-repo",
        )
        server = RDF4JMCPServer(settings)

        with patch.object(server, "_create_backend", return_value=mock_backend):
            await server.start()
            yield server
            await server.stop()

    async def test_server_start_stop(self, server_with_mock, mock_backend):
        """Test server start and stop."""
        assert server_with_mock._backend is not None
        await server_with_mock.stop()
        assert server_with_mock._backend is None

    async def test_get_backend(self, server_with_mock):
        """Test getting backend from started server."""
        backend = server_with_mock._get_backend()
        assert backend is not None

    async def test_get_backend_not_started(self):
        """Test getting backend from unstarted server raises error."""
        server = RDF4JMCPServer()
        with pytest.raises(RuntimeError):
            server._get_backend()


class TestToolHandlers:
    """Test individual tool handlers."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend for tool handler tests."""
        backend = AsyncMock()
        backend.sparql_select = AsyncMock(
            return_value=QueryResult(
                type="select",
                variables=["s"],
                bindings=[{"s": {"type": "uri", "value": "http://example.org/alice"}}],
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
                variables=["class", "label"],
                bindings=[
                    {
                        "class": {"type": "uri", "value": "http://example.org/Person"},
                        "label": {"type": "literal", "value": "Person"},
                    }
                ],
            )
        )
        backend.get_schema_summary = AsyncMock(
            return_value={
                "statistics": {
                    "total_statements": 100,
                    "total_classes": 10,
                    "total_properties": 20,
                },
                "namespaces": [
                    {"prefix": "rdf", "namespace": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
                ],
                "classes": [
                    {"class": {"value": "http://example.org/Person"}, "label": {"value": "Person"}}
                ],
                "properties": [
                    {"property": {"value": "http://example.org/name"}, "label": {"value": "name"}}
                ],
            }
        )
        return backend

    @pytest.fixture
    async def server_with_mock(self, mock_backend):
        """Server with mock backend for tool tests."""
        settings = Settings(
            rdf4j_server_url="http://localhost:8080/rdf4j-server",
            default_repository="test-repo",
        )
        server = RDF4JMCPServer(settings)

        with patch.object(server, "_create_backend", return_value=mock_backend):
            await server.start()
            yield server
            await server.stop()

    async def test_handle_sparql_select(self, server_with_mock, mock_backend):
        """Test SPARQL SELECT handler."""
        import json

        result = await server_with_mock._handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s a <http://example.org/Person> }"},
            server_with_mock._settings,
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "select"
        assert data["count"] >= 1

    async def test_handle_sparql_construct(self, server_with_mock, mock_backend):
        """Test SPARQL CONSTRUCT handler."""
        result = await server_with_mock._handle_sparql_construct(
            mock_backend,
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
        )

        assert len(result) == 1
        assert "Turtle" in result[0].text

    async def test_handle_sparql_ask(self, server_with_mock, mock_backend):
        """Test SPARQL ASK handler."""
        import json

        result = await server_with_mock._handle_sparql_ask(
            mock_backend,
            {"query": "ASK { ?s a <http://example.org/Person> }"},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "ask"
        assert data["result"] is True

    async def test_handle_describe_resource(self, server_with_mock, mock_backend):
        """Test describe_resource handler."""
        result = await server_with_mock._handle_describe_resource(
            mock_backend,
            {"iri": "http://example.org/alice"},
        )

        assert len(result) == 1
        assert "alice" in result[0].text

    async def test_handle_search_classes(self, server_with_mock, mock_backend):
        """Test search_classes handler."""
        import json

        result = await server_with_mock._handle_search_classes(
            mock_backend,
            {},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "classes"

    async def test_handle_get_schema_summary(self, server_with_mock, mock_backend):
        """Test get_schema_summary handler."""
        import json

        result = await server_with_mock._handle_get_schema_summary(
            mock_backend,
            {},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "schema_summary"
        assert "statistics" in data
        assert "namespaces" in data


class TestReadonlyMode:
    """Test readonly mode functionality."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend for readonly tests."""
        backend = AsyncMock()
        backend.sparql_select = AsyncMock(
            return_value=QueryResult(
                type="select",
                variables=["s"],
                bindings=[{"s": {"type": "uri", "value": "http://example.org/alice"}}],
            )
        )
        backend.sparql_construct = AsyncMock(
            return_value=QueryResult(
                type="construct",
                triples="<http://example.org/alice> a <http://example.org/Person> .",
            )
        )
        backend.sparql_ask = AsyncMock(return_value=QueryResult(type="ask", boolean=True))
        return backend

    @pytest.fixture
    async def readonly_server(self, mock_backend):
        """Create a server with readonly mode enabled."""
        settings = Settings(
            rdf4j_server_url="http://localhost:8080/rdf4j-server",
            default_repository="test-repo",
            readonly=True,
        )
        server = RDF4JMCPServer(settings)

        with patch.object(server, "_create_backend", return_value=mock_backend):
            await server.start()
            yield server
            await server.stop()

    @pytest.fixture
    async def writable_server(self, mock_backend):
        """Create a server with readonly mode disabled."""
        settings = Settings(
            rdf4j_server_url="http://localhost:8080/rdf4j-server",
            default_repository="test-repo",
            readonly=False,
        )
        server = RDF4JMCPServer(settings)

        with patch.object(server, "_create_backend", return_value=mock_backend):
            await server.start()
            yield server
            await server.stop()

    async def test_readonly_blocks_insert(self, readonly_server, mock_backend):
        """Test that INSERT queries are blocked in readonly mode."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_select(
                mock_backend,
                {"query": "INSERT DATA { <http://ex.org/s> <http://ex.org/p> <http://ex.org/o> }"},
                readonly_server._settings,
            )

    async def test_readonly_blocks_delete(self, readonly_server, mock_backend):
        """Test that DELETE queries are blocked in readonly mode."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_select(
                mock_backend,
                {"query": "DELETE DATA { <http://ex.org/s> <http://ex.org/p> <http://ex.org/o> }"},
                readonly_server._settings,
            )

    async def test_readonly_blocks_load(self, readonly_server, mock_backend):
        """Test that LOAD queries are blocked in readonly mode."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_construct(
                mock_backend,
                {"query": "LOAD <http://example.org/data.ttl>"},
            )

    async def test_readonly_blocks_clear(self, readonly_server, mock_backend):
        """Test that CLEAR queries are blocked in readonly mode."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_ask(
                mock_backend,
                {"query": "CLEAR GRAPH <http://example.org/graph>"},
            )

    async def test_readonly_blocks_drop(self, readonly_server, mock_backend):
        """Test that DROP queries are blocked in readonly mode."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_select(
                mock_backend,
                {"query": "DROP GRAPH <http://example.org/graph>"},
                readonly_server._settings,
            )

    async def test_readonly_blocks_create(self, readonly_server, mock_backend):
        """Test that CREATE queries are blocked in readonly mode."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_select(
                mock_backend,
                {"query": "CREATE GRAPH <http://example.org/newgraph>"},
                readonly_server._settings,
            )

    async def test_readonly_allows_select(self, readonly_server, mock_backend):
        """Test that SELECT queries are allowed in readonly mode."""
        result = await readonly_server._handle_sparql_select(
            mock_backend,
            {"query": "SELECT ?s WHERE { ?s a <http://example.org/Person> }"},
            readonly_server._settings,
        )
        assert len(result) == 1

    async def test_readonly_allows_construct(self, readonly_server, mock_backend):
        """Test that CONSTRUCT queries are allowed in readonly mode."""
        result = await readonly_server._handle_sparql_construct(
            mock_backend,
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
        )
        assert len(result) == 1

    async def test_readonly_allows_ask(self, readonly_server, mock_backend):
        """Test that ASK queries are allowed in readonly mode."""
        result = await readonly_server._handle_sparql_ask(
            mock_backend,
            {"query": "ASK { ?s a <http://example.org/Person> }"},
        )
        assert len(result) == 1

    async def test_writable_allows_insert(self, writable_server, mock_backend):
        """Test that INSERT queries are allowed when not in readonly mode."""
        # This should not raise an error (backend call will be made)
        await writable_server._handle_sparql_select(
            mock_backend,
            {"query": "INSERT DATA { <http://ex.org/s> <http://ex.org/p> <http://ex.org/o> }"},
            writable_server._settings,
        )
        mock_backend.sparql_select.assert_called()

    async def test_check_readonly_case_insensitive(self, readonly_server, mock_backend):
        """Test that write detection is case-insensitive."""
        with pytest.raises(ReadonlyError):
            await readonly_server._handle_sparql_select(
                mock_backend,
                {"query": "insert data { <http://ex.org/s> <http://ex.org/p> <http://ex.org/o> }"},
                readonly_server._settings,
            )
