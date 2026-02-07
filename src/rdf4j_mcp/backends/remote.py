"""Remote RDF backend using RDF4J Python client."""

import asyncio
import logging
import time
from typing import Any

import httpx
import pyoxigraph as og
import rdflib
from rdf4j_python import AsyncRdf4j, AsyncRdf4JRepository
from rdf4j_python.exception import (
    NetworkError,
    QueryError,
    RepositoryNotFoundException,
)
from rdf4j_python.utils.const import Rdf4jContentType

from rdf4j_mcp.exceptions import (
    QueryTimeoutError,
    RDF4JConnectionError,
    RepositoryNotFoundError,
    SPARQLSyntaxError,
)

from .base import (
    Backend,
    NamespaceInfo,
    QueryResult,
    RepositoryInfo,
    StatisticsInfo,
)

logger = logging.getLogger(__name__)

_RETRY_BACKOFF = (0.5, 1.0, 2.0)


class RemoteBackend(Backend):
    """Remote RDF backend using RDF4J HTTP API."""

    def __init__(
        self,
        server_url: str,
        default_repository: str | None = None,
        cache_ttl: int = 300,
        query_timeout: int = 30,
    ):
        """Initialize remote backend.

        Args:
            server_url: URL of the RDF4J server
            default_repository: Default repository ID to use
            cache_ttl: TTL in seconds for cached results
            query_timeout: Query timeout in seconds
        """
        self._server_url = server_url.rstrip("/")
        self._default_repository = default_repository
        self._current_repository: str | None = default_repository
        self._client: AsyncRdf4j | None = None
        self._repo: AsyncRdf4JRepository | None = None
        self._cache_ttl = cache_ttl
        self._query_timeout = query_timeout
        self._cache: dict[str, tuple[Any, float]] = {}

    async def connect(self) -> None:
        """Connect to the RDF4J server."""
        try:
            self._client = AsyncRdf4j(self._server_url)
            await self._client.__aenter__()

            # Connect to default repository if specified
            if self._default_repository:
                self._repo = await self._client.get_repository(self._default_repository)
                self._current_repository = self._default_repository
        except (NetworkError, httpx.ConnectError, OSError) as exc:
            raise RDF4JConnectionError(
                f"Failed to connect to RDF4J server at {self._server_url}: {exc}"
            ) from exc

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

    def _cache_get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        entry = self._cache.get(key)
        if entry is not None and time.monotonic() < entry[1]:
            return entry[0]
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        """Store a value in the cache with the configured TTL."""
        self._cache[key] = (value, time.monotonic() + self._cache_ttl)

    async def _execute_with_retry(
        self, repo: AsyncRdf4JRepository, query: str, *, is_update: bool = False
    ) -> Any:
        """Execute a query/update with retry on transient errors and timeout wrapping."""
        last_exc: Exception | None = None
        for attempt, backoff in enumerate(_RETRY_BACKOFF):
            try:
                if is_update:
                    return await asyncio.wait_for(
                        repo.update(query, Rdf4jContentType.SPARQL_UPDATE),
                        timeout=self._query_timeout,
                    )
                else:
                    return await asyncio.wait_for(repo.query(query), timeout=self._query_timeout)
            except TimeoutError as exc:
                raise QueryTimeoutError(f"Query timed out after {self._query_timeout}s") from exc
            except httpx.TimeoutException as exc:
                raise QueryTimeoutError(f"Query timed out after {self._query_timeout}s") from exc
            except QueryError as exc:
                raise SPARQLSyntaxError(str(exc)) from exc
            except (NetworkError, httpx.HTTPStatusError) as exc:
                # Retry on 5xx server errors
                is_server_error = (
                    isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500
                ) or isinstance(exc, NetworkError)
                if is_server_error and attempt < len(_RETRY_BACKOFF) - 1:
                    last_exc = exc
                    logger.warning(
                        "Transient error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        len(_RETRY_BACKOFF),
                        backoff,
                        exc,
                    )
                    await asyncio.sleep(backoff)
                    continue
                raise RDF4JConnectionError(
                    f"Request failed after {attempt + 1} attempt(s): {exc}"
                ) from exc
        # Should not reach here, but just in case
        raise RDF4JConnectionError(f"Request failed: {last_exc}") from last_exc

    async def _get_repository(self, repository_id: str | None = None) -> AsyncRdf4JRepository:
        """Get repository instance."""
        client = self._ensure_connected()
        repo_id = repository_id or self._current_repository

        if repo_id is None:
            raise RepositoryNotFoundError("No repository specified and no default repository set")

        if self._repo is not None and self._current_repository == repo_id:
            return self._repo

        try:
            return await client.get_repository(repo_id)
        except RepositoryNotFoundException as exc:
            raise RepositoryNotFoundError(f"Repository '{repo_id}' not found") from exc

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
        result = await self._execute_with_retry(repo, query)

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

    def _oxigraph_to_rdflib(self, term: Any) -> rdflib.term.Node:
        """Convert a pyoxigraph term to an rdflib term."""
        if isinstance(term, og.NamedNode):
            return rdflib.URIRef(term.value)
        elif isinstance(term, og.BlankNode):
            return rdflib.BNode(term.value)
        elif isinstance(term, og.Literal):
            if term.language:
                return rdflib.Literal(term.value, lang=term.language)
            elif term.datatype:
                return rdflib.Literal(term.value, datatype=rdflib.URIRef(term.datatype.value))
            else:
                return rdflib.Literal(term.value)
        return rdflib.Literal(str(term))

    async def sparql_construct(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL CONSTRUCT or DESCRIBE query."""
        repo = await self._get_repository(repository_id)
        result = await self._execute_with_retry(repo, query)

        if isinstance(result, og.QueryTriples):
            triples_list = list(result)
            if not triples_list:
                return QueryResult(type="construct", triples="")

            # Build an rdflib Graph and bind namespace prefixes
            g = rdflib.Graph()
            namespaces = await self.get_namespaces(repository_id)
            for ns in namespaces:
                g.bind(ns.prefix, rdflib.Namespace(ns.namespace))

            for triple in triples_list:
                s = self._oxigraph_to_rdflib(triple.subject)
                p = self._oxigraph_to_rdflib(triple.predicate)
                o = self._oxigraph_to_rdflib(triple.object)
                g.add((s, p, o))

            turtle = g.serialize(format="turtle")
            return QueryResult(type="construct", triples=turtle.strip())
        else:
            return QueryResult(type="construct", triples="")

    async def sparql_ask(self, query: str, repository_id: str | None = None) -> QueryResult:
        """Execute a SPARQL ASK query."""
        repo = await self._get_repository(repository_id)
        result = await self._execute_with_retry(repo, query)

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
        """Get namespace prefix mappings (cached)."""
        repo_id = repository_id or self._current_repository
        cache_key = f"ns:{repo_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        repo = await self._get_repository(repository_id)
        namespaces = await repo.get_namespaces()
        result = [NamespaceInfo(prefix=ns.prefix, namespace=str(ns.namespace)) for ns in namespaces]
        self._cache_set(cache_key, result)
        return result

    async def get_statistics(self, repository_id: str | None = None) -> StatisticsInfo:
        """Get repository statistics (cached)."""
        repo_id = repository_id or self._current_repository
        cache_key = f"stats:{repo_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        repo = await self._get_repository(repository_id)

        # Get total statement count
        total_statements = await repo.size()

        # Combined subjects + objects count (single scan of all triples)
        subjects_objects_query = """
        SELECT (COUNT(DISTINCT ?s) AS ?subjects) (COUNT(DISTINCT ?o) AS ?objects)
        WHERE { ?s ?p ?o }
        """
        so_result = await self._execute_with_retry(repo, subjects_objects_query)
        total_subjects = 0
        total_objects = 0
        if isinstance(so_result, og.QuerySolutions):
            for solution in so_result:
                if solution[0] is not None:
                    total_subjects = int(solution[0].value)
                if solution[1] is not None:
                    total_objects = int(solution[1].value)

        # Combined classes + properties count using subqueries
        classes_props_query = """
        SELECT ?classes ?properties WHERE {
            {
                SELECT (COUNT(DISTINCT ?class) AS ?classes) WHERE {
                    { ?class a <http://www.w3.org/2002/07/owl#Class> }
                    UNION { ?class a <http://www.w3.org/2000/01/rdf-schema#Class> }
                    UNION { ?s a ?class }
                }
            }
            {
                SELECT (COUNT(DISTINCT ?prop) AS ?properties) WHERE {
                    { ?prop a <http://www.w3.org/1999/02/22-rdf-syntax-ns#Property> }
                    UNION { ?prop a <http://www.w3.org/2002/07/owl#ObjectProperty> }
                    UNION { ?prop a <http://www.w3.org/2002/07/owl#DatatypeProperty> }
                    UNION { ?s ?prop ?o }
                }
            }
        }
        """
        cp_result = await self._execute_with_retry(repo, classes_props_query)
        total_classes = 0
        total_properties = 0
        if isinstance(cp_result, og.QuerySolutions):
            for solution in cp_result:
                if solution[0] is not None:
                    total_classes = int(solution[0].value)
                if solution[1] is not None:
                    total_properties = int(solution[1].value)

        result = StatisticsInfo(
            total_statements=total_statements,
            total_classes=total_classes,
            total_properties=total_properties,
            total_subjects=total_subjects,
            total_objects=total_objects,
        )
        self._cache_set(cache_key, result)
        return result

    async def sparql_update(self, query: str, repository_id: str | None = None) -> str:
        """Execute a SPARQL UPDATE query."""
        repo = await self._get_repository(repository_id)
        await self._execute_with_retry(repo, query, is_update=True)
        return "Update executed successfully"
