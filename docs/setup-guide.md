# Setup Guide

This guide covers detailed setup instructions for the RDF4J MCP Server.

## Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- (Optional) RDF4J Server for remote backend

## Installation Methods

### Method 1: pip install (Recommended)

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Method 2: Using uv

```bash
# Install uv if you haven't
pip install uv

# Create environment and install
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Backend Setup

### Local Backend (rdflib)

The local backend uses rdflib for in-memory RDF storage. It's perfect for:
- Development and testing
- Small to medium datasets
- Standalone usage without external services

**Configuration:**

```bash
# Empty in-memory store
rdf4j-mcp --backend local

# Load from file
rdf4j-mcp --backend local --store-path /path/to/data.ttl

# Specify format explicitly
rdf4j-mcp --backend local --store-path data.rdf --store-format xml
```

**Supported formats:**
- `turtle` - Turtle (.ttl)
- `xml` - RDF/XML (.rdf, .xml)
- `n3` - Notation3 (.n3)
- `nt` - N-Triples (.nt)
- `nquads` - N-Quads (.nq)
- `trig` - TriG (.trig)
- `jsonld` - JSON-LD (.jsonld)

### Remote Backend (RDF4J Server)

The remote backend connects to an RDF4J server via HTTP. Use this for:
- Production deployments
- Large datasets
- Shared repositories
- Advanced RDF4J features (inference, full-text search)

**Setting up RDF4J Server:**

1. **Using Docker (easiest):**
   ```bash
   docker run -d -p 8080:8080 eclipse/rdf4j-workbench
   ```

2. **Manual installation:**
   - Download from https://rdf4j.org/download/
   - Deploy the WAR files to Tomcat or Jetty
   - Access workbench at http://localhost:8080/rdf4j-workbench

**Configuration:**

```bash
rdf4j-mcp --backend remote \
  --server-url http://localhost:8080/rdf4j-server \
  --repository my-repository
```

## MCP Client Integration

### Claude Desktop

1. Find your config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add the server configuration:

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

3. Restart Claude Desktop

### Using with Environment Variables

You can also use a `.env` file:

```bash
# .env
RDF4J_MCP_BACKEND_TYPE=remote
RDF4J_MCP_RDF4J_SERVER_URL=http://localhost:8080/rdf4j-server
RDF4J_MCP_DEFAULT_REPOSITORY=my-repo
RDF4J_MCP_QUERY_TIMEOUT=60
```

Then simply run:
```bash
rdf4j-mcp
```

### Claude Desktop with Environment Variables

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

## Verifying Installation

### Check the Server Starts

```bash
# Should start without errors
rdf4j-mcp --backend local --debug
```

### Test with MCP Inspector

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector with your server
mcp-inspector rdf4j-mcp --backend local
```

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=rdf4j_mcp

# Run specific test file
pytest tests/test_local_backend.py -v
```

## Troubleshooting

### "Backend not connected" Error

Make sure you're calling `connect()` or using the server properly:
```python
async with LocalBackend() as backend:
    # Use backend here
    pass
```

### "Repository not found" Error

For remote backend, verify:
1. RDF4J server is running
2. Repository exists (check in RDF4J Workbench)
3. URL and repository ID are correct

### Import Errors

Ensure all dependencies are installed:
```bash
pip install -e ".[dev]"
```

### Connection Timeout

Increase the timeout:
```bash
rdf4j-mcp --backend remote --server-url http://...
# Or set environment variable
export RDF4J_MCP_QUERY_TIMEOUT=120
```

## Next Steps

- Check out the [examples](../examples/) for usage patterns
- Read about [available tools](../README.md#tools)
- Explore [MCP prompts](../README.md#prompts) for guided workflows
