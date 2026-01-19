#!/usr/bin/env python3
"""
SPARQL Query Demo: Common Query Patterns

This demo shows various SPARQL query patterns commonly used
when working with knowledge graphs.
"""

import asyncio
from pathlib import Path

from rdf4j_mcp.backends.local import LocalBackend
from rdf4j_mcp.config import BackendType, Settings
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
    sample_data = Path(__file__).parent / "sample_data.ttl"

    print("=" * 60)
    print("SPARQL Query Patterns Demo")
    print("=" * 60)

    settings = Settings(
        backend_type=BackendType.LOCAL,
        local_store_path=str(sample_data),
        local_store_format="turtle",
    )

    server = RDF4JMCPServer(settings)
    await server.start()

    try:
        backend = server._get_backend()

        # Query 1: Basic SELECT
        await run_query(
            backend,
            "1. BASIC SELECT - List all people",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?name ?email
            WHERE {
                ?person a ex:Person ;
                        ex:name ?name ;
                        ex:email ?email .
            }
            ORDER BY ?name
            """,
            lambda b: f"{b['name']['value']} <{b['email']['value']}>"
        )

        # Query 2: OPTIONAL clause
        await run_query(
            backend,
            "2. OPTIONAL - People with optional department",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?name ?deptName
            WHERE {
                ?person a ex:Person ;
                        ex:name ?name .
                OPTIONAL {
                    ?person ex:memberOf ?dept .
                    ?dept ex:name ?deptName .
                }
            }
            ORDER BY ?name
            """,
            lambda b: f"{b['name']['value']} - {b.get('deptName', {}).get('value', 'No department')}"
        )

        # Query 3: FILTER
        await run_query(
            backend,
            "3. FILTER - Projects with budget over $200,000",
            """
            PREFIX ex: <http://example.org/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?name ?budget
            WHERE {
                ?project a ex:Project ;
                         ex:name ?name ;
                         ex:budget ?budget .
                FILTER(?budget > 200000)
            }
            ORDER BY DESC(?budget)
            """,
            lambda b: f"{b['name']['value']}: ${float(b['budget']['value']):,.0f}"
        )

        # Query 4: Aggregation with GROUP BY
        await run_query(
            backend,
            "4. AGGREGATION - Team size per project",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?projectName (COUNT(?person) AS ?teamSize)
            WHERE {
                ?project a ex:Project ;
                         ex:name ?projectName .
                ?person ex:worksOn ?project .
            }
            GROUP BY ?project ?projectName
            ORDER BY DESC(?teamSize)
            """,
            lambda b: f"{b['projectName']['value']}: {b['teamSize']['value']} members"
        )

        # Query 5: HAVING clause
        await run_query(
            backend,
            "5. HAVING - Projects with 2+ team members",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?projectName (COUNT(?person) AS ?teamSize)
            WHERE {
                ?project a ex:Project ;
                         ex:name ?projectName .
                ?person ex:worksOn ?project .
            }
            GROUP BY ?project ?projectName
            HAVING (COUNT(?person) >= 2)
            ORDER BY DESC(?teamSize)
            """,
            lambda b: f"{b['projectName']['value']}: {b['teamSize']['value']} members"
        )

        # Query 6: Subquery
        await run_query(
            backend,
            "6. SUBQUERY - People working on the most expensive project",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?personName ?projectName ?budget
            WHERE {
                {
                    SELECT ?project (MAX(?b) AS ?maxBudget)
                    WHERE {
                        ?project a ex:Project ;
                                 ex:budget ?b .
                    }
                    GROUP BY ?project
                    ORDER BY DESC(?maxBudget)
                    LIMIT 1
                }
                ?project ex:name ?projectName ;
                         ex:budget ?budget .
                ?person ex:worksOn ?project ;
                        ex:name ?personName .
            }
            """,
            lambda b: f"{b['personName']['value']} on {b['projectName']['value']} (${float(b['budget']['value']):,.0f})"
        )

        # Query 7: UNION
        await run_query(
            backend,
            "7. UNION - All things with names (people and projects)",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?type ?name
            WHERE {
                {
                    ?entity a ex:Person ;
                            ex:name ?name .
                    BIND("Person" AS ?type)
                }
                UNION
                {
                    ?entity a ex:Project ;
                            ex:name ?name .
                    BIND("Project" AS ?type)
                }
            }
            ORDER BY ?type ?name
            """,
            lambda b: f"[{b['type']['value']}] {b['name']['value']}"
        )

        # Query 8: Property Path
        await run_query(
            backend,
            "8. PROPERTY PATH - People connected to organizations (via department)",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?personName ?orgName
            WHERE {
                ?person a ex:Person ;
                        ex:name ?personName ;
                        ex:memberOf/^ex:hasDepartment ?org .
                ?org ex:name ?orgName .
            }
            """,
            lambda b: f"{b['personName']['value']} -> {b['orgName']['value']}"
        )

        # Query 9: REGEX filter
        await run_query(
            backend,
            "9. REGEX - Find technologies containing 'Python' or 'SPARQL'",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?name
            WHERE {
                ?tech a ex:Technology ;
                      ex:name ?name .
                FILTER(REGEX(?name, "Python|SPARQL", "i"))
            }
            """,
            lambda b: b['name']['value']
        )

        # Query 10: Complex analysis
        await run_query(
            backend,
            "10. COMPLEX - Technology usage across active projects",
            """
            PREFIX ex: <http://example.org/>
            SELECT ?techName (COUNT(DISTINCT ?project) AS ?projectCount)
                   (GROUP_CONCAT(DISTINCT ?projectName; separator=", ") AS ?projects)
            WHERE {
                ?project a ex:Project ;
                         ex:name ?projectName ;
                         ex:status "active" ;
                         ex:uses ?tech .
                ?tech ex:name ?techName .
            }
            GROUP BY ?tech ?techName
            ORDER BY DESC(?projectCount)
            """,
            lambda b: f"{b['techName']['value']}: {b['projectCount']['value']} projects ({b['projects']['value']})"
        )

        # ASK Query Demo
        print("\n11. ASK QUERIES - Boolean questions")
        print("-" * 50)

        ask_queries = [
            ("Is there anyone named 'Alice Johnson'?",
             "ASK { ?p <http://example.org/name> 'Alice Johnson' }"),
            ("Are there any projects using Kubernetes?",
             "ASK { ?p <http://example.org/uses> <http://example.org/kubernetes> }"),
            ("Is there a completed project?",
             "ASK { ?p a <http://example.org/Project> ; <http://example.org/status> 'completed' }"),
        ]

        for question, query in ask_queries:
            result = await backend.sparql_ask(query)
            answer = "Yes" if result.boolean else "No"
            print(f"   Q: {question}")
            print(f"   A: {answer}\n")

        # CONSTRUCT Query Demo
        print("\n12. CONSTRUCT - Build a subgraph")
        print("-" * 50)
        construct_query = """
        PREFIX ex: <http://example.org/>
        CONSTRUCT {
            ?person ex:name ?name ;
                    ex:worksOn ?project .
            ?project ex:name ?projectName .
        }
        WHERE {
            ?person a ex:Person ;
                    ex:name ?name ;
                    ex:worksOn ?project .
            ?project ex:name ?projectName .
        }
        LIMIT 5
        """
        print(f"Query:\n{construct_query}")
        result = await backend.sparql_construct(construct_query)
        print("\nResult (Turtle):")
        if result.triples:
            # Show first 500 chars
            print(result.triples[:800])

        print("\n" + "=" * 60)
        print("Query patterns demo completed!")
        print("=" * 60)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
