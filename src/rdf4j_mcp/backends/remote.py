"""Remote RDF backend using RDF4J Python client."""

from typing import Any

import pyoxigraph as og
from rdf4j_python import AsyncRdf4j, AsyncRdf4JRepository

from .base import (
    Backend,
    NamespaceInfo,
    QueryResult,
    RepositoryInfo,
    StatisticsInfo,
)


class RemoteBackend(Backend):
    """Remote RDF backend using RDF4J HTTP API."""

    def __init__(
        self,
        server_url: str,
        default_repository: str | None = None,
    ):
        """Initialize remote backend.

        Args:
            server_url: URL of the RDF4J server
            default_repository: Default repository ID to use
        """
        self._server_url = server_url.rstrip("/")
        self._default_repository = default_repository
        self._current_repository: str | None = default_repository
        self._client: AsyncRdf4j | None = None
        self._repo: AsyncRdf4JRepository | None = None

    async def connect(self) -> None:
        """Connect to the RDF4J server."""
        self._client = AsyncRdf4j(self._server_url)
        await self._client.__aenter__()

        # Connect to default repository if specified
        if self._default_repository:
            self._repo = await self._client.get_repository(self._default_repository)
            self._current_repository = self._default_repository

    async def close(self) -> None:
        """Close connection to the server."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._repo = None

    def _ensure_connected(self) -> AsyncRdf4j:
        """Ensure client is connected."""
        if self._client is None:
            raise RuntimeError("Backend not connected. Call connect() first.")
        return self._client

    async def _get_repository(self, repository_id: str | None = None) -> AsyncRdf4JRepository:
        """Get repository instance."""
        client = self._ensure_connected()
        repo_id = repository_id or self._current_repository

        if repo_id is None:
            raise ValueError("No repository specified and no default repository set")

        if self._repo is not None and self._current_repository == repo_id:
            return self._repo

        return await client.get_repository(repo_id)

    async def list_repositories(self) -> list[RepositoryInfo]:
        """List available repositories."""
        client = self._ensure_connected()
        repos = await client.list_repositories()

        return [
            RepositoryInfo(
                id=repo.id,
                title=repo.title,
                uri=repo.uri,
                readable=repo.readable,
                writable=repo.writable,
            )
            for repo in repos
        ]

    async def select_repository(self, repository_id: str) -> None:
        """Select a repository to work with."""
        client = self._ensure_connected()
        self._repo = await client.get_repository(repository_id)
        self._current_repository = repository_id

    async def get_current_repository(self) -> str | None:
        """Get the currently selected repository ID."""
        return self._current_repository

    def _solution_to_dict(self, solution: og.QuerySolution) -> dict[str, Any]:
        """Convert a pyoxigraph QuerySolution to a dict."""
        result = {}
        for i, var in enumerate(solution):
            if var is not None:
                result[f"var_{i}"] = self._term_to_dict(var)
        return result

    def _term_to_dict(self, term: Any) -> dict[str, Any]:
        """Convert a pyoxigraph term to a dict."""
        if isinstance(term, og.NamedNode):
            return {"type": "uri", "value": term.value}
        elif isinstance(term, og.Literal):
            result: dict[str, Any] = {"type": "literal", "value": term.value}
            if term.language:
                result["xml:lang"] = term.language
            if term.datatype:
                result["datatype"] = term.datatype.value
            return result
        elif isinstance(term, og.BlankNode):
            return {"type": "bnode", "value": term.value}
        else:
            return {"type": "unknown", "value": str(term)}

    def _query_solutions_to_bindings(
        self, solutions: og.QuerySolutions
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Convert QuerySolutions to bindings list and variable names."""
        variables = list(solutions.variables)
        var_names = [str(v.value) for v in variables]

        bindings = []
        for solution in solutions:
            binding = {}
            for i, var_name in enumerate(var_names):
                value = solution[i]
                if value is not None:
                    binding[var_name] = self._term_to_dict(value)
            bindings.append(binding)

        return bindings, var_names

    async def sparql_select(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL SELECT query."""
        repo = await self._get_repository(repository_id)
        result = await repo.query(query)

        if isinstance(result, og.QuerySolutions):
            bindings, variables = self._query_solutions_to_bindings(result)
            return QueryResult(
                type="select",
                bindings=bindings,
                variables=variables,
            )
        else:
            return QueryResult(
                type="select",
                bindings=[],
                variables=[],
            )

    async def sparql_construct(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL CONSTRUCT or DESCRIBE query."""
        repo = await self._get_repository(repository_id)
        result = await repo.query(query)

        if isinstance(result, og.QueryTriples):
            # Serialize triples to Turtle format
            triples_list = list(result)
            turtle_lines = []
            for triple in triples_list:
                s = self._format_term(triple.subject)
                p = self._format_term(triple.predicate)
                o = self._format_term(triple.object)
                turtle_lines.append(f"{s} {p} {o} .")

            return QueryResult(
                type="construct",
                triples="\n".join(turtle_lines),
            )
        else:
            return QueryResult(
                type="construct",
                triples="",
            )

    def _format_term(self, term: Any) -> str:
        """Format a term for Turtle output."""
        if isinstance(term, og.NamedNode):
            return f"<{term.value}>"
        elif isinstance(term, og.Literal):
            escaped = term.value.replace("\\", "\\\\").replace('"', '\\"')
            if term.language:
                return f'"{escaped}"@{term.language}'
            elif term.datatype and term.datatype.value != "http://www.w3.org/2001/XMLSchema#string":
                return f'"{escaped}"^^<{term.datatype.value}>'
            else:
                return f'"{escaped}"'
        elif isinstance(term, og.BlankNode):
            return f"_:{term.value}"
        else:
            return str(term)

    async def sparql_ask(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL ASK query."""
        repo = await self._get_repository(repository_id)
        result = await repo.query(query)

        if isinstance(result, bool):
            return QueryResult(
                type="ask",
                boolean=result,
            )
        else:
            return QueryResult(
                type="ask",
                boolean=False,
            )

    async def get_namespaces(self, repository_id: str | None = None) -> list[NamespaceInfo]:
        """Get namespace prefix mappings."""
        repo = await self._get_repository(repository_id)
        namespaces = await repo.get_namespaces()

        return [NamespaceInfo(prefix=ns.prefix, namespace=str(ns.namespace)) for ns in namespaces]

    async def get_statistics(self, repository_id: str | None = None) -> StatisticsInfo:
        """Get repository statistics."""
        repo = await self._get_repository(repository_id)

        # Get total statement count
        total_statements = await repo.size()

        # Count classes
        classes_query = """
        SELECT (COUNT(DISTINCT ?class) AS ?count) WHERE {
            { ?class a <http://www.w3.org/2002/07/owl#Class> }
            UNION { ?class a <http://www.w3.org/2000/01/rdf-schema#Class> }
            UNION { ?s a ?class }
        }
        """
        classes_result = await repo.query(classes_query)
        total_classes = 0
        if isinstance(classes_result, og.QuerySolutions):
            for solution in classes_result:
                if solution[0] is not None:
                    total_classes = int(solution[0].value)  # type: ignore

        # Count properties
        props_query = """
        SELECT (COUNT(DISTINCT ?prop) AS ?count) WHERE {
            { ?prop a <http://www.w3.org/1999/02/22-rdf-syntax-ns#Property> }
            UNION { ?prop a <http://www.w3.org/2002/07/owl#ObjectProperty> }
            UNION { ?prop a <http://www.w3.org/2002/07/owl#DatatypeProperty> }
            UNION { ?s ?prop ?o }
        }
        """
        props_result = await repo.query(props_query)
        total_properties = 0
        if isinstance(props_result, og.QuerySolutions):
            for solution in props_result:
                if solution[0] is not None:
                    total_properties = int(solution[0].value)  # type: ignore

        # Count subjects
        subjects_query = "SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { ?s ?p ?o }"
        subjects_result = await repo.query(subjects_query)
        total_subjects = 0
        if isinstance(subjects_result, og.QuerySolutions):
            for solution in subjects_result:
                if solution[0] is not None:
                    total_subjects = int(solution[0].value)  # type: ignore

        # Count objects
        objects_query = "SELECT (COUNT(DISTINCT ?o) AS ?count) WHERE { ?s ?p ?o }"
        objects_result = await repo.query(objects_query)
        total_objects = 0
        if isinstance(objects_result, og.QuerySolutions):
            for solution in objects_result:
                if solution[0] is not None:
                    total_objects = int(solution[0].value)  # type: ignore

        return StatisticsInfo(
            total_statements=total_statements,
            total_classes=total_classes,
            total_properties=total_properties,
            total_subjects=total_subjects,
            total_objects=total_objects,
        )
