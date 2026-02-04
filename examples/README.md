# RDF4J MCP Server Examples

This directory contains example scripts and sample data to help you get started with the RDF4J MCP Server.

## Quick Demo Setup

The fastest way to try the MCP server:

```bash
# Run the setup script (requires Docker)
./setup-demo.sh
```

This script will:
1. Start an RDF4J server in Docker
2. Create a `demo` repository
3. Load the sample data

Then run the MCP server:
```bash
rdf4j-mcp --server-url http://localhost:8081/rdf4j-server --repository demo
```

## Sample Data

### `sample_data.ttl`

A sample knowledge graph representing a fictional company with:
- **Classes**: Person, Organization, Project, Technology, Department
- **People**: Alice, Bob, Carol, David, Emma
- **Projects**: KG Platform, Data Pipeline, Web Dashboard, ML Models
- **Technologies**: Python, SPARQL, RDF4J, React, Kubernetes, TensorFlow

## Demo Scripts

### `demo_basic.py`

**Basic operations demo** - Shows fundamental server operations:

```bash
python examples/demo_basic.py
```

Covers:
- Getting repository statistics
- Listing namespaces
- Searching classes and properties
- Basic SPARQL SELECT queries
- ASK queries

### `demo_exploration.py`

**Knowledge graph exploration demo** - Shows how to discover and understand a schema:

```bash
python examples/demo_exploration.py
```

Covers:
- Schema overview and statistics
- Class discovery
- Property-class relationships
- Instance distribution

### `demo_sparql_queries.py`

**SPARQL query patterns demo** - Shows common SPARQL query patterns:

```bash
python examples/demo_sparql_queries.py
```

Covers:
- Basic SELECT queries
- OPTIONAL clauses
- FILTER expressions
- Aggregation (COUNT, GROUP BY)
- Property paths
- CONSTRUCT queries

## Running the Demos

1. **Start the demo server:**
   ```bash
   ./setup-demo.sh
   ```

2. **Run any demo:**
   ```bash
   python examples/demo_basic.py
   python examples/demo_exploration.py
   python examples/demo_sparql_queries.py
   ```

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["--server-url", "http://localhost:8081/rdf4j-server", "--repository", "demo"]
    }
  }
}
```

## Example MCP Tool Usage

Once connected via MCP, try these tools:

### Get Schema Summary
```
Use the get_schema_summary tool to see an overview of the knowledge graph.
```

### Search for Classes
```
Use search_classes with pattern "Person" to find person-related classes.
```

### Execute SPARQL
```
Use sparql_select with this query:
PREFIX ex: <http://example.org/>
SELECT ?name ?project WHERE {
  ?person a ex:Person ; ex:name ?name ; ex:worksOn ?proj .
  ?proj ex:name ?project .
}
```

### Describe a Resource
```
Use describe_resource with iri "http://example.org/alice" to see all information about Alice.
```

## Cleanup

To stop and remove the demo server:

```bash
docker stop rdf4j-demo && docker rm rdf4j-demo
```
