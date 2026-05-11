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
from core.utils import RESOLVED_STATUSES
from config.settings import settings

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
    if account_id == user_email:
        if not quiet:
            print("  Confluence 사용자 조회 실패, Jira를 통해 accountId 재시도...")
        jira_id = jira.get_user_account_id(user_email)
        if jira_id:
            account_id = jira_id
            user_info['accountId'] = jira_id
            if not quiet:
                print(f"  accountId: {jira_id} [OK via Jira]")
        else:
            if not quiet:
                print(f"  [경고] accountId 조회 실패 — Confluence 문서 수집이 0건일 수 있습니다.")
    elif not quiet:
        print(f"  accountId: {account_id} [OK]")

    # ── Jira 이슈 수집 ────────────────────────────────────────────
    if not quiet:
        print(f"Jira 이슈 수집 중... ({start_date} ~ {end_date})")
    jql_all = (
        f'(project = "SQA" OR '
        f'(issuetype = Defect AND (assignee = "{user_email}" OR reporter = "{user_email}"))) '
        f'AND created >= "{start_date}" AND created <= "{end_date}" ORDER BY created ASC'
    )
    raw = jira.jira.search_issues(
        jql_all, maxResults=0,
        fields='key,summary,status,issuetype,priority,created,resolutiondate,project,fixVersions,assignee'
    )

    sqa_issues, defect_issues = [], []
    for iss in raw:
        # 프로젝트 명 세분화 및 통합 (최종 2개 카테고리: Bodoc 4.0, Planner & B2B)
        raw_project_name = iss.fields.project.name
        project_key = iss.fields.project.key
        
        if project_key == 'APTS':
            # Product Team Sprint (APTS)는 키워드/버전으로 분류
            versions = [v.name.lower() for v in getattr(iss.fields, 'fixVersions', [])]
            version_str = " ".join(versions)
            summary_lower = iss.fields.summary.lower()
            _PLANNER_KW = ('플래너', 'planner')
            _BODOC_KW = ('보닥', 'bodoc', 'android', 'ios', 'ai 상담사')
            if any(kw in version_str or kw in summary_lower for kw in _PLANNER_KW):
                project_name = "Planner & B2B"
            elif any(kw in version_str or kw in summary_lower for kw in _BODOC_KW):
                project_name = "Bodoc 4.0"
            else:
                project_name = "Planner & B2B"
        elif project_key == 'BODOCRUN':
            project_name = "Bodoc 4.0"
        elif project_key in ('PLN3', 'BDPLNPD'):
            project_name = "Planner & B2B"
        else:
            # 그 외 프로젝트들 처리 (필요시 추가)
            if '보닥' in raw_project_name or 'Bodoc' in raw_project_name:
                project_name = "Bodoc 4.0"
            else:
                project_name = "Planner & B2B"

        assignee_email = getattr(iss.fields.assignee, 'emailAddress', None) if iss.fields.assignee else None
        d = {
            'key':          iss.key,
            'summary':      iss.fields.summary,
            'status':       iss.fields.status.name,
            'issuetype':    iss.fields.issuetype.name,
            'priority':     iss.fields.priority.name if iss.fields.priority else 'None',
            'project_name': project_name,
            'month':        str(iss.fields.created)[:7],
            'resolved':     is_resolved(iss),
            'is_main':      assignee_email == user_email,
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
    for p in conf.confluence.cql(cql, limit=100, expand='content.history').get('results', []):
        c = p.get('content', {})
        hist = c.get('history', {})
        pages.append({
            'id':           c.get('id', ''),
            'title':        c.get('title', ''),
            'space':        c.get('space', {}).get('name', ''),
            'url':          f"{base_url}/wiki{c.get('_links', {}).get('webui', '')}",
            'created':      hist.get('createdDate', '')[:10],
            'lastModified': hist.get('lastUpdated', {}).get('when', '')[:10] if isinstance(hist.get('lastUpdated'), dict) else '',
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
