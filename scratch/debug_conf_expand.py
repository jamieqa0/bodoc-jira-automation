import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.clients.confluence import ConfluenceClient
from config.settings import settings
import json

def debug_confluence_cql_expand():
    conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    cql = 'type = page AND space.type = "global" ORDER BY lastModified DESC'
    
    # Try different expand patterns
    patterns = ['history', 'content.history']
    
    for p in patterns:
        print(f"\n--- Testing expand='{p}' ---")
        response = conf.confluence.cql(cql, limit=1, expand=p)
        if response.get('results'):
            res = response['results'][0]
            print(f"Top level keys: {res.keys()}")
            c = res.get('content', {})
            print(f"Content keys: {c.keys()}")
            if 'history' in c:
                print("SUCCESS: history found in content!")
            if 'history' in res:
                print("SUCCESS: history found at top level!")

if __name__ == "__main__":
    debug_confluence_cql_expand()
