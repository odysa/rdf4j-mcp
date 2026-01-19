"""Abstract base class for RDF backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class RepositoryInfo:
    """Information about an RDF repository."""

    id: str
    title: str
    uri: str | None = None
    readable: bool = True
    writable: bool = True


@dataclass
class NamespaceInfo:
    """Namespace prefix mapping."""

    prefix: str
    namespace: str


@dataclass
class QueryResult:
    """Result of a SPARQL query."""

    type: str  # "select", "construct", "ask", "describe"
    bindings: list[dict[str, Any]] | None = None  # For SELECT queries
    triples: str | None = None  # For CONSTRUCT/DESCRIBE (as Turtle)
    boolean: bool | None = None  # For ASK queries
    variables: list[str] | None = None  # Variable names for SELECT


@dataclass
class StatisticsInfo:
    """Repository statistics."""

    total_statements: int
    total_classes: int
    total_properties: int
    total_subjects: int
    total_objects: int


class Backend(ABC):
    """Abstract base class for RDF storage backends."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the backend."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to the backend."""
        pass

    @abstractmethod
    async def list_repositories(self) -> list[RepositoryInfo]:
        """List available repositories."""
        pass

    @abstractmethod
    async def select_repository(self, repository_id: str) -> None:
        """Select a repository to work with."""
        pass

    @abstractmethod
    async def get_current_repository(self) -> str | None:
        """Get the currently selected repository ID."""
        pass

    @abstractmethod
    async def sparql_select(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL SELECT query."""
        pass

    @abstractmethod
    async def sparql_construct(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL CONSTRUCT or DESCRIBE query."""
        pass

    @abstractmethod
    async def sparql_ask(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL ASK query."""
        pass

    @abstractmethod
    async def get_namespaces(self, repository_id: str | None = None) -> list[NamespaceInfo]:
        """Get namespace prefix mappings."""
        pass

    @abstractmethod
    async def get_statistics(self, repository_id: str | None = None) -> StatisticsInfo:
        """Get repository statistics."""
        pass

    async def describe_resource(self, iri: str, repository_id: str | None = None) -> QueryResult:
        """Get all triples about a resource."""
        query = f"DESCRIBE <{iri}>"
        return await self.sparql_construct(query, repository_id)

    async def search_classes(
        self,
        pattern: str | None = None,
        limit: int = 100,
        repository_id: str | None = None,
    ) -> QueryResult:
        """Search for classes in the ontology."""
        filter_clause = ""
        if pattern:
            filter_clause = f'FILTER(REGEX(STR(?class), "{pattern}", "i"))'

        query = f"""
        SELECT DISTINCT ?class ?label ?comment
        WHERE {{
            {{ ?class a owl:Class }}
            UNION
            {{ ?class a rdfs:Class }}
            UNION
            {{ ?s a ?class }}
            OPTIONAL {{ ?class rdfs:label ?label }}
            OPTIONAL {{ ?class rdfs:comment ?comment }}
            {filter_clause}
        }}
        ORDER BY ?class
        LIMIT {limit}
        """
        return await self.sparql_select(query, repository_id)

    async def search_properties(
        self,
        pattern: str | None = None,
        domain: str | None = None,
        range_: str | None = None,
        limit: int = 100,
        repository_id: str | None = None,
    ) -> QueryResult:
        """Search for properties in the ontology."""
        filters = []
        if pattern:
            filters.append(f'REGEX(STR(?property), "{pattern}", "i")')
        if domain:
            filters.append(f"?domain = <{domain}>")
        if range_:
            filters.append(f"?range = <{range_}>")

        filter_clause = ""
        if filters:
            filter_clause = "FILTER(" + " && ".join(filters) + ")"

        query = f"""
        SELECT DISTINCT ?property ?label ?domain ?range
        WHERE {{
            {{ ?property a rdf:Property }}
            UNION
            {{ ?property a owl:ObjectProperty }}
            UNION
            {{ ?property a owl:DatatypeProperty }}
            UNION
            {{ ?s ?property ?o }}
            OPTIONAL {{ ?property rdfs:label ?label }}
            OPTIONAL {{ ?property rdfs:domain ?domain }}
            OPTIONAL {{ ?property rdfs:range ?range }}
            {filter_clause}
        }}
        ORDER BY ?property
        LIMIT {limit}
        """
        return await self.sparql_select(query, repository_id)

    async def find_instances(
        self,
        class_iri: str,
        limit: int = 100,
        repository_id: str | None = None,
    ) -> QueryResult:
        """Find instances of a class."""
        query = f"""
        SELECT DISTINCT ?instance ?label
        WHERE {{
            ?instance a <{class_iri}> .
            OPTIONAL {{ ?instance rdfs:label ?label }}
        }}
        ORDER BY ?instance
        LIMIT {limit}
        """
        return await self.sparql_select(query, repository_id)

    async def get_schema_summary(self, repository_id: str | None = None) -> dict[str, Any]:
        """Get a summary of the ontology schema."""
        classes_result = await self.search_classes(limit=50, repository_id=repository_id)
        properties_result = await self.search_properties(limit=50, repository_id=repository_id)
        stats = await self.get_statistics(repository_id)
        namespaces = await self.get_namespaces(repository_id)

        return {
            "statistics": {
                "total_statements": stats.total_statements,
                "total_classes": stats.total_classes,
                "total_properties": stats.total_properties,
            },
            "classes": classes_result.bindings or [],
            "properties": properties_result.bindings or [],
            "namespaces": [{"prefix": ns.prefix, "namespace": ns.namespace} for ns in namespaces],
        }

    async def __aenter__(self) -> "Backend":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
