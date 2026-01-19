#!/usr/bin/env python3
"""
Basic Demo: RDF4J MCP Server with Local Backend

This demo shows how to use the RDF4J MCP server programmatically
with a local rdflib backend.
"""

import asyncio
from pathlib import Path

from rdf4j_mcp.config import BackendType, Settings
from rdf4j_mcp.server import RDF4JMCPServer


async def main():
    # Get path to sample data
    sample_data = Path(__file__).parent / "sample_data.ttl"

    print("=" * 60)
    print("RDF4J MCP Server - Basic Demo")
    print("=" * 60)

    # Create and start the server with local backend
    settings = Settings(
        backend_type=BackendType.LOCAL,
        local_store_path=str(sample_data),
        local_store_format="turtle",
    )

    server = RDF4JMCPServer(settings)
    await server.start()

    try:
        backend = server._get_backend()

        # Demo 1: Get Statistics
        print("\n1. Repository Statistics")
        print("-" * 40)
        stats = await backend.get_statistics()
        print(f"   Total statements: {stats.total_statements}")
        print(f"   Total classes: {stats.total_classes}")
        print(f"   Total properties: {stats.total_properties}")
        print(f"   Total subjects: {stats.total_subjects}")
        print(f"   Total objects: {stats.total_objects}")

        # Demo 2: List Namespaces
        print("\n2. Namespaces")
        print("-" * 40)
        namespaces = await backend.get_namespaces()
        for ns in namespaces[:8]:
            print(f"   {ns.prefix}: <{ns.namespace}>")

        # Demo 3: Search Classes
        print("\n3. Classes in Ontology")
        print("-" * 40)
        classes = await backend.search_classes(limit=10)
        for binding in classes.bindings or []:
            cls = binding.get("class", {}).get("value", "")
            label = binding.get("label", {}).get("value", "")
            if "example.org" in cls:
                print(f"   {cls.split('/')[-1]}: {label}")

        # Demo 4: Search Properties
        print("\n4. Properties in Ontology")
        print("-" * 40)
        props = await backend.search_properties(limit=15)
        for binding in props.bindings or []:
            prop = binding.get("property", {}).get("value", "")
            if "example.org" in prop:
                domain = binding.get("domain", {}).get("value", "").split("/")[-1]
                range_ = binding.get("range", {}).get("value", "").split("/")[-1]
                print(f"   {prop.split('/')[-1]}: {domain} -> {range_}")

        # Demo 5: SPARQL SELECT Query
        print("\n5. SPARQL SELECT: Find all people and their projects")
        print("-" * 40)
        query = """
        PREFIX ex: <http://example.org/>
        SELECT ?name ?project ?projectName
        WHERE {
            ?person a ex:Person ;
                    ex:name ?name ;
                    ex:worksOn ?project .
            ?project ex:name ?projectName .
        }
        ORDER BY ?name
        """
        result = await backend.sparql_select(query)
        for binding in result.bindings or []:
            name = binding.get("name", {}).get("value", "")
            project = binding.get("projectName", {}).get("value", "")
            print(f"   {name} -> {project}")

        # Demo 6: Find Instances
        print("\n6. Find Instances of ex:Project")
        print("-" * 40)
        instances = await backend.find_instances("http://example.org/Project")
        for binding in instances.bindings or []:
            inst = binding.get("instance", {}).get("value", "").split("/")[-1]
            label = binding.get("label", {}).get("value", "")
            print(f"   {inst}: {label}")

        # Demo 7: Describe Resource
        print("\n7. Describe Resource: ex:alice")
        print("-" * 40)
        description = await backend.describe_resource("http://example.org/alice")
        print(description.triples[:500] if description.triples else "No triples found")

        # Demo 8: SPARQL ASK Query
        print("\n\n8. SPARQL ASK: Does anyone work on KG Platform?")
        print("-" * 40)
        ask_query = """
        PREFIX ex: <http://example.org/>
        ASK {
            ?person ex:worksOn ex:kg-platform .
        }
        """
        ask_result = await backend.sparql_ask(ask_query)
        print(f"   Result: {ask_result.boolean}")

        # Demo 9: Complex Query - Project Team Analysis
        print("\n9. Complex Query: Project team sizes and budgets")
        print("-" * 40)
        complex_query = """
        PREFIX ex: <http://example.org/>
        SELECT ?projectName ?budget (COUNT(?person) as ?teamSize)
        WHERE {
            ?project a ex:Project ;
                     ex:name ?projectName ;
                     ex:budget ?budget .
            ?person ex:worksOn ?project .
        }
        GROUP BY ?project ?projectName ?budget
        ORDER BY DESC(?budget)
        """
        complex_result = await backend.sparql_select(complex_query)
        for binding in complex_result.bindings or []:
            name = binding.get("projectName", {}).get("value", "")
            budget = binding.get("budget", {}).get("value", "")
            size = binding.get("teamSize", {}).get("value", "")
            print(f"   {name}: ${float(budget):,.0f} budget, {size} team members")

        print("\n" + "=" * 60)
        print("Demo completed!")
        print("=" * 60)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
