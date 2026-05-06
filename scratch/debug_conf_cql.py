import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.clients.confluence import ConfluenceClient
from config.settings import settings
import json

def debug_confluence_cql():
    conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    
    # Try a simple CQL
    cql = 'type = page AND space.type = "global" ORDER BY lastModified DESC'
    print(f"Running CQL: {cql}")
    
    response = conf.confluence.cql(cql, limit=3, expand='history')
    
    print("\n--- Raw Response (first 1 result) ---")
    if response.get('results'):
        # Check the first result structure
        first = response['results'][0]
        print(json.dumps(first, indent=2, ensure_ascii=False))
        
        c = first.get('content', {})
        print("\n--- Content fields ---")
        print(f"Content keys: {c.keys()}")
        
        hist = c.get('history', {})
        print(f"History: {hist}")
        
        # Sometimes history is at the top level of the result object, not inside content
        hist_top = first.get('history', {})
        print(f"History (top level): {hist_top}")

if __name__ == "__main__":
    debug_confluence_cql()
