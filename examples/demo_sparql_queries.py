#!/usr/bin/env python3
"""
SPARQL Query Demo: Common Query Patterns

This demo shows various SPARQL query patterns commonly used
when working with knowledge graphs.

Prerequisites:
- A running RDF4J server at the configured URL
- A repository with sample data loaded
"""

import asyncio

from rdf4j_mcp.config import Settings
from rdf4j_mcp.server import RDF4JMCPServer


async def run_query(backend, title, query, format_func=None):
    """Helper to run and display a query."""
    print(f"\n{title}")
    print("-" * 50)
    print(f"Query:\n{query.strip()}\n")

    result = await backend.sparql_select(query)

    print("Results:")
    if not result.bindings:
        print("   (no results)")
        return

    for binding in result.bindings or []:
        if format_func:
            print(f"   {format_func(binding)}")
        else:
            parts = []
            for var, val in binding.items():
                v = val.get("value", "").split("/")[-1]
                parts.append(f"{var}={v}")
            print(f"   {', '.join(parts)}")


async def main():
    print("=" * 60)
    print("SPARQL Query Patterns Demo")
    print("=" * 60)

    # Adjust the URL and repository to match your RDF4J server
    settings = Settings(
        rdf4j_server_url="http://localhost:8080/rdf4j-server",
        default_repository="test-repo",
    )

    server = RDF4JMCPServer(settings)
    await server.start()

    try:
        backend = server._get_backend()

        # Query 1: Basic SELECT - Find all classes
        await run_query(
            backend,
            "1. BASIC SELECT - List all classes",
            """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?class ?label
            WHERE {
                ?class a owl:Class .
                OPTIONAL { ?class rdfs:label ?label }
            }
            LIMIT 10
            """,
            lambda b: (
                f"{b.get('class', {}).get('value', '').split('/')[-1]}: "
                f"{b.get('label', {}).get('value', 'No label')}"
            ),
        )

        # Query 2: OPTIONAL clause
        await run_query(
            backend,
            "2. OPTIONAL - Properties with optional domain/range",
            """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT ?prop ?domain ?range
            WHERE {
                ?prop a rdf:Property .
                OPTIONAL { ?prop rdfs:domain ?domain }
                OPTIONAL { ?prop rdfs:range ?range }
            }
            LIMIT 10
            """,
            lambda b: (
                f"{b.get('prop', {}).get('value', '').split('/')[-1]} - "
                f"domain: {b.get('domain', {}).get('value', 'Any').split('/')[-1]}, "
                f"range: {b.get('range', {}).get('value', 'Any').split('/')[-1]}"
            ),
        )

        # Query 3: Aggregation with COUNT
        await run_query(
            backend,
            "3. AGGREGATION - Count instances per class",
            """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?class (COUNT(?instance) AS ?count)
            WHERE {
                ?instance a ?class .
            }
            GROUP BY ?class
            ORDER BY DESC(?count)
            LIMIT 10
            """,
            lambda b: (
                f"{b.get('class', {}).get('value', '').split('/')[-1]}: "
                f"{b.get('count', {}).get('value', '0')} instances"
            ),
        )

        # Query 4: FILTER
        await run_query(
            backend,
            "4. FILTER - Resources with specific patterns",
            """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?resource ?label
            WHERE {
                ?resource rdfs:label ?label .
                FILTER(STRLEN(?label) > 5)
            }
            LIMIT 10
            """,
        )

        # Query 5: UNION
        await run_query(
            backend,
            "5. UNION - Find all classes and properties",
            """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?entity ?type
            WHERE {
                {
                    ?entity a owl:Class .
                    BIND("Class" AS ?type)
                }
                UNION
                {
                    ?entity a rdf:Property .
                    BIND("Property" AS ?type)
                }
            }
            LIMIT 10
            """,
            lambda b: (
                f"[{b.get('type', {}).get('value', '')}] "
                f"{b.get('entity', {}).get('value', '').split('/')[-1]}"
            ),
        )

        # ASK Query Demo
        print("\n6. ASK QUERIES - Boolean questions")
        print("-" * 50)

        ask_queries = [
            (
                "Are there any OWL classes defined?",
                "PREFIX owl: <http://www.w3.org/2002/07/owl#> ASK { ?c a owl:Class }",
            ),
            (
                "Are there any RDF properties defined?",
                (
                    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> "
                    "ASK { ?p a rdf:Property }"
                ),
            ),
        ]

        for question, query in ask_queries:
            result = await backend.sparql_ask(query)
            answer = "Yes" if result.boolean else "No"
            print(f"   Q: {question}")
            print(f"   A: {answer}\n")

        # CONSTRUCT Query Demo
        print("\n7. CONSTRUCT - Build a subgraph")
        print("-" * 50)
        construct_query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        CONSTRUCT {
            ?class a owl:Class ;
                   rdfs:label ?label .
        }
        WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
        }
        LIMIT 5
        """
        print(f"Query:\n{construct_query}")
        result = await backend.sparql_construct(construct_query)
        print("\nResult (Turtle):")
        if result.triples:
            print(result.triples[:800])
        else:
            print("   (no results)")

        print("\n" + "=" * 60)
        print("Query patterns demo completed!")
        print("=" * 60)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
