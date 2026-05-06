import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.clients.confluence import ConfluenceClient
from config.settings import settings
import json

def debug_confluence_cql():
    conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    cql = 'type = page AND space.type = "global" ORDER BY lastModified DESC'
    response = conf.confluence.cql(cql, limit=1)
    
    if response.get('results'):
        first = response['results'][0]
        print("Top-level keys in CQL result:")
        print(first.keys())
        
        # Check if history is inside content
        c = first.get('content', {})
        print("\nContent keys:")
        print(c.keys())
        
        # Look for date fields
        for k, v in first.items():
            if 'date' in k.lower() or 'time' in k.lower() or 'modified' in k.lower():
                print(f"Found date field at top level: {k} = {v}")

if __name__ == "__main__":
    debug_confluence_cql()
