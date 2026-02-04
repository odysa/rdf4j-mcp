# RDF4J MCP Server

**Explore knowledge graphs with Claude** - A Model Context Protocol (MCP) server that enables AI-powered exploration of RDF data and SPARQL querying.

## Quick Demo

Try it out in under 2 minutes:

```bash
# 1. Clone and install
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp
uv sync  # or: pip install -e .

# 2. Start RDF4J + load sample data
./examples/setup-demo.sh

# 3a. Run as local MCP server (stdio)
rdf4j-mcp --server-url http://localhost:8081/rdf4j-server --repository demo

# 3b. Or run as remote HTTP server
rdf4j-mcp-server --port 3000 --server-url http://localhost:8081/rdf4j-server --repository demo
```

Then try these prompts with Claude:

> "What classes and properties are in this knowledge graph?"

> "Find all people and the projects they work on"

> "Show me the project with the highest budget"

## Installation

**Prerequisites:** Python 3.11+, Docker (for RDF4J)

```bash
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp
uv sync  # or: pip install -e .
```

## Two Ways to Run

| Command | Transport | Use Case |
|---------|-----------|----------|
| `rdf4j-mcp` | stdio | MCP client spawns locally (Claude Desktop, VS Code) |
| `rdf4j-mcp-server` | HTTP/SSE | Standalone remote server, multiple clients |

### Option 1: Local Mode (stdio)

The MCP client spawns the server as a local process:

```bash
rdf4j-mcp --server-url http://localhost:8080/rdf4j-server --repository my-repo
```

### Option 2: Remote Mode (HTTP/SSE)

Run as a standalone HTTP server:

```bash
# Start the server
rdf4j-mcp-server --port 3000 \
  --server-url http://localhost:8080/rdf4j-server \
  --repository my-repo

# Or with environment variables
export RDF4J_MCP_RDF4J_SERVER_URL=http://localhost:8080/rdf4j-server
export RDF4J_MCP_DEFAULT_REPOSITORY=my-repo
rdf4j-mcp-server --port 3000

# Or with uvicorn (production)
uvicorn rdf4j_mcp.main:app --host 0.0.0.0 --port 3000 --workers 4
```

**Endpoints:**
- `GET /sse` - SSE endpoint for MCP clients
- `GET /health` - Health check
- `GET /info` - Server configuration

## Client Configuration

### Claude Desktop

Config file locations:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Local mode (stdio):**
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

**Remote mode (HTTP):**
```json
{
  "mcpServers": {
    "rdf4j": {
      "url": "http://your-server:3000/sse"
    }
  }
}
```

### VS Code

Create `.vscode/mcp.json` in your workspace:

**Local mode:**
```json
{
  "servers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": ["--server-url", "http://localhost:8080/rdf4j-server", "--repository", "my-repo"]
    }
  }
}
```

**Remote mode:**
```json
{
  "servers": {
    "rdf4j": {
      "url": "http://your-server:3000/sse"
    }
  }
}
```

For GitHub Copilot, use `@mcp` in chat:
```
@mcp What classes are in the knowledge graph?
```

## Features

### MCP Tools

| Tool | Description |
|------|-------------|
| `sparql_select` | Execute SELECT queries, returns JSON |
| `sparql_construct` | Execute CONSTRUCT/DESCRIBE, returns Turtle |
| `sparql_ask` | Execute ASK queries, returns boolean |
| `describe_resource` | Get all triples about an IRI |
| `search_classes` | Find classes by name pattern |
| `search_properties` | Find properties by pattern/domain/range |
| `find_instances` | Find instances of a class |
| `get_schema_summary` | Ontology overview with statistics |
| `list_repositories` | List available repositories |
| `get_namespaces` | Get namespace prefix mappings |
| `get_statistics` | Statement/class/property counts |
| `select_repository` | Switch active repository |

### MCP Resources

| URI | Description |
|-----|-------------|
| `rdf4j://repositories` | List of repositories |
| `rdf4j://repository/{id}/schema` | Schema summary |
| `rdf4j://repository/{id}/namespaces` | Namespace prefixes |
| `rdf4j://repository/{id}/statistics` | Repository statistics |

### MCP Prompts

| Prompt | Description |
|--------|-------------|
| `explore_knowledge_graph` | Guided exploration with schema context |
| `write_sparql_query` | Natural language to SPARQL |
| `explain_ontology` | Explain classes and relationships |

## Configuration

### CLI Options

**rdf4j-mcp (stdio mode):**
```
--server-url URL    RDF4J server URL (default: http://localhost:8080/rdf4j-server)
--repository ID     Default repository ID
--debug             Enable debug logging
```

**rdf4j-mcp-server (HTTP mode):**
```
--host HOST         Bind address (default: 0.0.0.0)
--port PORT         Listen port (default: 3000)
--server-url URL    RDF4J server URL
--repository ID     Default repository ID
--reload            Auto-reload for development
--debug             Enable debug logging
```

### Environment Variables

All use the `RDF4J_MCP_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `RDF4J_SERVER_URL` | `http://localhost:8080/rdf4j-server` | RDF4J server URL |
| `DEFAULT_REPOSITORY` | - | Default repository ID |
| `QUERY_TIMEOUT` | `30` | Query timeout (seconds) |
| `DEFAULT_LIMIT` | `100` | Default query LIMIT |
| `MAX_LIMIT` | `10000` | Maximum query LIMIT |

## Running RDF4J Server

Using Docker:
```bash
docker run -d -p 8080:8080 eclipse/rdf4j-workbench
```

Then create a repository at http://localhost:8080/rdf4j-workbench.

Or use the demo setup script which handles everything:
```bash
./examples/setup-demo.sh
```

## Development

```bash
uv sync --dev

# Run tests
pytest

# Lint and format
ruff check src tests
ruff format src tests

# Type check
ty check src
```

## License

MIT
