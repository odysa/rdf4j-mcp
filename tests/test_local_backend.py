"""Tests for the local backend."""

import pytest

from rdf4j_mcp.backends.local import LocalBackend


@pytest.fixture
async def backend():
    """Create a local backend for testing."""
    backend = LocalBackend()
    await backend.connect()
    yield backend
    await backend.close()


@pytest.fixture
async def backend_with_data(backend):
    """Backend with sample RDF data loaded."""
    sample_turtle = """
    @prefix ex: <http://example.org/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .

    ex:Person a owl:Class ;
        rdfs:label "Person" ;
        rdfs:comment "A human being" .

    ex:Organization a owl:Class ;
        rdfs:label "Organization" .

    ex:name a owl:DatatypeProperty ;
        rdfs:label "name" ;
        rdfs:domain ex:Person .

    ex:worksFor a owl:ObjectProperty ;
        rdfs:label "works for" ;
        rdfs:domain ex:Person ;
        rdfs:range ex:Organization .

    ex:alice a ex:Person ;
        ex:name "Alice" ;
        ex:worksFor ex:acme .

    ex:bob a ex:Person ;
        ex:name "Bob" ;
        ex:worksFor ex:acme .

    ex:acme a ex:Organization ;
        ex:name "Acme Corp" .
    """
    await backend.load_data(sample_turtle, format="turtle")
    return backend


class TestLocalBackendBasics:
    """Test basic backend operations."""

    async def test_connect_disconnect(self):
        """Test connecting and disconnecting."""
        backend = LocalBackend()
        await backend.connect()
        assert backend._graph is not None
        await backend.close()
        assert backend._graph is None

    async def test_list_repositories(self, backend):
        """Test listing repositories."""
        repos = await backend.list_repositories()
        assert len(repos) == 1
        assert repos[0].id == "local"
        assert repos[0].title == "Local RDF Store"

    async def test_get_current_repository(self, backend):
        """Test getting current repository."""
        current = await backend.get_current_repository()
        assert current == "local"

    async def test_select_repository_invalid(self, backend):
        """Test selecting invalid repository raises error."""
        with pytest.raises(ValueError):
            await backend.select_repository("nonexistent")


class TestSPARQLQueries:
    """Test SPARQL query operations."""

    async def test_sparql_select_empty(self, backend):
        """Test SELECT on empty graph."""
        result = await backend.sparql_select("SELECT * WHERE { ?s ?p ?o }")
        assert result.type == "select"
        assert result.bindings == []

    async def test_sparql_select_with_data(self, backend_with_data):
        """Test SELECT with data."""
        result = await backend_with_data.sparql_select(
            "SELECT ?name WHERE { ?s <http://example.org/name> ?name }"
        )
        assert result.type == "select"
        assert len(result.bindings) == 3  # Alice, Bob, Acme Corp
        names = [b["name"]["value"] for b in result.bindings]
        assert "Alice" in names
        assert "Bob" in names
        assert "Acme Corp" in names

    async def test_sparql_construct(self, backend_with_data):
        """Test CONSTRUCT query."""
        result = await backend_with_data.sparql_construct(
            "CONSTRUCT { ?s ?p ?o } WHERE { ?s a <http://example.org/Person> . ?s ?p ?o }"
        )
        assert result.type == "construct"
        assert result.triples is not None
        assert "Alice" in result.triples

    async def test_sparql_ask_true(self, backend_with_data):
        """Test ASK query returning true."""
        result = await backend_with_data.sparql_ask(
            "ASK { ?s a <http://example.org/Person> }"
        )
        assert result.type == "ask"
        assert result.boolean is True

    async def test_sparql_ask_false(self, backend_with_data):
        """Test ASK query returning false."""
        result = await backend_with_data.sparql_ask(
            "ASK { ?s a <http://example.org/NonExistent> }"
        )
        assert result.type == "ask"
        assert result.boolean is False


class TestExplorationMethods:
    """Test knowledge graph exploration methods."""

    async def test_search_classes(self, backend_with_data):
        """Test searching for classes."""
        result = await backend_with_data.search_classes()
        assert result.type == "select"
        assert len(result.bindings) > 0

        # Check we found our classes
        class_iris = [b.get("class", {}).get("value", "") for b in result.bindings]
        assert any("Person" in c for c in class_iris)
        assert any("Organization" in c for c in class_iris)

    async def test_search_classes_with_pattern(self, backend_with_data):
        """Test searching classes with pattern."""
        result = await backend_with_data.search_classes(pattern="Person")
        assert result.type == "select"
        assert len(result.bindings) > 0

        class_iris = [b.get("class", {}).get("value", "") for b in result.bindings]
        assert any("Person" in c for c in class_iris)

    async def test_search_properties(self, backend_with_data):
        """Test searching for properties."""
        result = await backend_with_data.search_properties()
        assert result.type == "select"
        assert len(result.bindings) > 0

    async def test_search_properties_with_domain(self, backend_with_data):
        """Test searching properties with domain filter."""
        result = await backend_with_data.search_properties(
            domain="http://example.org/Person"
        )
        assert result.type == "select"

    async def test_find_instances(self, backend_with_data):
        """Test finding instances of a class."""
        result = await backend_with_data.find_instances(
            class_iri="http://example.org/Person"
        )
        assert result.type == "select"
        assert len(result.bindings) == 2  # Alice and Bob

        instance_iris = [b.get("instance", {}).get("value", "") for b in result.bindings]
        assert any("alice" in i for i in instance_iris)
        assert any("bob" in i for i in instance_iris)

    async def test_describe_resource(self, backend_with_data):
        """Test describing a resource."""
        result = await backend_with_data.describe_resource(
            iri="http://example.org/alice"
        )
        assert result.type == "construct"
        assert result.triples is not None
        assert "alice" in result.triples


class TestStatistics:
    """Test statistics retrieval."""

    async def test_get_statistics_empty(self, backend):
        """Test statistics on empty graph."""
        stats = await backend.get_statistics()
        assert stats.total_statements == 0

    async def test_get_statistics_with_data(self, backend_with_data):
        """Test statistics with data."""
        stats = await backend_with_data.get_statistics()
        assert stats.total_statements > 0
        assert stats.total_classes > 0
        assert stats.total_properties > 0
        assert stats.total_subjects > 0
        assert stats.total_objects > 0


class TestNamespaces:
    """Test namespace operations."""

    async def test_get_namespaces(self, backend):
        """Test getting namespaces."""
        namespaces = await backend.get_namespaces()
        # Should have default namespaces bound
        prefixes = [ns.prefix for ns in namespaces]
        assert "rdf" in prefixes
        assert "rdfs" in prefixes
        assert "owl" in prefixes


class TestSchemaSummary:
    """Test schema summary."""

    async def test_get_schema_summary(self, backend_with_data):
        """Test getting schema summary."""
        summary = await backend_with_data.get_schema_summary()

        assert "statistics" in summary
        assert "classes" in summary
        assert "properties" in summary
        assert "namespaces" in summary

        assert summary["statistics"]["total_statements"] > 0
        assert len(summary["classes"]) > 0
        assert len(summary["properties"]) > 0


class TestDataLoading:
    """Test data loading operations."""

    async def test_load_data_turtle(self, backend):
        """Test loading Turtle data."""
        turtle = """
        @prefix ex: <http://example.org/> .
        ex:test ex:value "hello" .
        """
        count = await backend.load_data(turtle, format="turtle")
        assert count == 1

    async def test_load_data_multiple(self, backend):
        """Test loading multiple triples."""
        turtle = """
        @prefix ex: <http://example.org/> .
        ex:a ex:b ex:c .
        ex:d ex:e ex:f .
        ex:g ex:h ex:i .
        """
        count = await backend.load_data(turtle, format="turtle")
        assert count == 3


class TestContextManager:
    """Test async context manager."""

    async def test_context_manager(self):
        """Test using backend as context manager."""
        async with LocalBackend() as backend:
            assert backend._graph is not None
            repos = await backend.list_repositories()
            assert len(repos) == 1
        assert backend._graph is None
