"""
Pinterest MCP Tool for Agno Agent.

This tool integrates the Pinterest MCP server with your Agno agent,
demonstrating Pattern 2 MCP usage: Agent → MCP Client → MCP Server → Pinterest

Compare this to pexels_tool.py to see the difference between:
- Direct API integration (Pexels)
- MCP-mediated integration (Pinterest)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agno.tools import tool
from services.mcp_client import search_pinterest_sync
from agent.hooks import log_pre_hook


@tool(pre_hook=log_pre_hook)
def search_pinterest_mcp(query: str, count: int = 10) -> list[dict]:
    """Search Pinterest for artist reference photos using MCP.

    This tool demonstrates MCP (Model Context Protocol) integration.
    Unlike direct API calls, this tool:
    1. Connects to a Pinterest MCP server
    2. Discovers available tools dynamically
    3. Calls tools through standardized protocol
    4. Returns results to the agent

    Educational benefits:
    - Learn how MCP enables dynamic tool discovery
    - Understand protocol-based vs direct integration
    - See how agents can use any MCP server generically

    Use this tool to find reference images for art practice sessions.
    Pinterest often has better artistic references than stock photo sites.

    Args:
        query: Search terms for finding reference photos.
              Examples: "figure drawing pose", "hand anatomy reference",
              "dynamic gesture sketch", "portrait lighting study"
        count: Number of photos to retrieve (default 10, max 30)

    Returns:
        List of image dictionaries with url, title, description, etc.
    """
    # This calls the MCP server, which handles the actual Pinterest search
    # The agent doesn't need to know HOW Pinterest is accessed - just that
    # there's an MCP tool that can do it
    print(f"[Pinterest MCP Tool] Searching via MCP: '{query}' (count: {count})")

    try:
        images = search_pinterest_sync(query=query, limit=count)

        print(f"[Pinterest MCP Tool] Found {len(images)} images via MCP")

        # Convert MCP response format to agent-friendly format
        return [
            {
                "id": img.get("id", ""),
                "url": img.get("image_url", ""),
                "thumbnail": img.get("thumbnail_url", ""),
                "title": img.get("title", ""),
                "description": img.get("description", ""),
                "source": img.get("source_url", ""),
                "creator": img.get("creator", ""),
            }
            for img in images
        ]

    except Exception as e:
        print(f"[Pinterest MCP Tool] Error: {e}")
        return []


@tool(pre_hook=log_pre_hook)
def search_pinterest_diverse_mcp(queries: list[str], per_query: int = 5) -> list[dict]:
    """Search Pinterest with multiple queries for diverse reference images.

    This demonstrates MCP's ability to expose complex operations as simple tools.
    The MCP server handles query diversity logic, not the agent.

    Use this when you need variety in reference images across multiple
    themes or perspectives.

    Args:
        queries: List of 3-6 specific search terms for diversity.
                Example: ["ballet dancer", "martial arts", "parkour", "gymnast"]
        per_query: Images to fetch per query term (default 5)

    Returns:
        Combined list of diverse images (typically 15-30 images)
    """
    print(f"[Pinterest MCP Tool] Diverse search via MCP: {queries}")

    try:
        # Import here to avoid circular imports
        import asyncio
        from services.mcp_client import PinterestMCPClient

        server_path = str(Path(__file__).parent.parent.parent / "mcp_servers" / "pinterest_server.py")

        async def _search():
            async with PinterestMCPClient(server_path) as client:
                return await client.search_diverse(queries, per_query)

        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        images = loop.run_until_complete(_search())

        print(f"[Pinterest MCP Tool] Found {len(images)} diverse images")

        return [
            {
                "id": img.get("id", ""),
                "url": img.get("image_url", ""),
                "thumbnail": img.get("thumbnail_url", ""),
                "title": img.get("title", ""),
                "description": img.get("description", ""),
                "source": img.get("source_url", ""),
                "creator": img.get("creator", ""),
            }
            for img in images
        ]

    except Exception as e:
        print(f"[Pinterest MCP Tool] Error: {e}")
        import traceback
        traceback.print_exc()
        return []


# Educational comparison note:
# -----------------------------
# Compare this file to pexels_tool.py:
#
# pexels_tool.py:
#   - Imports pexels_client directly
#   - Calls pexels_client.search_photos() directly
#   - Tightly coupled to Pexels API structure
#
# pinterest_mcp_tool.py (this file):
#   - Uses MCP client (generic protocol)
#   - Calls MCP tools through standardized interface
#   - Loosely coupled - could swap MCP servers without changing agent
#
# Key insight: With MCP, your agent can use ANY image service that
# implements the protocol, not just services you've directly integrated.
