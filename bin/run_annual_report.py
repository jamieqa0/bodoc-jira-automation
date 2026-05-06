#!/usr/bin/env python3
"""
연간 업무 성과 보고서 생성 스크립트
Jira 이슈(작업관리/결함 분리)와 Confluence 문서를 수집해 연간 보고서를 게시합니다.

Usage:
    python bin/run_annual_report.py --year 2025
    python bin/run_annual_report.py --year 2026 --user jamie@aijinet.com
    python bin/run_annual_report.py --year 2025 --quiet
"""

import argparse
import sys
import os
import re
import urllib.parse
import calendar
import warnings
from collections import Counter
from datetime import date

warnings.filterwarnings('ignore', message='.*Unverified HTTPS request.*')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.generators.annual_report_generator import AnnualGenerator
from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from config.settings import settings

RESOLVED_STATUSES = {
    'Prod 배포완료', '종료', 'Resolved', 'Closed', 'Done',
    'Verified', '해결됨', '완료', '종료됨',
}

def is_resolved(iss):
    return (
        getattr(iss.fields, 'resolutiondate', None) is not None
        or iss.fields.status.name in RESOLVED_STATUSES
    )

def main():
    parser = argparse.ArgumentParser(description='연간 업무 성과 보고서 생성 및 Confluence 게시')
    parser.add_argument('--year', type=int, default=date.today().year, help='대상 연도 (기본: 현재 연도)')
    parser.add_argument('--user', default=None, help='사용자 이메일 (기본: 설정된 사용자)')
    parser.add_argument('--quiet', action='store_true', help='간단한 출력만 표시')
    args = parser.parse_args()

    user_email = args.user or settings.ATLASSIAN_USER
    year = args.year
    quiet = args.quiet
    today = date.today()
    base_url = settings.ATLASSIAN_URL.rstrip('/')

    start_date = f"{year}-01-01"
    end_date   = f"{year}-12-31" if year < today.year else today.strftime('%Y-%m-%d')
    is_current_year = (year == today.year)

    # ── 클라이언트 초기화 ─────────────────────────────────────────
    jira = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    generator = AnnualGenerator()

    # ── 사용자 정보 ───────────────────────────────────────────────
    if not quiet:
        print(f"사용자 정보 조회 중... ({user_email})")
    user_info = conf.get_user_info(user_email)
    user_info['email'] = user_email
    account_id = user_info['accountId']

    # ── Jira 이슈 수집 ────────────────────────────────────────────
    if not quiet:
        print(f"Jira 이슈 수집 중... ({start_date} ~ {end_date})")
    jql_all = (
        f'((assignee = "{user_email}" OR reporter = "{user_email}") OR project = "SQA") '
        f'AND created >= "{start_date}" AND created <= "{end_date}" ORDER BY created ASC'
    )
    raw = jira.jira.search_issues(
        jql_all, maxResults=0,
        fields='key,summary,status,issuetype,priority,created,resolutiondate,project'
    )

    sqa_issues, defect_issues = [], []
    for iss in raw:
        d = {
            'key':          iss.key,
            'summary':      iss.fields.summary,
            'status':       iss.fields.status.name,
            'issuetype':    iss.fields.issuetype.name,
            'priority':     iss.fields.priority.name if iss.fields.priority else 'None',
            'project_name': iss.fields.project.name,
            'month':        str(iss.fields.created)[:7],
            'resolved':     is_resolved(iss),
        }
        if re.search(r'amplitude', iss.fields.summary, re.IGNORECASE):
            d['amplitude'] = True
        (sqa_issues if iss.fields.project.key == 'SQA' else defect_issues).append(d)

    if not quiet:
        print(f"  SQA(작업관리): {len(sqa_issues)}개 / 결함: {len(defect_issues)}개")

    # ── Confluence 페이지 수집 ────────────────────────────────────
    if not quiet:
        print("Confluence 페이지 수집 중...")
    cql = (
        f'type = page AND space.type = "global" '
        f'AND (creator = "{account_id}" OR lastModifier = "{account_id}") '
        f'AND (created >= "{start_date}" OR lastModified >= "{start_date}") '
        f'AND (created <= "{end_date}" OR lastModified <= "{end_date}") '
        f'ORDER BY lastModified DESC'
    )
    pages = []
    for p in conf.confluence.cql(cql, limit=100).get('results', []):
        c = p.get('content', {})
        hist = c.get('history', {})
        last_mod = hist.get('lastModified', {})
        pages.append({
            'id':           c.get('id', ''),
            'title':        c.get('title', ''),
            'space':        {'key': c.get('space', {}).get('key', ''), 'name': c.get('space', {}).get('name', '')},
            'url':          f"{base_url}/wiki{c.get('_links', {}).get('webui', '')}",
            'created':      hist.get('createdDate', '')[:10],
            'lastModified': last_mod.get('when', '')[:10] if isinstance(last_mod, dict) else '',
        })
    if not quiet:
        print(f"  Confluence 페이지: {len(pages)}개")

    # ── 보고서 생성 및 게시 ───────────────────────────────────────
    if not quiet:
        print("보고서 생성 중...")
    
    title, full_body = generator.generate_html(
        sqa_issues, defect_issues, pages, user_info, 
        year, start_date, end_date, is_current_year
    )

    if not quiet:
        print(f"Confluence 게시 중: '{title}'")

    result = conf.publish_page(
        space=settings.CONFLUENCE_SPACE_KEY,
        title=title,
        body=full_body,
        parent_id=settings.CONFLUENCE_MOR_PARENT_ID,
    )

    if result and result.get('id'):
        page_id = result['id']
        url = f"{base_url}/wiki/spaces/{settings.CONFLUENCE_SPACE_KEY}/pages/{page_id}"
        print(f"SUCCESS: {url}")
    else:
        print("ERROR: 게시 실패")
        sys.exit(1)

if __name__ == '__main__':
    main()
