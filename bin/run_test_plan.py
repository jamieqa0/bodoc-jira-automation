import os
import sys
import logging
import urllib3
from jinja2 import Environment, FileSystemLoader

# 프로젝트 루트를 sys.path에 추가 (상위 폴더의 모듈을 불러오기 위함)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from core.utils import get_today_str

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestPlanReporter:
    def __init__(self):
        self.jira = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        self.confluence = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        
        # 템플릿 환경 설정
        self.jinja_env = Environment(loader=FileSystemLoader(str(settings.TEMPLATE_DIR)))

    def create_test_plan_html(self, task_info):
        """테스트 플랜 HTML 양식을 생성합니다."""
        from core.utils import extract_project_name, extract_version
        
        template = self.jinja_env.get_template('test_plan_template.html')
        render_data = {
            'report_title': f"Test Plan: {task_info['summary']}",
            'summary': task_info['summary'],
            'project_name': extract_project_name(task_info['summary']),
            'version': extract_version(task_info['summary']),
            'reporter': task_info['reporter'],
            'key': task_info['key'],
            'today': get_today_str(),
            'prd_url': task_info.get('prd_url') or "링크 필요",
            'jira_url': settings.ATLASSIAN_URL
        }
        return template.render(render_data)

    def run(self, issue_key):
        logging.info(f"테스트 플랜 생성을 시작합니다: {issue_key}")
        
        task_info = self.jira.get_issue_info(issue_key)
        if not task_info:
            logging.error("이슈 정보를 찾을 수 없어 중단합니다.")
            return

        html_content = self.create_test_plan_html(task_info)
        
        page_title = f"Test Plan: {task_info['summary']}"
        result = self.confluence.publish_page(
            space=settings.CONFLUENCE_SPACE_KEY,
            title=page_title,
            body=html_content,
            parent_id=settings.CONFLUENCE_TEST_PLAN_PARENT_ID
        )
        
        if result:
            logging.info(f"성공적으로 게시되었습니다: {settings.ATLASSIAN_URL}/wiki/spaces/{settings.CONFLUENCE_SPACE_KEY}/pages/{result.get('id')}")
        else:
            logging.error("게시에 실패했습니다.")

if __name__ == "__main__":
    issue_key = sys.argv[1] if len(sys.argv) > 1 else "SQA-122"
    reporter = TestPlanReporter()
    reporter.run(issue_key)

