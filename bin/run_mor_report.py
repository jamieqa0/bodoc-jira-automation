#!/usr/bin/env python3
"""
MOR Report 초안 생성 스크립트
Jira/Confluence 데이터를 수집하고 Claude API로 MOR 초안을 생성합니다.
"""

import argparse
import sys
import os
import warnings
from datetime import datetime

# urllib3 경고 억제 (quiet 모드에서만)
warnings.filterwarnings('ignore', message='.*Unverified HTTPS request.*')

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from core.mor_generator import MorGenerator
from config.settings import settings


def main():
    parser = argparse.ArgumentParser(description='MOR Report 초안 생성 및 게시')
    parser.add_argument('--month', required=True, help='년월 (예: 2026-04)')
    parser.add_argument('--user', help='사용자 이메일 (기본: 설정된 사용자)')
    parser.add_argument('--publish', action='store_true', help='생성 즉시 Confluence에 게시')
    parser.add_argument('--quiet', action='store_true', help='간단한 출력만 표시')
    args = parser.parse_args()

    user_email = args.user or settings.ATLASSIAN_USER
    year_month = args.month
    quiet = args.quiet

    # 클라이언트 초기화
    jira_client = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    confluence_client = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)

    # 데이터 수집
    if not quiet:
        print(f"Jira 데이터 수집 중... (사용자: {user_email}, 월: {year_month})")
    jira_issues = jira_client.fetch_user_issues(user_email, year_month, quiet=quiet)

    if not quiet:
        print("Confluence 데이터 수집 중...")
    confluence_pages = confluence_client.fetch_user_pages(user_email, year_month, quiet=quiet)

    # MOR 초안 생성
    if not quiet:
        print("MOR 초안 생성 중...")
    generator = MorGenerator()
    draft_content = generator.generate_draft(jira_issues, confluence_pages, user_email, year_month)

    if args.publish:
        # 바로 Confluence에 게시
        if not quiet:
            print("Confluence에 MOR 초안 게시 중...")
        import markdown
        from jinja2 import Environment, FileSystemLoader
        import os

        # Markdown → HTML 변환
        html_content = markdown.markdown(draft_content, extensions=['tables', 'fenced_code'])

        # Confluence 템플릿 적용
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'core', 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('mor_template.html')

        page_title = f"MOR 초안 - {user_email} - {year_month}"
        rendered_html = template.render(
            title=page_title,
            content=html_content,
            user=user_email,
            month=year_month,
            generated_date=settings.get_current_date()
        )

        # Confluence에 게시
        page_url = confluence_client.publish_page(
            space=settings.CONFLUENCE_SPACE_KEY,
            title=page_title,
            body=rendered_html,
            parent_id=settings.CONFLUENCE_MOR_PARENT_ID,
            quiet=quiet
        )

        if quiet:
            print("SUCCESS")
        else:
            print(f"MOR 초안이 Confluence에 게시되었습니다: {page_url}")
            print("Confluence에서 직접 편집한 후 최종 버전을 게시하세요.")
    else:
        # 파일 저장
        filename = f"mor_draft_{year_month}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(draft_content)

        if quiet:
            print("SUCCESS")
        else:
            print(f"MOR 초안이 '{filename}'에 저장되었습니다.")
            print("편집 후 'python bin/publish_mor.py --month {year_month}'로 게시하세요.")


if __name__ == '__main__':
    main()