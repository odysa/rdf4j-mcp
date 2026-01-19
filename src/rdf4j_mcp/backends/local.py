"""Local RDF backend using rdflib."""

from typing import Any, Optional

import rdflib
from rdflib import RDF, RDFS, OWL, Graph, Namespace
from rdflib.query import ResultRow

from .base import (
    Backend,
    NamespaceInfo,
    QueryResult,
    RepositoryInfo,
    StatisticsInfo,
)


class LocalBackend(Backend):
    """Local RDF backend using rdflib for in-memory or file-based storage."""

    def __init__(
        self,
        store_path: Optional[str] = None,
        store_format: str = "turtle",
    ):
        """Initialize local backend.

        Args:
            store_path: Path to RDF file to load (optional)
            store_format: Format of RDF file (turtle, xml, n3, nt, nquads, trig, jsonld)
        """
        self._store_path = store_path
        self._store_format = store_format
        self._graph: Optional[Graph] = None
        self._repository_id = "local"

    async def connect(self) -> None:
        """Initialize the RDF graph."""
        self._graph = Graph()

        # Bind common namespaces
        self._graph.bind("rdf", RDF)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("owl", OWL)
        self._graph.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))

        # Load from file if specified
        if self._store_path:
            self._graph.parse(self._store_path, format=self._store_format)

    async def close(self) -> None:
        """Close the backend (no-op for local)."""
        self._graph = None

    def _ensure_connected(self) -> Graph:
        """Ensure graph is connected and return it."""
        if self._graph is None:
            raise RuntimeError("Backend not connected. Call connect() first.")
        return self._graph

    async def list_repositories(self) -> list[RepositoryInfo]:
        """List available repositories (returns single local repo)."""
        return [
            RepositoryInfo(
                id=self._repository_id,
                title="Local RDF Store",
                uri=self._store_path,
                readable=True,
                writable=True,
            )
        ]

    async def select_repository(self, repository_id: str) -> None:
        """Select repository (no-op for local, only one repo)."""
        if repository_id != self._repository_id:
            raise ValueError(f"Unknown repository: {repository_id}")

    async def get_current_repository(self) -> Optional[str]:
        """Get current repository ID."""
        return self._repository_id

    def _bindings_to_dicts(self, result: rdflib.query.Result) -> list[dict[str, Any]]:
        """Convert rdflib query result to list of dicts."""
        bindings = []
        for row in result:
            if isinstance(row, ResultRow):
                binding = {}
                for var in result.vars or []:
                    value = getattr(row, str(var), None)
                    if value is not None:
                        binding[str(var)] = self._term_to_dict(value)
                bindings.append(binding)
        return bindings

    def _term_to_dict(self, term: Any) -> dict[str, Any]:
        """Convert an rdflib term to a dict representation."""
        if isinstance(term, rdflib.URIRef):
            return {"type": "uri", "value": str(term)}
        elif isinstance(term, rdflib.Literal):
            result: dict[str, Any] = {"type": "literal", "value": str(term)}
            if term.language:
                result["xml:lang"] = term.language
            if term.datatype:
                result["datatype"] = str(term.datatype)
            return result
        elif isinstance(term, rdflib.BNode):
            return {"type": "bnode", "value": str(term)}
        else:
            return {"type": "unknown", "value": str(term)}

    async def sparql_select(
        self, query: str, repository_id: Optional[str] = None
    ) -> QueryResult:
        """Execute a SPARQL SELECT query."""
        graph = self._ensure_connected()
        result = graph.query(query)

        variables = [str(v) for v in (result.vars or [])]
        bindings = self._bindings_to_dicts(result)

        return QueryResult(
            type="select",
            bindings=bindings,
            variables=variables,
        )

    async def sparql_construct(
        self, query: str, repository_id: Optional[str] = None
    ) -> QueryResult:
        """Execute a SPARQL CONSTRUCT or DESCRIBE query."""
        graph = self._ensure_connected()
        result = graph.query(query)

        # Create a new graph from the result triples
        result_graph = Graph()
        for triple in result:
            result_graph.add(triple)

        # Serialize to Turtle
        turtle = result_graph.serialize(format="turtle")

        return QueryResult(
            type="construct",
            triples=turtle,
        )

    async def sparql_ask(
        self, query: str, repository_id: Optional[str] = None
    ) -> QueryResult:
        """Execute a SPARQL ASK query."""
        graph = self._ensure_connected()
        result = graph.query(query)

        return QueryResult(
            type="ask",
            boolean=bool(result.askAnswer),
        )

    async def get_namespaces(
        self, repository_id: Optional[str] = None
    ) -> list[NamespaceInfo]:
        """Get namespace prefix mappings."""
        graph = self._ensure_connected()
        namespaces = []
        for prefix, ns in graph.namespaces():
            namespaces.append(NamespaceInfo(prefix=prefix, namespace=str(ns)))
        return namespaces

    async def get_statistics(
        self, repository_id: Optional[str] = None
    ) -> StatisticsInfo:
        """Get repository statistics."""
        graph = self._ensure_connected()

        # Count total statements
        total_statements = len(graph)

        # Count distinct classes
        classes_query = """
        SELECT (COUNT(DISTINCT ?class) AS ?count) WHERE {
            { ?class a owl:Class }
            UNION { ?class a rdfs:Class }
            UNION { ?s a ?class }
        }
        """
        classes_result = graph.query(classes_query)
        total_classes = 0
        for row in classes_result:
            if hasattr(row, "count") and row.count is not None:
                total_classes = int(row.count)

        # Count distinct properties
        props_query = """
        SELECT (COUNT(DISTINCT ?prop) AS ?count) WHERE {
            { ?prop a rdf:Property }
            UNION { ?prop a owl:ObjectProperty }
            UNION { ?prop a owl:DatatypeProperty }
            UNION { ?s ?prop ?o }
        }
        """
        props_result = graph.query(props_query)
        total_properties = 0
        for row in props_result:
            if hasattr(row, "count") and row.count is not None:
                total_properties = int(row.count)

        # Count distinct subjects
        subjects = set()
        objects = set()
        for s, _, o in graph:
            subjects.add(s)
            objects.add(o)

        return StatisticsInfo(
            total_statements=total_statements,
            total_classes=total_classes,
            total_properties=total_properties,
            total_subjects=len(subjects),
            total_objects=len(objects),
        )

    async def load_file(self, file_path: str, format: Optional[str] = None) -> int:
        """Load RDF data from a file.

        Args:
            file_path: Path to the RDF file
            format: RDF format (auto-detected if not specified)

        Returns:
            Number of triples loaded
        """
        graph = self._ensure_connected()
        before = len(graph)
        graph.parse(file_path, format=format)
        return len(graph) - before

    async def load_data(self, data: str, format: str = "turtle") -> int:
        """Load RDF data from a string.

        Args:
            data: RDF data as string
            format: RDF format

        Returns:
            Number of triples loaded
        """
        graph = self._ensure_connected()
        before = len(graph)
        graph.parse(data=data, format=format)
        return len(graph) - before
