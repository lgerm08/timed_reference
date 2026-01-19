# Pinterest MCP Server

A Model Context Protocol (MCP) server that provides Pinterest image search functionality for AI agents.

## Educational Purpose

This implementation demonstrates **Pattern 2** MCP usage:

```
AI Agent (Python/Moonshot) → MCP Client → MCP Server → Pinterest
```

This is different from the more common **Pattern 1**:

```
AI Assistant (Claude Desktop) → MCP Server → Pinterest
```

## What You'll Learn

1. **MCP Protocol Basics**
   - How MCP uses JSON-RPC over stdio
   - Tool discovery and schema definition
   - Request/response patterns

2. **Server Implementation**
   - Building an MCP server in Python
   - Exposing tools through standardized interface
   - Handling async operations

3. **Client Integration**
   - Connecting agents to MCP servers
   - Dynamic tool discovery
   - Protocol-based vs direct API integration

4. **Dual Usage**
   - Same server works for both your agent AND Claude Code
   - Demonstrates MCP's flexibility

## Files

- `pinterest_server.py` - The MCP server implementation
- `mcp_config.json` - Configuration for Claude Code/Desktop

## Installation

Install MCP Python SDK:

```bash
pip install mcp
```

For actual Pinterest integration (replace mock data):

```bash
pip install py3-pinterest
# or
pip install pinterest-api
```

## Testing the Server

### Test 1: Direct Server Test (stdio)

```bash
cd timed_reference
python mcp_servers/pinterest_server.py
```

Then send MCP protocol messages via stdin. Example:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
```

### Test 2: With MCP Inspector (Recommended)

Install the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python mcp_servers/pinterest_server.py
```

This gives you a GUI to test the server.

### Test 3: From Your Python Agent

```python
from services.mcp_client import PinterestMCPClient
import asyncio

async def test():
    async with PinterestMCPClient("mcp_servers/pinterest_server.py") as client:
        results = await client.search("figure drawing", limit=5)
        print(results)

asyncio.run(test())
```

### Test 4: With Claude Code (VSCode)

1. Add to your user settings (`.claude/settings.json` or VSCode settings):

```json
{
  "mcpServers": {
    "pinterest": {
      "command": "python",
      "args": ["C:/Users/Lucas/Documents/namastex/tutoriais/timed reference/timed_reference/mcp_servers/pinterest_server.py"]
    }
  }
}
```

2. Restart Claude Code
3. Ask Claude: "Search Pinterest for figure drawing references"

## Available Tools

### 1. `search_pinterest`

Search Pinterest for reference images.

**Parameters:**
- `query` (string, required): Search term (2-4 words recommended)
- `limit` (integer, optional): Number of results (default 10, max 30)
- `art_focused` (boolean, optional): Add art/reference filters (default true)

**Example:**
```json
{
  "query": "hand anatomy reference",
  "limit": 10,
  "art_focused": true
}
```

### 2. `search_pinterest_diverse`

Search with multiple queries for diverse results.

**Parameters:**
- `queries` (array of strings, required): 2-8 search terms
- `images_per_query` (integer, optional): Images per term (default 5, max 10)

**Example:**
```json
{
  "queries": ["ballet dancer", "martial arts", "parkour", "gymnast"],
  "images_per_query": 5
}
```

## Current Implementation Status

⚠️ **Mock Data Mode**

The server currently returns mock/placeholder images for development and learning purposes.

To add real Pinterest integration:

1. **Option A: py3-pinterest library**
   ```python
   from pinterest import Pinterest

   pinterest = Pinterest(email='...', password='...')
   results = pinterest.search('search term')
   ```

2. **Option B: Unofficial API scraping**
   ```python
   # Use httpx to call Pinterest's internal APIs
   # See pinterest_server.py _mock_search() for structure
   ```

3. **Option C: Official Pinterest API**
   - Requires Pinterest Business account
   - Apply for API access
   - Use official endpoints

## Integration with Your Agent

See `agent/tools/pinterest_mcp_tool.py` for how your Agno agent uses this server.

Key differences from direct integration:

| Aspect | Direct API (Pexels) | MCP (Pinterest) |
|--------|-------------------|-----------------|
| Coupling | Tight - imports pexels_client | Loose - protocol-based |
| Discovery | Static - hardcoded | Dynamic - from server |
| Reusability | Agent-specific | Any MCP client can use |
| Standardization | Custom interface | MCP protocol |

## Next Steps for Learning

1. **Observe the protocol**
   - Run MCP Inspector to see JSON-RPC messages
   - Understand initialization, tool listing, tool calls

2. **Modify the server**
   - Add a new tool (e.g., `get_pinterest_board`)
   - See how clients automatically discover it

3. **Compare integrations**
   - Use both Pexels (direct) and Pinterest (MCP)
   - Notice the architectural differences

4. **Build another MCP server**
   - Try Unsplash, Flickr, or another service
   - Your agent can use it with the same MCP client

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Claude MCP Guide](https://code.claude.com/docs/en/mcp)

## Educational Value

This implementation prioritizes **learning** over production-readiness:

✓ Clear comments explaining MCP concepts
✓ Mock data so you can test without credentials
✓ Comparison with direct integration (Pexels)
✓ Works with both your agent AND Claude Code
✓ Step-by-step progression from basic to advanced

Remember: The goal is understanding MCP, not building a production Pinterest client!
