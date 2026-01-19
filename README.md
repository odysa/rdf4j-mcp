# RDF4J MCP Server

A Model Context Protocol (MCP) server for knowledge graph exploration and SPARQL querying. Supports both local RDF stores (via rdflib) and remote RDF4J servers.

## Quick Start

### Installation

```bash
# Clone and install
git clone <repository-url>
cd rdf4j-mcp
pip install -e .

# Or using uv
uv pip install -e .
```

### Run with Local Backend

```bash
# Start with an empty in-memory store
rdf4j-mcp --backend local

# Or load an existing RDF file
rdf4j-mcp --backend local --store-path data.ttl --store-format turtle

# Or using uv
uv run rdf4j-mcp --backend local
```

### Run with Remote RDF4J Server

```bash
rdf4j-mcp --backend remote \
  --server-url http://localhost:8080/rdf4j-server \
  --repository my-repo
```

### Configure in Claude Desktop

Add to your Claude Desktop config:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["--backend", "local", "--store-path", "/path/to/data.ttl"]
    }
  }
}
```

Or using uv:

```json
{
  "mcpServers": {
    "rdf4j-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rdf4j-mcp", "rdf4j-mcp"]
    }
  }
}
```

## Features

### Tools

| Tool | Description |
|------|-------------|
| `sparql_select` | Execute SELECT queries, return JSON |
| `sparql_construct` | Execute CONSTRUCT/DESCRIBE, return Turtle |
| `sparql_ask` | Execute ASK queries, return boolean |
| `describe_resource` | Get all triples about an IRI |
| `search_classes` | Find classes by pattern |
| `search_properties` | Find properties by pattern/domain/range |
| `find_instances` | Find instances of a class |
| `get_schema_summary` | Ontology overview |
| `list_repositories` | List available repositories |
| `get_namespaces` | Get namespace prefixes |
| `get_statistics` | Statement/class/property counts |

### Resources

| URI | Description |
|-----|-------------|
| `rdf4j://repositories` | List of repositories |
| `rdf4j://repository/{id}/schema` | Schema summary |
| `rdf4j://repository/{id}/namespaces` | Namespace prefixes |

### Prompts

| Prompt | Description |
|--------|-------------|
| `explore_knowledge_graph` | Guided KG exploration with schema context |
| `write_sparql_query` | Natural language to SPARQL assistance |
| `explain_ontology` | Explain schema elements |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RDF4J_MCP_BACKEND_TYPE` | `local` | Backend: `local` or `remote` |
| `RDF4J_MCP_RDF4J_SERVER_URL` | `http://localhost:8080/rdf4j-server` | RDF4J server URL |
| `RDF4J_MCP_DEFAULT_REPOSITORY` | - | Default repository ID |
| `RDF4J_MCP_LOCAL_STORE_PATH` | - | Path to local RDF file |
| `RDF4J_MCP_LOCAL_STORE_FORMAT` | `turtle` | RDF format |
| `RDF4J_MCP_QUERY_TIMEOUT` | `30` | Query timeout (seconds) |
| `RDF4J_MCP_DEFAULT_LIMIT` | `100` | Default LIMIT for queries |
| `RDF4J_MCP_MAX_LIMIT` | `10000` | Maximum allowed LIMIT |

### CLI Arguments

```
rdf4j-mcp [OPTIONS]

Options:
  --backend {local,remote}  Backend type (default: local)
  --server-url URL          RDF4J server URL
  --repository ID           Default repository ID
  --store-path PATH         Local RDF file path
  --store-format FORMAT     RDF format (turtle, xml, n3, nt, jsonld)
  --debug                   Enable debug logging
```

## Examples

See the [examples](examples/) directory for:
- Loading and exploring sample data
- Writing SPARQL queries
- Working with ontologies

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"
# Or using uv
uv sync --dev

# Run tests
pytest
# Or using uv
uv run pytest

# Run linter
ruff check src tests

# Type check
mypy src
```

## License

MIT
