#!/usr/bin/env python3
"""
Exploration Demo: Knowledge Graph Discovery

This demo shows how to use the exploration features to discover
and understand a knowledge graph schema.

Prerequisites:
- A running RDF4J server at the configured URL
- A repository with sample data loaded
"""

import asyncio

from rdf4j_mcp.config import Settings
from rdf4j_mcp.server import RDF4JMCPServer


async def main():
    print("=" * 60)
    print("Knowledge Graph Exploration Demo")
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

        # Step 1: Get Schema Summary
        print("\n1. SCHEMA OVERVIEW")
        print("=" * 60)
        summary = await backend.get_schema_summary()

        print("\nStatistics:")
        for key, value in summary["statistics"].items():
            print(f"   {key}: {value}")

        print("\nNamespaces Used:")
        for ns in summary["namespaces"][:6]:
            print(f"   {ns['prefix']}: <{ns['namespace']}>")

        # Step 2: Discover Classes
        print("\n\n2. DISCOVERING CLASSES")
        print("=" * 60)

        classes = await backend.search_classes()

        print(f"\nFound {len(classes.bindings or [])} classes:")
        for cls in (classes.bindings or [])[:10]:
            iri = cls.get("class", {}).get("value", "")
            label = cls.get("label", {}).get("value", "No label")
            comment = cls.get("comment", {}).get("value", "")
            print(f"\n   {iri.split('/')[-1]}")
            print(f"   Label: {label}")
            if comment:
                print(f"   Description: {comment}")

        # Step 3: Explore Properties
        print("\n\n3. DISCOVERING PROPERTIES")
        print("=" * 60)

        props = await backend.search_properties(limit=10)

        for prop in props.bindings or []:
            prop_iri = prop.get("property", {}).get("value", "")
            prop_name = prop_iri.split("/")[-1]
            domain = prop.get("domain", {}).get("value", "").split("/")[-1] or "Any"
            range_val = prop.get("range", {}).get("value", "").split("/")[-1] or "Any"
            print(f"   {prop_name}: {domain} -> {range_val}")

        # Step 4: Repository List
        print("\n\n4. AVAILABLE REPOSITORIES")
        print("=" * 60)

        repos = await backend.list_repositories()
        for repo in repos:
            readable = "R" if repo.readable else "-"
            writable = "W" if repo.writable else "-"
            print(f"   [{readable}{writable}] {repo.id}: {repo.title}")

        print("\n" + "=" * 60)
        print("Exploration completed!")
        print("=" * 60)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
