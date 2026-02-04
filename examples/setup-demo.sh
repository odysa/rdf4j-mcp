#!/bin/bash
# Setup script for RDF4J MCP demo
# This script starts RDF4J, creates a repository, and loads sample data

set -e

CONTAINER_NAME="rdf4j-demo"
PORT="${RDF4J_PORT:-8081}"
SERVER_URL="http://localhost:$PORT/rdf4j-server"
REPO_ID="demo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAMPLE_DATA="$SCRIPT_DIR/sample_data.ttl"

echo "=============================================="
echo "RDF4J MCP Demo Setup"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if sample data exists
if [ ! -f "$SAMPLE_DATA" ]; then
    echo "Error: Sample data not found at $SAMPLE_DATA"
    exit 1
fi

# Stop existing container if running
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1 || true
fi

# Start RDF4J container
echo "Starting RDF4J server on port $PORT..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8080" \
    eclipse/rdf4j-workbench:latest > /dev/null

# Wait for server to be ready
echo "Waiting for RDF4J server to start..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s "$SERVER_URL/protocol" > /dev/null 2>&1; then
        echo "RDF4J server is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "Error: RDF4J server failed to start"
    exit 1
fi

# Create repository using RDF4J REST API
echo "Creating repository '$REPO_ID'..."

# Write config to temp file to avoid @ being interpreted as file reference
REPO_CONFIG_FILE=$(mktemp)
cat > "$REPO_CONFIG_FILE" << 'REPOEOF'
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix config: <tag:rdf4j.org,2023:config/>.

[] a config:Repository ;
   config:rep.id "demo" ;
   rdfs:label "Demo Repository" ;
   config:rep.impl [
      config:rep.type "openrdf:SailRepository" ;
      config:sail.impl [
         config:sail.type "openrdf:MemoryStore" ;
         config:sail.iterationCacheSyncThreshold "10000" ;
         config:mem.persist false
      ]
   ].
REPOEOF

curl -s -X PUT \
    -H "Content-Type: text/turtle" \
    -T "$REPO_CONFIG_FILE" \
    "$SERVER_URL/repositories/$REPO_ID" > /dev/null

rm -f "$REPO_CONFIG_FILE"
echo "Repository created!"

# Load sample data
echo "Loading sample data..."
curl -s -X POST \
    -H "Content-Type: text/turtle" \
    -T "$SAMPLE_DATA" \
    "$SERVER_URL/repositories/$REPO_ID/statements" > /dev/null

echo "Sample data loaded!"

# Verify data was loaded
TRIPLE_COUNT=$(curl -s "$SERVER_URL/repositories/$REPO_ID/size")
echo "Repository contains $TRIPLE_COUNT triples"

echo ""
echo "=============================================="
echo "Setup complete!"
echo "=============================================="
echo ""
echo "RDF4J Workbench: http://localhost:$PORT/rdf4j-workbench"
echo "SPARQL Endpoint: $SERVER_URL/repositories/$REPO_ID"
echo ""
echo "Run the MCP server with:"
echo "  rdf4j-mcp --server-url $SERVER_URL --repository $REPO_ID"
echo ""
echo "Or use with Claude Desktop (add to config):"
echo '  {
    "mcpServers": {
      "rdf4j": {
        "command": "rdf4j-mcp",
        "args": ["--server-url", "'"$SERVER_URL"'", "--repository", "'"$REPO_ID"'"]
      }
    }
  }'
echo ""
echo "To stop the demo server:"
echo "  docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
