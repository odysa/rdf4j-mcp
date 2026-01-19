# Setup Guide

Complete setup instructions for the RDF4J MCP Server.

## Quick Setup (TL;DR)

```bash
# Install
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp
pip install -e .

# Run with sample data
rdf4j-mcp --backend local --store-path examples/sample_data.ttl

# Test it works
python examples/demo_basic.py
```

Then [configure Claude Desktop](#claude-desktop-setup).

## Prerequisites

- **Python 3.10+** - Check with `python --version`
- **pip** or **uv** - Package manager

## Installation

### Option 1: pip (Standard)

```bash
# Clone the repository
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install
pip install -e .

# Install with dev tools (for running tests)
pip install -e ".[dev]"
```

### Option 2: uv (Faster)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
# Install uv (if needed)
pip install uv

# Clone and install
git clone https://github.com/your-org/rdf4j-mcp.git
cd rdf4j-mcp
uv sync

# With dev tools
uv sync --dev
```

### Verify Installation

```bash
# Should show help
rdf4j-mcp --help

# Should run without errors
rdf4j-mcp --backend local --debug
```

## Backend Setup

### Local Backend (rdflib)

The local backend stores RDF data in memory using rdflib. Best for:
- Getting started and learning
- Development and testing
- Small to medium datasets (< 1M triples)
- Standalone usage without external services

**Basic usage:**

```bash
# Empty store
rdf4j-mcp --backend local

# Load a Turtle file
rdf4j-mcp --backend local --store-path data.ttl

# Load RDF/XML
rdf4j-mcp --backend local --store-path data.rdf --store-format xml
```

**Supported RDF formats:**

| Format | Extension | Flag |
|--------|-----------|------|
| Turtle | .ttl | `turtle` |
| RDF/XML | .rdf, .xml | `xml` |
| N-Triples | .nt | `nt` |
| Notation3 | .n3 | `n3` |
| JSON-LD | .jsonld | `jsonld` |
| N-Quads | .nq | `nquads` |
| TriG | .trig | `trig` |

### Remote Backend (RDF4J Server)

The remote backend connects to an Eclipse RDF4J server. Best for:
- Production deployments
- Large datasets (millions of triples)
- Shared access / multi-user scenarios
- Advanced features (inference, full-text search)

**Step 1: Start RDF4J Server**

Using Docker (easiest):
```bash
docker run -d -p 8080:8080 --name rdf4j eclipse/rdf4j-workbench
```

Or download from [rdf4j.org/download](https://rdf4j.org/download/) and deploy to Tomcat/Jetty.

**Step 2: Create a Repository**

1. Open RDF4J Workbench: http://localhost:8080/rdf4j-workbench
2. Click "New repository"
3. Choose a type (Native Java Store for most cases)
4. Enter an ID (e.g., `my-repo`)
5. Click "Create"

**Step 3: Connect**

```bash
rdf4j-mcp --backend remote \
  --server-url http://localhost:8080/rdf4j-server \
  --repository my-repo
```

## Claude Desktop Setup

### 1. Find Your Config File

| Platform | Location |
|----------|----------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Create the file if it doesn't exist.

### 2. Add Server Configuration

**Local backend with sample data:**

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "args": [
        "--backend", "local",
        "--store-path", "/absolute/path/to/rdf4j-mcp/examples/sample_data.ttl"
      ]
    }
  }
}
```

**Using uv:**

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/rdf4j-mcp",
        "rdf4j-mcp",
        "--backend", "local",
        "--store-path", "/absolute/path/to/rdf4j-mcp/examples/sample_data.ttl"
      ]
    }
  }
}
```

**Remote backend with environment variables:**

```json
{
  "mcpServers": {
    "rdf4j": {
      "command": "rdf4j-mcp",
      "env": {
        "RDF4J_MCP_BACKEND_TYPE": "remote",
        "RDF4J_MCP_RDF4J_SERVER_URL": "http://localhost:8080/rdf4j-server",
        "RDF4J_MCP_DEFAULT_REPOSITORY": "my-repo"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Close and reopen Claude Desktop completely (quit from system tray if needed).

### 4. Verify Connection

In Claude Desktop, you should see the RDF4J tools available. Try asking:

> "What tools do you have for querying RDF data?"

Or:

> "Use get_schema_summary to show me what's in the knowledge graph"

## Environment Variables

Use environment variables for configuration without CLI arguments:

```bash
# Create .env file
cat > .env << 'EOF'
RDF4J_MCP_BACKEND_TYPE=local
RDF4J_MCP_LOCAL_STORE_PATH=/path/to/data.ttl
RDF4J_MCP_QUERY_TIMEOUT=60
RDF4J_MCP_DEFAULT_LIMIT=200
EOF

# Run (automatically loads .env)
rdf4j-mcp
```

All variables use the `RDF4J_MCP_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_TYPE` | `local` | `local` or `remote` |
| `RDF4J_SERVER_URL` | `http://localhost:8080/rdf4j-server` | RDF4J server URL |
| `DEFAULT_REPOSITORY` | - | Default repository ID |
| `LOCAL_STORE_PATH` | - | Path to RDF file |
| `LOCAL_STORE_FORMAT` | `turtle` | RDF format |
| `QUERY_TIMEOUT` | `30` | Timeout in seconds |
| `DEFAULT_LIMIT` | `100` | Default query LIMIT |
| `MAX_LIMIT` | `10000` | Maximum LIMIT |

## Testing Your Setup

### Run the Demo Scripts

```bash
# Basic operations
python examples/demo_basic.py

# Schema exploration
python examples/demo_exploration.py

# SPARQL query patterns
python examples/demo_sparql_queries.py
```

### Use MCP Inspector

The MCP Inspector lets you test your server interactively:

```bash
# Install
npm install -g @modelcontextprotocol/inspector

# Run
mcp-inspector rdf4j-mcp --backend local --store-path examples/sample_data.ttl
```

### Run Unit Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=rdf4j_mcp

# Specific test file
pytest tests/test_local_backend.py -v
```

## Troubleshooting

### "Command not found: rdf4j-mcp"

The package isn't in your PATH. Solutions:

1. **Activate your virtual environment:**
   ```bash
   source venv/bin/activate  # or .venv/bin/activate for uv
   ```

2. **Use absolute path in Claude config:**
   ```json
   {
     "command": "/path/to/venv/bin/rdf4j-mcp"
   }
   ```

3. **Use uv run:**
   ```json
   {
     "command": "uv",
     "args": ["run", "--directory", "/path/to/rdf4j-mcp", "rdf4j-mcp"]
   }
   ```

### "Repository not found"

For remote backend:
1. Check RDF4J server is running: `curl http://localhost:8080/rdf4j-server/repositories`
2. Verify repository exists in RDF4J Workbench
3. Check the repository ID matches exactly (case-sensitive)

### "Backend not connected"

The backend context manager wasn't used correctly. If using programmatically:
```python
async with LocalBackend() as backend:
    # Use backend here
    pass
```

### Claude Desktop doesn't show the server

1. Check JSON syntax (use a validator)
2. Verify the command works in terminal first
3. Check Claude Desktop logs (Help → Show Logs)
4. Restart Claude Desktop completely (quit from system tray)

### Query timeout

Increase the timeout:
```bash
export RDF4J_MCP_QUERY_TIMEOUT=120
```

Or in Claude Desktop config:
```json
{
  "env": {
    "RDF4J_MCP_QUERY_TIMEOUT": "120"
  }
}
```

### Import errors

Reinstall with all dependencies:
```bash
pip install -e ".[dev]"
```

## Next Steps

- Try the [examples](../examples/) to learn usage patterns
- Read about [available tools](../README.md#mcp-tools)
- Explore [MCP prompts](../README.md#mcp-prompts) for guided workflows
- Load your own RDF data and start exploring!
