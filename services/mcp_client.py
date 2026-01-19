"""
MCP Client for connecting to MCP servers.

This client allows the agent to dynamically discover and use tools
from MCP servers like the Pinterest server.

Educational example showing how AI agents can integrate with MCP.
"""

import asyncio
import json
from typing import Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """
    Client for connecting to MCP servers.

    This demonstrates Pattern 2 MCP usage:
    AI Agent (Python) → MCP Client → MCP Server → External Service

    Compared to Pattern 1:
    AI Assistant (Claude) → MCP Server → External Service
    """

    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.available_tools: dict[str, list[dict]] = {}

    async def connect_server(
        self,
        server_name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None
    ):
        """
        Connect to an MCP server via stdio.

        Args:
            server_name: Friendly name for this server (e.g., "pinterest")
            command: Command to launch the server (e.g., "python")
            args: Arguments for the command (e.g., ["pinterest_server.py"])
            env: Environment variables for the server process
        """
        print(f"[MCP Client] Connecting to {server_name}...")

        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env or {}
        )

        # Connect to server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        # Create session
        read_stream, write_stream = stdio_transport
        session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Initialize session
        await session.initialize()

        # Store session
        self.sessions[server_name] = session

        # List and cache available tools
        tools_response = await session.list_tools()
        self.available_tools[server_name] = [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.inputSchema,
            }
            for tool in tools_response.tools
        ]

        print(f"[MCP Client] Connected to {server_name}")
        print(f"[MCP Client] Available tools: {[t['name'] for t in self.available_tools[server_name]]}")

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any]
    ) -> Any:
        """
        Call a tool on an MCP server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result (parsed from JSON if possible)
        """
        if server_name not in self.sessions:
            raise ValueError(f"Not connected to server '{server_name}'")

        session = self.sessions[server_name]

        print(f"[MCP Client] Calling {server_name}.{tool_name}({arguments})")

        # Call the tool
        result = await session.call_tool(tool_name, arguments)

        # Extract text content
        if result.content:
            text_content = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    text_content += content.text

            # Try to parse as JSON
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return text_content

        return None

    def get_available_tools(self, server_name: str | None = None) -> dict:
        """
        Get available tools from connected servers.

        Args:
            server_name: Specific server, or None for all servers

        Returns:
            Dictionary of {server_name: [tools]}
        """
        if server_name:
            return {server_name: self.available_tools.get(server_name, [])}
        return self.available_tools

    async def close(self):
        """Close all connections."""
        print("[MCP Client] Closing connections...")
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.available_tools.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class PinterestMCPClient:
    """
    Convenience wrapper specifically for Pinterest MCP server.

    This provides a simpler interface for common Pinterest operations
    while demonstrating how to wrap MCP clients for specific use cases.
    """

    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.client: Optional[MCPClient] = None
        self._initialized = False

    async def initialize(self):
        """Connect to the Pinterest MCP server."""
        if self._initialized:
            return

        self.client = MCPClient()

        await self.client.connect_server(
            server_name="pinterest",
            command="python",
            args=[self.server_script_path],
        )

        self._initialized = True

    async def search(
        self,
        query: str,
        limit: int = 10,
        art_focused: bool = True
    ) -> list[dict]:
        """
        Search Pinterest for images.

        Args:
            query: Search term
            limit: Number of results
            art_focused: Add art-specific filters

        Returns:
            List of image dictionaries
        """
        if not self._initialized:
            await self.initialize()

        result = await self.client.call_tool(
            "pinterest",
            "search_pinterest",
            {
                "query": query,
                "limit": limit,
                "art_focused": art_focused,
            }
        )

        return result.get("images", []) if isinstance(result, dict) else []

    async def search_diverse(
        self,
        queries: list[str],
        images_per_query: int = 5
    ) -> list[dict]:
        """
        Search with multiple queries for diverse results.

        Args:
            queries: List of search terms
            images_per_query: Images per query

        Returns:
            Combined list of diverse images
        """
        if not self._initialized:
            await self.initialize()

        result = await self.client.call_tool(
            "pinterest",
            "search_pinterest_diverse",
            {
                "queries": queries,
                "images_per_query": images_per_query,
            }
        )

        return result.get("images", []) if isinstance(result, dict) else []

    async def close(self):
        """Close the connection."""
        if self.client:
            await self.client.close()
        self._initialized = False

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions for synchronous usage
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create event loop for sync contexts."""
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        try:
            _event_loop = asyncio.get_event_loop()
        except RuntimeError:
            _event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_event_loop)
    return _event_loop


def search_pinterest_sync(query: str, limit: int = 10, server_path: str = None) -> list[dict]:
    """
    Synchronous wrapper for Pinterest search.

    Use this in synchronous contexts like Agno tools.
    """
    if server_path is None:
        import os
        from pathlib import Path
        server_path = str(Path(__file__).parent.parent / "mcp_servers" / "pinterest_server.py")

    async def _search():
        async with PinterestMCPClient(server_path) as client:
            return await client.search(query, limit)

    loop = get_event_loop()
    return loop.run_until_complete(_search())
