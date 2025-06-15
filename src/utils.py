# src/utils.py
import chromadb
import os
from typing import Dict, List

def inspect_chromadb(persist_directory: str = "data/vectorstore", collection_name: str = "salesforce_docs"):
    """Inspect ChromaDB collection for debugging"""
    try:
        client = chromadb.PersistentClient(path=persist_directory)
        
        # List all collections
        collections = client.list_collections()
        print(f"Available collections: {[c.name for c in collections]}")
        
        if not collections:
            print("No collections found!")
            return
        
        # Try to get the specific collection
        try:
            collection = client.get_collection(collection_name)
            print(f"Collection: {collection.name}")
            print(f"Document count: {collection.count()}")
            
            # Get sample documents
            if collection.count() > 0:
                results = collection.peek(limit=5)
                print("\nSample documents:")
                for i, (doc_id, metadata, document) in enumerate(zip(
                    results['ids'], 
                    results['metadatas'], 
                    results['documents']
                )):
                    print(f"{i+1}. ID: {doc_id}")
                    print(f"   Metadata: {metadata}")
                    print(f"   Content: {document[:100]}...")
            else:
                print("Collection is empty!")
                
        except Exception as e:
            print(f"Collection '{collection_name}' not found: {e}")
            
    except Exception as e:
        print(f"Error inspecting ChromaDB: {e}")

def reset_chromadb(persist_directory: str = "data/vectorstore"):
    """Reset ChromaDB collection"""
    if os.path.exists(persist_directory):
        import shutil
        shutil.rmtree(persist_directory)
        print("ChromaDB reset successfully")
    else:
        print("No existing ChromaDB found")

def check_chromadb_installation():
    """Check if ChromaDB is properly installed"""
    try:
        import chromadb
        print(f"ChromaDB version: {chromadb.__version__}")
        
        # Test creating a client
        client = chromadb.Client()
        print("ChromaDB client created successfully")
        
        # Test creating a collection
        collection = client.create_collection("test")
        print("Test collection created successfully")
        
        return True
    except Exception as e:
        print(f"ChromaDB installation issue: {e}")
        return False