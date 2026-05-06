import logging
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from core.utils import get_today_str, extract_project_name, extract_version
import os

class TestPlanGenerator:
    def __init__(self, jira_client=None, confluence_client=None):
        self.jira = jira_client or JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        self.confluence = confluence_client or ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        self.jinja_env = Environment(loader=FileSystemLoader(str(settings.TEMPLATE_DIR)))

    def create_test_plan_html(self, task_info):
        """테스트 플랜 HTML 양식을 생성합니다."""
        template_name = 'test_plan.html'
        template = self.jinja_env.get_template(template_name)
        render_data = {
            'report_title': f"Test Plan: {task_info['summary']}",
            'summary': task_info['summary'],
            'project_name': extract_project_name(task_info['summary']),
            'version': extract_version(task_info['summary']),
            'reporter': task_info['reporter'],
            'key': task_info['key'],
            'today': get_today_str(),
            'prd_url': task_info.get('prd_url') or "링크 필요",
            'dev_doc_urls': task_info.get('dev_doc_urls') or [],
            'jira_url': settings.ATLASSIAN_URL
        }
        return template.render(render_data)

    def generate(self, issue_key):
        logging.info(f"테스트 플랜 생성 시작: {issue_key}")
        
        task_info = self.jira.get_issue_info(issue_key)
        if not task_info:
            logging.error("이슈 정보를 찾을 수 없습니다.")
            return None, None

        html_content = self.create_test_plan_html(task_info)
        page_title = f"Test Plan: {task_info['summary']}"
        return html_content, page_title
