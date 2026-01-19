# RDF4J MCP Server Examples

This directory contains example scripts and sample data to help you get started with the RDF4J MCP Server.

## Sample Data

### `sample_data.ttl`

A sample knowledge graph representing a fictional company with:
- **Classes**: Person, Organization, Project, Technology, Department
- **People**: Alice, Bob, Carol, David, Emma
- **Projects**: KG Platform, Data Pipeline, Web Dashboard, ML Models
- **Technologies**: Python, SPARQL, RDF4J, React, Kubernetes

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
- Finding instances
- Describing resources
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
- Relationship analysis
- Connectivity analysis

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
- HAVING clauses
- Subqueries
- UNION patterns
- Property paths
- REGEX filters
- ASK queries
- CONSTRUCT queries

## Running the Demos

1. **Install the package:**
   ```bash
   pip install -e .
   ```

2. **Run any demo:**
   ```bash
   python examples/demo_basic.py
   python examples/demo_exploration.py
   python examples/demo_sparql_queries.py
   ```

## Using with MCP

To use the sample data with the MCP server:

```bash
# Start the server with sample data
rdf4j-mcp --backend local --store-path examples/sample_data.ttl

# Or configure in Claude Desktop
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": [
        "--backend", "local",
        "--store-path", "/path/to/rdf4j-mcp/examples/sample_data.ttl"
      ]
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
  ?person a ex:Person ; ex:name ?name ; ex:worksOn ?project .
}
```

### Describe a Resource
```
Use describe_resource with iri "http://example.org/alice" to see all information about Alice.
```

## Creating Your Own Data

Use the sample data as a template. Key elements:

1. **Define namespaces:**
   ```turtle
   @prefix ex: <http://example.org/> .
   @prefix owl: <http://www.w3.org/2002/07/owl#> .
   ```

2. **Define classes:**
   ```turtle
   ex:MyClass a owl:Class ;
       rdfs:label "My Class" ;
       rdfs:comment "Description of the class" .
   ```

3. **Define properties:**
   ```turtle
   ex:myProperty a owl:DatatypeProperty ;
       rdfs:domain ex:MyClass ;
       rdfs:range xsd:string .
   ```

4. **Create instances:**
   ```turtle
   ex:instance1 a ex:MyClass ;
       ex:myProperty "value" .
   ```
