"""Tests for MCP prompt handlers."""

from unittest.mock import AsyncMock

import pytest
from mcp.types import TextContent

from rdf4j_mcp.backends.base import QueryResult
from rdf4j_mcp.prompts.prompts import (
    _get_explain_prompt,
    _get_explore_prompt,
    _get_sparql_prompt,
)


def _get_text(result, index: int = 0) -> str:
    """Extract text from a prompt message, with type narrowing for ty."""
    content = result.messages[index].content
    assert isinstance(content, TextContent)
    return content.text


@pytest.fixture
def mock_backend():
    """Create a mock backend for prompt tests."""
    backend = AsyncMock()
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
                },
                {
                    "class": {"value": "http://example.org/Project"},
                    "label": {"value": "Project"},
                },
            ],
            "properties": [
                {
                    "property": {"value": "http://example.org/name"},
                    "label": {"value": "name"},
                },
                {
                    "property": {"value": "http://example.org/worksOn"},
                    "label": {"value": "works on"},
                    "domain": {"value": "http://example.org/Person"},
                    "range": {"value": "http://example.org/Project"},
                },
            ],
        }
    )
    backend.sparql_select = AsyncMock(
        return_value=QueryResult(
            type="select",
            variables=["property", "range", "label"],
            bindings=[
                {
                    "property": {"value": "http://example.org/name"},
                    "range": {"value": "http://www.w3.org/2001/XMLSchema#string"},
                }
            ],
        )
    )
    return backend


class TestExplorePrompt:
    """Tests for explore_knowledge_graph prompt."""

    async def test_basic_explore(self, mock_backend):
        result = await _get_explore_prompt(mock_backend, {})
        assert result.description == "Knowledge graph exploration context"
        assert len(result.messages) == 1
        text = _get_text(result)
        assert "Total statements: 500" in text
        assert "Total classes: 15" in text
        assert "Person" in text
        assert "sparql_select" in text

    async def test_explore_with_repository_id(self, mock_backend):
        await _get_explore_prompt(mock_backend, {"repository_id": "my-repo"})
        mock_backend.get_schema_summary.assert_called_once_with("my-repo")

    async def test_explore_with_focus_area(self, mock_backend):
        result = await _get_explore_prompt(mock_backend, {"focus_area": "People and organizations"})
        text = _get_text(result)
        assert "People and organizations" in text

    async def test_explore_shows_namespaces(self, mock_backend):
        result = await _get_explore_prompt(mock_backend, {})
        text = _get_text(result)
        assert "rdf:" in text
        assert "ex:" in text

    async def test_explore_shows_tools(self, mock_backend):
        result = await _get_explore_prompt(mock_backend, {})
        text = _get_text(result)
        assert "describe_resource" in text
        assert "search_classes" in text
        assert "find_instances" in text


class TestSparqlPrompt:
    """Tests for write_sparql_query prompt."""

    async def test_basic_sparql(self, mock_backend):
        result = await _get_sparql_prompt(mock_backend, {"question": "Find all people"})
        assert result.description == "SPARQL query writing assistance"
        assert len(result.messages) == 1
        text = _get_text(result)
        assert "Find all people" in text
        assert "PREFIX" in text

    async def test_sparql_with_repository_id(self, mock_backend):
        await _get_sparql_prompt(mock_backend, {"question": "test", "repository_id": "my-repo"})
        mock_backend.get_schema_summary.assert_called_once_with("my-repo")

    async def test_sparql_shows_classes(self, mock_backend):
        result = await _get_sparql_prompt(mock_backend, {"question": "Find people"})
        text = _get_text(result)
        assert "Person" in text
        assert "Project" in text

    async def test_sparql_shows_properties(self, mock_backend):
        result = await _get_sparql_prompt(mock_backend, {"question": "Find people"})
        text = _get_text(result)
        assert "name" in text
        assert "worksOn" in text

    async def test_sparql_includes_guidelines(self, mock_backend):
        result = await _get_sparql_prompt(mock_backend, {"question": "test"})
        text = _get_text(result)
        assert "OPTIONAL" in text
        assert "LIMIT" in text


class TestExplainPrompt:
    """Tests for explain_ontology prompt."""

    async def test_basic_explain(self, mock_backend):
        result = await _get_explain_prompt(mock_backend, {})
        assert result.description == "Ontology explanation"
        assert len(result.messages) == 1
        text = _get_text(result)
        assert "Total statements: 500" in text
        assert "Person" in text

    async def test_explain_with_repository_id(self, mock_backend):
        await _get_explain_prompt(mock_backend, {"repository_id": "my-repo"})
        mock_backend.get_schema_summary.assert_called_once_with("my-repo")

    async def test_explain_with_focus_class(self, mock_backend):
        result = await _get_explain_prompt(
            mock_backend, {"focus_class": "http://example.org/Person"}
        )
        text = _get_text(result)
        assert "Focus Class" in text
        assert "http://example.org/Person" in text
        # Should have queried for class properties
        mock_backend.sparql_select.assert_called_once()

    async def test_explain_with_focus_class_query_failure(self, mock_backend):
        mock_backend.sparql_select.side_effect = Exception("Query failed")
        result = await _get_explain_prompt(
            mock_backend, {"focus_class": "http://example.org/Person"}
        )
        text = _get_text(result)
        # Should still include focus class even on error
        assert "Focus Class" in text
        assert "http://example.org/Person" in text

    async def test_explain_shows_structure_requests(self, mock_backend):
        result = await _get_explain_prompt(mock_backend, {})
        text = _get_text(result)
        assert "high-level summary" in text
        assert "main concepts" in text
