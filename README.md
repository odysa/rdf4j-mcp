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
- **Production-ready** - Connect to RDF4J servers for robust knowledge graph access

## Quick Demo

Get started in under 2 minutes:

```bash
# 1. Install
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp
pip install -e .

# 2. Start RDF4J server (Docker)
docker run -d -p 8080:8080 eclipse/rdf4j-workbench

# 3. Connect to it
rdf4j-mcp http://localhost:8080/rdf4j-server
```

Then configure Claude Desktop (see [Setup Guide](#claude-desktop-configuration)) and try these prompts:

> "What repositories are available?"

> "What classes and properties are in this knowledge graph?"

> "Find all people and the projects they work on"

### Try It Programmatically

```bash
python examples/demo_basic.py
```

Sample output:
```
============================================================
RDF4J MCP Server - Basic Demo
============================================================

1. Repository Statistics
----------------------------------------
   Total statements: 97
   Total classes: 5
   Total properties: 10

2. Classes in Ontology
----------------------------------------
   Person: A human being
   Project: A planned endeavor with specific goals
   Organization: A company, institution, or other organized body

3. SPARQL SELECT: Find all people and their projects
----------------------------------------
   Alice Johnson -> Knowledge Graph Platform
   Alice Johnson -> Data Pipeline Infrastructure
   Bob Smith -> Knowledge Graph Platform
   Carol Williams -> Analytics Web Dashboard
```

## Installation

### Prerequisites

- Python 3.10+
- pip or [uv](https://github.com/astral-sh/uv) package manager

### Install from Source

```bash
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp

# Using pip
pip install -e .

# Or using uv (faster)
uv sync
```

## Usage

Connect to an RDF4J server for knowledge graph access:

```bash
# Start RDF4J server (Docker)
docker run -d -p 8080:8080 eclipse/rdf4j-workbench

# Connect to it
rdf4j-mcp http://localhost:8080/rdf4j-server

# Connect with a default repository
rdf4j-mcp http://localhost:8080/rdf4j-server --repository my-repo
```

## Claude Desktop Configuration

Add to your Claude Desktop config file:

| Platform | Config Location |
|----------|-----------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Basic Configuration

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["http://localhost:8080/rdf4j-server"]
    }
  }
}
```

### With Default Repository

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["http://localhost:8080/rdf4j-server", "--repository", "my-repo"]
    }
  }
}
```

### Using uv

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rdf4j-mcp", "rdf4j-mcp", "http://localhost:8080/rdf4j-server"]
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
rdf4j-mcp SERVER_URL [OPTIONS]

Arguments:
  SERVER_URL                RDF4J server URL (e.g., http://localhost:8080/rdf4j-server)

Options:
  --repository ID           Default repository ID
  --debug                   Enable debug logging
```

### Environment Variables

All variables use the `RDF4J_MCP_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `RDF4J_SERVER_URL` | `http://localhost:8080/rdf4j-server` | RDF4J server URL |
| `DEFAULT_REPOSITORY` | - | Default repository ID |
| `QUERY_TIMEOUT` | `30` | Query timeout in seconds |
| `DEFAULT_LIMIT` | `100` | Default LIMIT for queries |
| `MAX_LIMIT` | `10000` | Maximum allowed LIMIT |

## Examples

The [examples/](examples/) directory contains:

- **`sample_data.ttl`** - Sample knowledge graph with people, projects, and technologies
- **`demo_basic.py`** - Basic operations: statistics, namespaces, classes, SPARQL queries
- **`demo_exploration.py`** - Schema discovery and knowledge graph analysis
- **`demo_sparql_queries.py`** - SPARQL query patterns (SELECT, CONSTRUCT, ASK, aggregation)

Run any demo:
```bash
python examples/demo_basic.py
python examples/demo_exploration.py
python examples/demo_sparql_queries.py
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"
# Or using uv
uv sync --dev

# Run tests
pytest

# Run tests with coverage
pytest --cov=rdf4j_mcp

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
rdf4j-mcp http://localhost:8080/rdf4j-server
```

### Claude Desktop not detecting the server

1. Verify config file syntax (valid JSON)
2. Check that `rdf4j-mcp` is in your PATH, or use absolute path
3. Restart Claude Desktop completely

## License

MIT
