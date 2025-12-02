"""
Verification script for MCP integration with multiple servers.
Tests: Apify Weather Server and Langfuse MCP Server
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from agent.mcp_client import get_tools, call_tool

def main():
    print("🔍 Testing MCP Integration with Multiple Servers...")
    print("=" * 70)
    
    # Check which servers are configured
    has_apify = bool(os.getenv("APIFY_API_TOKEN"))
    has_langfuse = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
    
    print("\n📋 Server Configuration Status:")
    print(f"  🌤️  Apify Weather: {'✅ Configured' if has_apify else '❌ Not configured (APIFY_API_TOKEN missing)'}")
    print(f"  📊 Langfuse:      {'✅ Configured' if has_langfuse else '❌ Not configured (LANGFUSE keys missing)'}")
    
    if not has_apify and not has_langfuse:
        print("\n⚠️  No MCP servers configured!")
        print("\n💡 To configure servers, add to your .env file:")
        print("\n   For Apify Weather:")
        print("   APIFY_API_TOKEN=your_token")
        print("   Get token from: https://console.apify.com/account/integrations")
        print("\n   For Langfuse:")
        print("   LANGFUSE_HOST=https://cloud.langfuse.com")
        print("   LANGFUSE_PUBLIC_KEY=pk-lf-...")
        print("   LANGFUSE_SECRET_KEY=sk-lf-...")
        print("   Get keys from: https://cloud.langfuse.com")
        return
    
    # 1. Test Listing Tools
    print("\n" + "=" * 70)
    print("1. Discovering Available Tools from All Servers")
    print("=" * 70)
    tools = get_tools()
    
    if not tools:
        print("❌ No tools found!")
        return
    
    # Categorize tools by server
    weather_tools = [t for t in tools if t.get("_server") == "weather"]
    langfuse_tools = [t for t in tools if t.get("_server") == "langfuse"]
    
    if weather_tools:
        print(f"\n🌤️  Apify Weather Tools ({len(weather_tools)} found):")
        for tool in weather_tools:
            print(f"  ✓ {tool['name']}")
            print(f"    {tool['description']}")
    
    if langfuse_tools:
        print(f"\n📊 Langfuse Tools ({len(langfuse_tools)} found):")
        for tool in langfuse_tools:
            print(f"  ✓ {tool['name']}")
            print(f"    {tool['description']}")
    
    # 2. Test Weather Tools (if available)
    if weather_tools and has_apify:
        print("\n" + "=" * 70)
        print("2. Testing Apify Weather Server")
        print("=" * 70)
        
        # Test get_weather
        print("\n📍 Test: weather_get_weather(city='Paris')")
        result = call_tool("weather_get_weather", {"city": "Paris"})
        if len(result) > 150:
            print(f"  Result: {result[:150]}...")
        else:
            print(f"  Result: {result}")
        
        if "Error" not in str(result):
            print("  ✅ weather_get_weather working!")
        else:
            print("  ❌ weather_get_weather failed!")
        
        # Test get_current_datetime
        print("\n🕐 Test: weather_get_current_datetime(timezone='Europe/Paris')")
        result = call_tool("weather_get_current_datetime", {"timezone": "Europe/Paris"})
        print(f"  Result: {result}")
        
        if "Error" not in str(result):
            print("  ✅ weather_get_current_datetime working!")
        else:
            print("  ❌ weather_get_current_datetime failed!")
    
    # 3. Test Langfuse Tools (if available)
    if langfuse_tools and has_langfuse:
        print("\n" + "=" * 70)
        print("3. Testing Langfuse MCP Server")
        print("=" * 70)
        
        # Try to find and test a list prompts tool
        list_tool = next((t for t in langfuse_tools if "list" in t["_original_name"].lower() and "prompt" in t["_original_name"].lower()), None)
        
        if list_tool:
            print(f"\n📋 Test: {list_tool['name']}()")
            result = call_tool(list_tool['name'], {})
            if len(result) > 200:
                print(f"  Result: {result[:200]}...")
            else:
                print(f"  Result: {result}")
            
            if "Error" not in str(result):
                print(f"  ✅ {list_tool['name']} working!")
            else:
                print(f"  ❌ {list_tool['name']} failed!")
        else:
            print("\n  ℹ️  No 'list prompts' tool found, trying first available tool...")
            if langfuse_tools:
                first_tool = langfuse_tools[0]
                print(f"\n🧪 Test: {first_tool['name']}()")
                # Try calling with empty args
                result = call_tool(first_tool['name'], {})
                if len(result) > 200:
                    print(f"  Result: {result[:200]}...")
                else:
                    print(f"  Result: {result}")
                
                if "Error" not in str(result):
                    print(f"  ✅ {first_tool['name']} working!")
                else:
                    print(f"  ❌ {first_tool['name']} failed!")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Verification Complete!")
    print("=" * 70)
    print(f"\nServers tested: {sum([has_apify, has_langfuse])}/2")
    print(f"Total tools available: {len(tools)}")
    
    if not has_apify:
        print("\n💡 Tip: Add APIFY_API_TOKEN to enable weather tools")
    if not has_langfuse:
        print("💡 Tip: Add LANGFUSE keys to enable prompt management tools")

if __name__ == "__main__":
    main()
