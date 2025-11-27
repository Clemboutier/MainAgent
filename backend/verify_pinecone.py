#!/usr/bin/env python3
"""
Quick verification script to test Pinecone integration.
This script checks if the RAGStore can be initialized properly.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_vars():
    """Check if required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
    }
    
    optional_vars = {
        "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME", "mainagent-rag"),
        "PINECONE_DIMENSION": os.getenv("PINECONE_DIMENSION", "1536"),
        "PINECONE_CLOUD": os.getenv("PINECONE_CLOUD", "aws"),
        "PINECONE_REGION": os.getenv("PINECONE_REGION", "us-east-1"),
    }
    
    all_good = True
    for var, value in required_vars.items():
        if value:
            print(f"  ✅ {var}: {'*' * 10} (set)")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_good = False
    
    print("\n📋 Optional variables (using defaults if not set):")
    for var, value in optional_vars.items():
        print(f"  ℹ️  {var}: {value}")
    
    return all_good

def test_imports():
    """Test if all imports work."""
    print("\n📦 Testing imports...")
    
    try:
        from pinecone import Pinecone, ServerlessSpec
        print("  ✅ Pinecone imports successful")
    except ImportError as e:
        print(f"  ❌ Pinecone import failed: {e}")
        return False
    
    try:
        from agent.utils import RAGStore, get_rag_store
        print("  ✅ RAGStore imports successful")
    except ImportError as e:
        print(f"  ❌ RAGStore import failed: {e}")
        return False
    
    return True

def test_rag_store_init():
    """Test if RAGStore can be initialized."""
    print("\n🔌 Testing RAGStore initialization...")
    
    if not os.getenv("PINECONE_API_KEY"):
        print("  ⚠️  Skipping (PINECONE_API_KEY not set)")
        return None
    
    try:
        from agent.utils import get_rag_store
        store = get_rag_store()
        print(f"  ✅ RAGStore initialized successfully")
        print(f"  📊 Index name: {store.index_name}")
        return True
    except Exception as e:
        print(f"  ❌ RAGStore initialization failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 Pinecone Migration Verification Script")
    print("=" * 60)
    
    # Check environment variables
    env_ok = check_env_vars()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test RAGStore initialization
    if env_ok and imports_ok:
        store_ok = test_rag_store_init()
    else:
        store_ok = None
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if env_ok and imports_ok and store_ok:
        print("✅ All checks passed! Your Pinecone migration is ready.")
        print("\n📝 Next steps:")
        print("  1. Run: python -m scripts.build_index")
        print("  2. Run: uvicorn main:app --reload")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the errors above.")
        if not env_ok:
            print("\n💡 Tip: Copy .env.example to .env and add your API keys")
        return 1

if __name__ == "__main__":
    sys.exit(main())
