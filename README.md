# RDF4J MCP Server

**Explore knowledge graphs with Claude** - A Model Context Protocol (MCP) server that enables AI-powered exploration of RDF data and SPARQL querying.

```
Claude + Knowledge Graphs = Powerful Semantic Search & Discovery
```

## What It Does

RDF4J MCP Server connects Claude (or any MCP-compatible AI) to your knowledge graphs:

- **Query your data** - Ask questions in natural language, get SPARQL queries executed automatically
- **Explore schemas** - Understand ontologies, classes, properties, and relationships
- **Discover insights** - Find patterns and connections in your knowledge graph
- **Readonly mode** - Protect production data by blocking write operations

## Quick Demo

Get started in under 2 minutes:

```bash
# 1. Install
git clone https://github.com/odysa/rdf4j-mcp.git
cd rdf4j-mcp
pip install -e .

# 2. Start RDF4J server
docker run -d -p 8080:8080 eclipse/rdf4j-workbench

# 3. Connect to it
rdf4j-mcp --server-url http://localhost:8080/rdf4j-server --repository my-repo
```

Then configure Claude Desktop (see [Setup Guide](#claude-desktop-configuration)) and try these prompts:

> "What classes and properties are in this knowledge graph?"

> "Find all people and the projects they work on"

> "Show me all instances of type Person"

## Installation

### Prerequisites

- Python 3.11+
- pip or [rye](https://rye.astral.sh/) package manager
- RDF4J server (Docker recommended)

### Install from Source

```bash
git clone https://github.com/odysa/rdf4j-mcp.git
cd rdf4j-mcp

# Using pip
pip install -e .

# Or using rye (faster)
rye sync
```

## Usage

Connect to an RDF4J server:

```bash
# Start RDF4J server (Docker)
docker run -d -p 8080:8080 eclipse/rdf4j-workbench

# Connect to it
rdf4j-mcp --server-url http://localhost:8080/rdf4j-server --repository my-repo

# Enable readonly mode (blocks write operations)
rdf4j-mcp --server-url http://localhost:8080/rdf4j-server --repository my-repo --readonly
```

## Claude Desktop Configuration

Add to your Claude Desktop config file:

| Platform | Config Location |
|----------|-----------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Basic Config

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["--server-url", "http://localhost:8080/rdf4j-server", "--repository", "my-repo"]
    }
  }
}
```

### Readonly Mode (Recommended for Production)

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["--server-url", "http://localhost:8080/rdf4j-server", "--repository", "my-repo", "--readonly"]
    }
  }
}
```

### Using Environment Variables

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "env": {
        "RDF4J_MCP_RDF4J_SERVER_URL": "http://localhost:8080/rdf4j-server",
        "RDF4J_MCP_DEFAULT_REPOSITORY": "my-repo",
        "RDF4J_MCP_READONLY": "true"
      }
    }
  }
}
```

After editing the config, restart Claude Desktop.

## Features

### MCP Tools

| Tool | Description |
|------|-------------|
| `sparql_select` | Execute SELECT queries, returns JSON results |
| `sparql_construct` | Execute CONSTRUCT/DESCRIBE queries, returns Turtle |
| `sparql_ask` | Execute ASK queries, returns boolean |
| `describe_resource` | Get all triples about an IRI |
| `search_classes` | Find classes by name pattern |
| `search_properties` | Find properties by pattern, domain, or range |
| `find_instances` | Find instances of a class |
| `get_schema_summary` | Get ontology overview with statistics |
| `list_repositories` | List available repositories |
| `get_namespaces` | Get namespace prefix mappings |
| `get_statistics` | Get statement/class/property counts |
| `select_repository` | Switch active repository |
| `get_current_repository` | Get current repository ID |

### MCP Resources

| URI | Description |
|-----|-------------|
| `rdf4j://repositories` | List of available repositories |
| `rdf4j://repository/{id}/schema` | Schema summary for a repository |
| `rdf4j://repository/{id}/namespaces` | Namespace prefixes |
| `rdf4j://repository/{id}/statistics` | Repository statistics |

### MCP Prompts

| Prompt | Description |
|--------|-------------|
| `explore_knowledge_graph` | Guided exploration with schema context |
| `write_sparql_query` | Natural language to SPARQL assistance |
| `explain_ontology` | Explain classes, properties, and relationships |

## Configuration Reference

### CLI Arguments

```
rdf4j-mcp [OPTIONS]

Options:
  --server-url URL     RDF4J server URL (default: http://localhost:8080/rdf4j-server)
  --repository ID      Default repository ID
  --readonly           Block write operations (INSERT, DELETE, etc.)
  --debug              Enable debug logging
```

### Environment Variables

All variables use the `RDF4J_MCP_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `RDF4J_SERVER_URL` | `http://localhost:8080/rdf4j-server` | RDF4J server URL |
| `DEFAULT_REPOSITORY` | - | Default repository ID |
| `READONLY` | `false` | Block write operations |
| `QUERY_TIMEOUT` | `30` | Query timeout in seconds |
| `DEFAULT_LIMIT` | `100` | Default LIMIT for queries |
| `MAX_LIMIT` | `10000` | Maximum allowed LIMIT |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"
# Or using rye
rye sync --all-features

# Run tests
pytest

# Lint and format
ruff check src tests
ruff format src tests

# Type check
ty check src
```

## Troubleshooting

### Server won't start

Make sure all dependencies are installed:
```bash
pip install -e ".[dev]"
```

### "Repository not found" error

1. Verify RDF4J server is running: `curl http://localhost:8080/rdf4j-server/repositories`
2. Check repository exists in RDF4J Workbench
3. Verify `--repository` argument matches the repository ID

### Query timeout

Increase timeout via environment variable:
```bash
export RDF4J_MCP_QUERY_TIMEOUT=120
rdf4j-mcp --server-url http://localhost:8080/rdf4j-server ...
```

### Write operations blocked

If you see "Write operations are not allowed in readonly mode", the server is running with `--readonly` flag or `RDF4J_MCP_READONLY=true`. This is intentional for production safety. To allow writes, remove the readonly configuration.

### Claude Desktop not detecting the server

1. Verify config file syntax (valid JSON)
2. Check that `rdf4j-mcp` is in your PATH, or use absolute path
3. Restart Claude Desktop completely

## License

MIT
