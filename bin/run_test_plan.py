import os
import sys
import logging
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.clients.confluence import ConfluenceClient
from core.generators.test_plan_generator import TestPlanGenerator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    if len(sys.argv) < 2:
        logging.error("Usage: python bin/run_test_plan.py <ISSUE_KEY>")
        return

    issue_key = sys.argv[1]
    generator = TestPlanGenerator()
    confluence = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    
    html, title = generator.generate(issue_key)
    if not html:
        return
        
    result = confluence.publish_page(
        space=settings.CONFLUENCE_SPACE_KEY,
        title=title,
        body=html,
        parent_id=settings.CONFLUENCE_TEST_PLAN_PARENT_ID,
        update=True
    )
    
    if result:
        logging.info(f"성공적으로 게시되었습니다: {settings.ATLASSIAN_URL}/wiki/spaces/{settings.CONFLUENCE_SPACE_KEY}/pages/{result.get('id')}")
    else:
        logging.error("게시에 실패했습니다.")

if __name__ == "__main__":
    main()
