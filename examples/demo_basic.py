#!/usr/bin/env python3
"""
Basic Demo: RDF4J MCP Server with Remote Backend

This demo shows how to use the RDF4J MCP server programmatically
with a remote RDF4J server.

Prerequisites:
- A running RDF4J server at the configured URL
- A repository with sample data loaded
"""

import asyncio

from rdf4j_mcp.config import Settings
from rdf4j_mcp.server import RDF4JMCPServer


async def main():
    print("=" * 60)
    print("RDF4J MCP Server - Basic Demo")
    print("=" * 60)

    # Create and start the server with remote backend
    # Adjust the URL and repository to match your RDF4J server
    settings = Settings(
        rdf4j_server_url="http://localhost:8080/rdf4j-server",
        default_repository="test-repo",
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
            print(f"   {cls}: {label}")

        # Demo 4: Search Properties
        print("\n4. Properties in Ontology")
        print("-" * 40)
        props = await backend.search_properties(limit=15)
        for binding in props.bindings or []:
            prop = binding.get("property", {}).get("value", "")
            domain = binding.get("domain", {}).get("value", "").split("/")[-1]
            range_ = binding.get("range", {}).get("value", "").split("/")[-1]
            print(f"   {prop.split('/')[-1]}: {domain} -> {range_}")

        # Demo 5: SPARQL SELECT Query
        print("\n5. SPARQL SELECT: Find all classes")
        print("-" * 40)
        query = """
        SELECT DISTINCT ?class ?label
        WHERE {
            ?class a <http://www.w3.org/2002/07/owl#Class> .
            OPTIONAL { ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }
        }
        LIMIT 10
        """
        result = await backend.sparql_select(query)
        for binding in result.bindings or []:
            cls = binding.get("class", {}).get("value", "")
            label = binding.get("label", {}).get("value", "No label")
            print(f"   {cls.split('/')[-1]}: {label}")

        # Demo 6: SPARQL ASK Query
        print("\n6. SPARQL ASK: Are there any owl:Class definitions?")
        print("-" * 40)
        ask_query = """
        ASK {
            ?class a <http://www.w3.org/2002/07/owl#Class> .
        }
        """
        ask_result = await backend.sparql_ask(ask_query)
        print(f"   Result: {ask_result.boolean}")

        print("\n" + "=" * 60)
        print("Demo completed!")
        print("=" * 60)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
