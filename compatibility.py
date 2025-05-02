"""
Compatibility module for handling SQLite version requirements in ChromaDB.
This file should be imported before any other modules to ensure proper SQLite version handling.
"""
import sys
import importlib.util
import os

def enable_sqlite_compatibility():
    """
    Enable SQLite compatibility for ChromaDB by attempting to use pysqlite3.
    
    This function tries to:
    1. Check if pysqlite3 is available
    2. If available, replace sqlite3 with pysqlite3 in sys.modules
    3. If not available, print a warning but allow the program to continue
       (may fail later if ChromaDB is actually used)
    
    Returns:
        bool: True if compatibility was enabled, False otherwise
    """
    try:
        # Check if pysqlite3 package is available
        if importlib.util.find_spec("pysqlite3") is not None:
            # Replace sqlite3 with pysqlite3
            __import__('pysqlite3')
            sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
            print("✅ SQLite compatibility enabled for ChromaDB")
            return True
        else:
            # Package not installed, we need to inform the user
            print("\n⚠️ pysqlite3-binary package not found.")
            print("ChromaDB requires SQLite >= 3.35.0")
            print("To enable full memory features, install: pip install pysqlite3-binary\n")
            
            # Set env variable to indicate limited functionality
            os.environ["KARO_MEMORY_DISABLED"] = "1"
            return False
    except Exception as e:
        print(f"\n⚠️ Error enabling SQLite compatibility: {e}")
        print("Some memory features may not work correctly.\n")
        
        # Set env variable to indicate limited functionality
        os.environ["KARO_MEMORY_DISABLED"] = "1"
        return False

# Auto-execute when module is imported
enable_sqlite_compatibility()