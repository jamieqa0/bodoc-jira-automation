import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.clients.confluence import ConfluenceClient
from config.settings import settings
import json

def debug_confluence_content():
    conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    cql = 'type = page AND space.type = "global" ORDER BY lastModified DESC'
    response = conf.confluence.cql(cql, limit=1)
    
    if response.get('results'):
        page_id = response['results'][0]['content']['id']
        print(f"Fetching full content for ID: {page_id}")
        
        full = conf.confluence.get_page_by_id(page_id, expand='history')
        print(json.dumps(full, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    debug_confluence_content()
