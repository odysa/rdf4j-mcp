"""Tests for the MCP server."""

import pytest

from rdf4j_mcp.config import BackendType, Settings
from rdf4j_mcp.server import RDF4JMCPServer, create_server


class TestServerCreation:
    """Test server creation and initialization."""

    def test_create_server_default(self):
        """Test creating server with default settings."""
        server = create_server()
        assert server is not None
        assert server._settings.backend_type == BackendType.LOCAL

    def test_create_server_custom_settings(self):
        """Test creating server with custom settings."""
        settings = Settings(
            backend_type=BackendType.LOCAL,
            query_timeout=60,
            default_limit=50,
        )
        server = create_server(settings)
        assert server._settings.query_timeout == 60
        assert server._settings.default_limit == 50


class TestServerWithLocalBackend:
    """Test server operations with local backend."""

    @pytest.fixture
    async def server(self):
        """Create and start a server for testing."""
        settings = Settings(backend_type=BackendType.LOCAL)
        server = RDF4JMCPServer(settings)
        await server.start()
        yield server
        await server.stop()

    @pytest.fixture
    async def server_with_data(self, server):
        """Server with sample data loaded."""
        from rdf4j_mcp.backends.local import LocalBackend

        backend = server._get_backend()
        if isinstance(backend, LocalBackend):
            sample_turtle = """
            @prefix ex: <http://example.org/> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

            ex:Person a owl:Class ;
                rdfs:label "Person" .

            ex:name a owl:DatatypeProperty ;
                rdfs:domain ex:Person .

            ex:alice a ex:Person ;
                ex:name "Alice" .

            ex:bob a ex:Person ;
                ex:name "Bob" .
            """
            await backend.load_data(sample_turtle, format="turtle")
        return server

    async def test_server_start_stop(self, server):
        """Test server start and stop."""
        assert server._backend is not None
        await server.stop()
        assert server._backend is None

    async def test_get_backend(self, server):
        """Test getting backend from started server."""
        backend = server._get_backend()
        assert backend is not None

    async def test_get_backend_not_started(self):
        """Test getting backend from unstarted server raises error."""
        server = RDF4JMCPServer()
        with pytest.raises(RuntimeError):
            server._get_backend()


class TestToolHandlers:
    """Test individual tool handlers."""

    @pytest.fixture
    async def server_with_data(self):
        """Server with sample data."""
        settings = Settings(backend_type=BackendType.LOCAL)
        server = RDF4JMCPServer(settings)
        await server.start()

        from rdf4j_mcp.backends.local import LocalBackend

        backend = server._get_backend()
        if isinstance(backend, LocalBackend):
            sample_turtle = """
            @prefix ex: <http://example.org/> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

            ex:Person a owl:Class ;
                rdfs:label "Person" .

            ex:name a owl:DatatypeProperty .

            ex:alice a ex:Person ;
                ex:name "Alice" .
            """
            await backend.load_data(sample_turtle, format="turtle")

        yield server
        await server.stop()

    async def test_handle_sparql_select(self, server_with_data):
        """Test SPARQL SELECT handler."""
        import json

        backend = server_with_data._get_backend()
        result = await server_with_data._handle_sparql_select(
            backend,
            {"query": "SELECT ?s WHERE { ?s a <http://example.org/Person> }"},
            server_with_data._settings,
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "select"
        assert data["count"] >= 1

    async def test_handle_sparql_construct(self, server_with_data):
        """Test SPARQL CONSTRUCT handler."""
        backend = server_with_data._get_backend()
        result = await server_with_data._handle_sparql_construct(
            backend,
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
        )

        assert len(result) == 1
        assert "Turtle" in result[0].text

    async def test_handle_sparql_ask(self, server_with_data):
        """Test SPARQL ASK handler."""
        import json

        backend = server_with_data._get_backend()
        result = await server_with_data._handle_sparql_ask(
            backend,
            {"query": "ASK { ?s a <http://example.org/Person> }"},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "ask"
        assert data["result"] is True

    async def test_handle_describe_resource(self, server_with_data):
        """Test describe_resource handler."""
        backend = server_with_data._get_backend()
        result = await server_with_data._handle_describe_resource(
            backend,
            {"iri": "http://example.org/alice"},
        )

        assert len(result) == 1
        assert "alice" in result[0].text

    async def test_handle_search_classes(self, server_with_data):
        """Test search_classes handler."""
        import json

        backend = server_with_data._get_backend()
        result = await server_with_data._handle_search_classes(
            backend,
            {},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "classes"

    async def test_handle_get_schema_summary(self, server_with_data):
        """Test get_schema_summary handler."""
        import json

        backend = server_with_data._get_backend()
        result = await server_with_data._handle_get_schema_summary(
            backend,
            {},
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["type"] == "schema_summary"
        assert "statistics" in data
        assert "namespaces" in data
