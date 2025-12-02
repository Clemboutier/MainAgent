"""
Client utilities for connecting to MCP servers using the official MCP library.
Supports multiple MCP servers (Apify Weather and Langfuse).
"""

import asyncio
import os
import traceback
from typing import List, Dict, Any
from mcp import ClientSession
from mcp.client.sse import sse_client

# Configuration for multiple MCP servers
MCP_SERVERS = {
    "weather": {
        "url": "https://jiri-spilka--weather-mcp-server.apify.actor/mcp",
        "auth_header": lambda: f"Bearer {os.getenv('APIFY_API_TOKEN', '')}",
        "enabled": lambda: bool(os.getenv('APIFY_API_TOKEN'))
    },
    "langfuse": {
        "url": f"{os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}/api/public/mcp",
        "auth_header": lambda: f"Bearer {os.getenv('LANGFUSE_PUBLIC_KEY', '')}:{os.getenv('LANGFUSE_SECRET_KEY', '')}",
        "enabled": lambda: bool(os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY'))
    }
}

async def _get_tools_from_server(server_name: str, server_config: dict) -> List[Dict[str, Any]]:
    """Get tools from a specific MCP server."""
    if not server_config["enabled"]():
        return []
    
    headers = {}
    auth_header = server_config["auth_header"]()
    if auth_header and auth_header != "Bearer ":
        headers["Authorization"] = auth_header
    
    try:
        async with sse_client(server_config["url"], headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                # Convert Tool objects to dicts and add server info
                return [
                    {
                        "name": f"{server_name}_{tool.name}",  # Prefix with server name
                        "description": f"[{server_name.upper()}] {tool.description}",
                        "inputSchema": tool.inputSchema,
                        "_server": server_name,
                        "_original_name": tool.name
                    }
                    for tool in result.tools
                ]
    except Exception as e:
        print(f"Error fetching tools from {server_name}: {e}")
        return []

async def _get_tools_async() -> List[Dict[str, Any]]:
    """Async implementation to get tools from all enabled MCP servers."""
    all_tools = []
    
    for server_name, server_config in MCP_SERVERS.items():
        tools = await _get_tools_from_server(server_name, server_config)
        all_tools.extend(tools)
    
    return all_tools

async def _call_tool_async(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Async implementation to call a tool on the appropriate MCP server."""
    # Extract server name from tool name (format: servername_toolname)
    if "_" not in tool_name:
        return f"Error: Invalid tool name format: {tool_name}"
    
    server_name, original_tool_name = tool_name.split("_", 1)
    
    if server_name not in MCP_SERVERS:
        return f"Error: Unknown server: {server_name}"
    
    server_config = MCP_SERVERS[server_name]
    
    if not server_config["enabled"]():
        return f"Error: Server {server_name} is not configured (missing credentials)"
    
    headers = {}
    auth_header = server_config["auth_header"]()
    if auth_header and auth_header != "Bearer ":
        headers["Authorization"] = auth_header
    
    try:
        async with sse_client(server_config["url"], headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(original_tool_name, arguments)
                # Extract text content from result
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return str(result)
    except Exception as e:
        print(f"Error calling tool {tool_name} on {server_name}: {e}")
        traceback.print_exc()
        return f"Error executing tool {tool_name}: {e}"

def get_tools() -> List[Dict[str, Any]]:
    """Get available tools from all enabled MCP servers."""
    try:
        return asyncio.run(_get_tools_async())
    except Exception as e:
        print(f"Error fetching tools: {e}")
        return []

def call_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Call a tool on the appropriate MCP server."""
    try:
        return asyncio.run(_call_tool_async(tool_name, arguments))
    except Exception as e:
        return f"Error executing tool {tool_name}: {e}"
