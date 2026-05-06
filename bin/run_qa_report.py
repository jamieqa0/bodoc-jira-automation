import os
import sys
import logging
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.clients.confluence import ConfluenceClient
from core.generators.qa_report_generator import QAReportGenerator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    if len(sys.argv) < 2:
        logging.error("Usage: python bin/run_qa_report.py <QA_TASK_KEY>")
        return

    qa_key = sys.argv[1]
    generator = QAReportGenerator()
    confluence = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    
    result = generator.generate(qa_key)
    if not result:
        return
        
    html, charts, summary = result
    
    page_title = f"{summary} Report"
    page = confluence.publish_page(
        settings.CONFLUENCE_SPACE_KEY,
        page_title,
        html,
        settings.CONFLUENCE_QA_REPORT_PARENT_ID,
        update=True
    )
    
    if page:
        for name, data in charts.items():
            confluence.attach_file(page.get('id'), name, data)
        logging.info(f"게시 완료: {settings.ATLASSIAN_URL}/wiki/pages/{page.get('id')}")

if __name__ == "__main__":
    main()
