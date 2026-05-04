#!/usr/bin/env python3
"""
MOR Report 게시 스크립트
로컬 초안을 Confluence에 게시합니다.
"""

import argparse
import sys
import os
import warnings
import markdown

# urllib3 경고 억제 (quiet 모드에서만)
warnings.filterwarnings('ignore', message='.*Unverified HTTPS request.*')

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clients.confluence import ConfluenceClient
from config.settings import settings


def main():
    parser = argparse.ArgumentParser(description='MOR Report 게시')
    parser.add_argument('--month', required=True, help='년월 (예: 2026-04)')
    parser.add_argument('--user', help='사용자 이메일 (기본: 설정된 사용자)')
    parser.add_argument('--quiet', action='store_true', help='간단한 출력만 표시')
    args = parser.parse_args()

    user_email = args.user or settings.ATLASSIAN_USER
    year_month = args.month
    quiet = args.quiet

    # 초안 파일 읽기
    filename = f"mor_draft_{year_month}.md"
    if not os.path.exists(filename):
        if quiet:
            print("ERROR: Draft file not found")
        else:
            print(f"오류: '{filename}' 파일이 존재하지 않습니다. 먼저 초안을 생성하세요.")
        sys.exit(1)

    with open(filename, 'r', encoding='utf-8') as f:
        draft_content = f.read()

    # Markdown → HTML 변환
    html_content = markdown.markdown(draft_content, extensions=['tables', 'fenced_code'])

    # Confluence 템플릿 적용
    from jinja2 import Environment, FileSystemLoader
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'core', 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('mor_template.html')

    page_title = f"MOR Report - {user_email} - {year_month}"
    rendered_html = template.render(
        title=page_title,
        content=html_content,
        user=user_email,
        month=year_month,
        generated_date=settings.get_current_date()
    )

    # Confluence에 게시
    confluence_client = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
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
        print(f"MOR Report이 Confluence에 게시되었습니다: {page_url}")


if __name__ == '__main__':
    main()