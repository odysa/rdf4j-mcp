# rdf4j-mcp

MCP server for RDF4J integration, built with [FastMCP](https://github.com/jlowin/fastmcp).

## Installation

```bash
uv pip install -e .
```

## Usage

### Run the server

```bash
# Using the installed entry point
rdf4j-mcp

# Or using fastmcp CLI
fastmcp run src/rdf4j_mcp/server.py

# Or using uv
uv run rdf4j-mcp
```

### Claude Desktop Configuration

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

## Available Components

### Tools

| Tool | Description |
|------|-------------|
| `echo` | Echo a message back to the caller |
| `add` | Add two numbers together |

### Resources

| Resource URI | Description |
|--------------|-------------|
| `config://version` | Get the current server version |
| `config://info` | Get server information |

### Prompts

| Prompt | Description |
|--------|-------------|
| `summarize` | Generate a prompt asking for a summary |
| `explain` | Generate a prompt asking for an explanation |

## Development

### Install dev dependencies

```bash
uv sync --dev
```

### Run tests

```bash
uv run pytest
```

### Test with FastMCP client

```python
from fastmcp import Client

async with Client("src/rdf4j_mcp/server.py") as client:
    tools = await client.list_tools()
    result = await client.call_tool("add", {"a": 5, "b": 3})
    print(result)  # 8
```
