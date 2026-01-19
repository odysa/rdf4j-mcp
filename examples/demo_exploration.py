#!/usr/bin/env python3
"""
Exploration Demo: Knowledge Graph Discovery

This demo shows how to use the exploration features to discover
and understand a knowledge graph schema.
"""

import asyncio
from pathlib import Path

from rdf4j_mcp.config import BackendType, Settings
from rdf4j_mcp.server import RDF4JMCPServer


async def main():
    sample_data = Path(__file__).parent / "sample_data.ttl"

    print("=" * 60)
    print("Knowledge Graph Exploration Demo")
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
        owl_classes = [
            b
            for b in (classes.bindings or [])
            if "example.org" in b.get("class", {}).get("value", "")
        ]

        print(f"\nFound {len(owl_classes)} custom classes:")
        for cls in owl_classes:
            iri = cls.get("class", {}).get("value", "")
            label = cls.get("label", {}).get("value", "No label")
            comment = cls.get("comment", {}).get("value", "")
            print(f"\n   {iri.split('/')[-1]}")
            print(f"   Label: {label}")
            if comment:
                print(f"   Description: {comment}")

        # Step 3: Explore Properties for Each Class
        print("\n\n3. CLASS-PROPERTY RELATIONSHIPS")
        print("=" * 60)

        for cls in owl_classes:
            class_iri = cls.get("class", {}).get("value", "")
            class_name = class_iri.split("/")[-1]

            props = await backend.search_properties(domain=class_iri)
            class_props = [
                p
                for p in (props.bindings or [])
                if p.get("domain", {}).get("value", "") == class_iri
            ]

            if class_props:
                print(f"\n{class_name}:")
                for prop in class_props:
                    prop_name = prop.get("property", {}).get("value", "").split("/")[-1]
                    range_val = prop.get("range", {}).get("value", "")
                    range_name = range_val.split("/")[-1] if range_val else "Any"
                    print(f"   -> {prop_name} -> {range_name}")

        # Step 4: Explore Instance Distribution
        print("\n\n4. INSTANCE DISTRIBUTION")
        print("=" * 60)

        for cls in owl_classes:
            class_iri = cls.get("class", {}).get("value", "")
            class_name = class_iri.split("/")[-1]

            instances = await backend.find_instances(class_iri)
            count = len(instances.bindings or [])

            if count > 0:
                print(f"\n{class_name}: {count} instances")
                for inst in (instances.bindings or [])[:3]:
                    inst_name = inst.get("instance", {}).get("value", "").split("/")[-1]
                    label = inst.get("label", {}).get("value", "")
                    display = f"{inst_name}"
                    if label:
                        display += f" ({label})"
                    print(f"   - {display}")
                if count > 3:
                    print(f"   ... and {count - 3} more")

        # Step 5: Relationship Analysis
        print("\n\n5. RELATIONSHIP ANALYSIS")
        print("=" * 60)

        # Find all object properties and their usage
        query = """
        PREFIX ex: <http://example.org/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?prop ?domain ?range (COUNT(*) as ?usage)
        WHERE {
            ?prop a owl:ObjectProperty ;
                  rdfs:domain ?domain ;
                  rdfs:range ?range .
            ?s ?prop ?o .
        }
        GROUP BY ?prop ?domain ?range
        ORDER BY DESC(?usage)
        """
        result = await backend.sparql_select(query)

        print("\nObject Property Usage:")
        for binding in result.bindings or []:
            prop = binding.get("prop", {}).get("value", "").split("/")[-1]
            domain = binding.get("domain", {}).get("value", "").split("/")[-1]
            range_ = binding.get("range", {}).get("value", "").split("/")[-1]
            usage = binding.get("usage", {}).get("value", "0")
            print(f"   {domain} --[{prop}]--> {range_}  (used {usage}x)")

        # Step 6: Network Connectivity
        print("\n\n6. CONNECTIVITY ANALYSIS")
        print("=" * 60)

        # Find entities with most connections
        query = """
        PREFIX ex: <http://example.org/>

        SELECT ?entity ?type (COUNT(?related) as ?connections)
        WHERE {
            ?entity a ?type .
            { ?entity ?p ?related } UNION { ?related ?p ?entity }
            FILTER(?type IN (ex:Person, ex:Project, ex:Organization))
        }
        GROUP BY ?entity ?type
        ORDER BY DESC(?connections)
        LIMIT 10
        """
        result = await backend.sparql_select(query)

        print("\nMost Connected Entities:")
        for binding in result.bindings or []:
            entity = binding.get("entity", {}).get("value", "").split("/")[-1]
            type_ = binding.get("type", {}).get("value", "").split("/")[-1]
            conns = binding.get("connections", {}).get("value", "0")
            print(f"   {entity} ({type_}): {conns} connections")

        print("\n" + "=" * 60)
        print("Exploration completed!")
        print("=" * 60)

    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
