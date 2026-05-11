#!/usr/bin/env python3
"""
MOR Report 초안 생성 스크립트
Jira/Confluence 데이터를 수집하고 Claude API로 MOR 초안을 생성합니다.
"""

import argparse
import sys
import os
import warnings

# urllib3 경고 억제 (quiet 모드에서만)
warnings.filterwarnings('ignore', message='.*Unverified HTTPS request.*')

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from core.generators.mor_report_generator import MorGenerator
from config.settings import settings


def publish_to_confluence(confluence_client, content, user_email, year_month, display_name, quiet=False):
    """콘플루언스에 게시하는 공통 로직"""
    import markdown
    from jinja2 import Environment, FileSystemLoader
    import os

    # Markdown → HTML 변환
    html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])

    # Confluence 템플릿 적용
    env = Environment(loader=FileSystemLoader(str(settings.TEMPLATE_DIR)))
    template = env.get_template('mor_report.html')

    # 타이틀 형식 변경: MOR 초안 2025-09 - jamie
    page_title = f"MOR 초안 {year_month} - {display_name}"
    
    rendered_html = template.render(
        title=page_title,
        content=html_content,
        user=display_name,
        month=year_month,
        generated_date=settings.get_current_date()
    )

    # Confluence에 게시
    result = confluence_client.publish_page(
        space=settings.CONFLUENCE_SPACE_KEY,
        title=page_title,
        body=rendered_html,
        parent_id=settings.CONFLUENCE_MOR_PARENT_ID,
        quiet=quiet
    )
    
    if result and '_links' in result and 'webui' in result['_links']:
        return f"{settings.ATLASSIAN_URL.rstrip('/')}/wiki{result['_links']['webui']}"
    elif result and 'id' in result:
        return f"{settings.ATLASSIAN_URL.rstrip('/')}/wiki/pages/viewpage.action?pageId={result['id']}"
    
    return str(result)


def main():
    parser = argparse.ArgumentParser(description='MOR Report 생성 및 게시')
    parser.add_argument('--month', required=True, help='년월 (예: 2026-04)')
    parser.add_argument('--user', help='사용자 이메일 (기본: 설정된 사용자)')
    parser.add_argument('--publish', action='store_true', help='Confluence에 바로 게시')
    parser.add_argument('--draft', help='이미 작성된 마크다운 초안 파일 경로 (제공 시 생성 단계 건너뜀)')
    parser.add_argument('--quiet', action='store_true', help='간단한 출력만 표시')
    args = parser.parse_args()

    user_email = args.user or settings.ATLASSIAN_USER
    year_month = args.month
    quiet = args.quiet

    confluence_client = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    
    # 사용자 이름 조회를 위해 정보 가져오기
    user_info = confluence_client.get_user_info(user_email)
    display_name = user_info.get('displayName', user_email.split('@')[0])

    if args.draft:
        # 파일에서 읽기
        if not os.path.exists(args.draft):
            if quiet: print("ERROR: Draft file not found"); sys.exit(1)
            print(f"오류: '{args.draft}' 파일이 존재하지 않습니다."); sys.exit(1)
        
        with open(args.draft, 'r', encoding='utf-8') as f:
            content = f.read()
        if not quiet: print(f"'{args.draft}' 파일로부터 내용을 읽었습니다.")
    else:
        # 데이터 수집 및 생성
        jira_client = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        if not quiet: print(f"Jira 데이터 수집 중... (사용자: {display_name}, 월: {year_month})")
        jira_issues = jira_client.fetch_user_issues(user_email, year_month, quiet=quiet)

        if not quiet: print("Confluence 데이터 수집 중...")
        confluence_pages = confluence_client.fetch_user_pages(user_email, year_month, quiet=quiet)

        if not quiet: print("MOR 초안 생성 중...")
        generator = MorGenerator()
        content = generator.generate_draft(jira_issues, confluence_pages, user_email, year_month)

    if args.publish:
        if not quiet: print("Confluence에 게시 중...")
        try:
            page_url = publish_to_confluence(confluence_client, content, user_email, year_month, display_name, quiet)
            if quiet:
                print("SUCCESS")
            else:
                print(f"성공적으로 게시되었습니다: {page_url}")
        except Exception as e:
            if quiet: print(f"ERROR: {str(e)}")
            else: print(f"게시 중 오류 발생: {e}")
            sys.exit(1)
    else:
        # 파일 저장
        filename = f"mor_draft_{year_month}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        if quiet:
            print("SUCCESS")
        else:
            print(f"내용이 '{filename}'에 저장되었습니다.")
            print(f"수정 후 'python bin/run_mor_report.py --month {year_month} --draft {filename} --publish' 명령어로 게시하세요.")


if __name__ == '__main__':
    main()