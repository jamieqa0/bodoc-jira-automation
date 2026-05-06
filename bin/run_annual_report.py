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

from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from config.settings import settings

RESOLVED_STATUSES = {
    'Prod 배포완료', '종료', 'Resolved', 'Closed', 'Done',
    'Verified', '해결됨', '완료', '종료됨',
}
PRIORITY_ORDER = ['Highest', 'High', 'Medium', 'Low', 'Lowest', 'None']


# ── HTML 헬퍼 ─────────────────────────────────────────────────────

def jql_url(base_url, jql):
    return f"{base_url}/issues/?jql={urllib.parse.quote(jql)}"

def linked(text, url):
    return f"<a href='{url}'>{text}</a>"

def center(v):
    return f"<td style='text-align:center'>{v}</td>"

def table(headers, rows_html):
    th = "".join(f"<th>{h}</th>" for h in headers)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table>"

def ov_table(rows_html):
    return (
        "<table><colgroup><col style='width:240px'/><col/></colgroup>"
        f"<tbody>{rows_html}</tbody></table>"
    )


# ── 분석 헬퍼 ─────────────────────────────────────────────────────

def is_resolved(iss):
    return (
        getattr(iss.fields, 'resolutiondate', None) is not None
        or iss.fields.status.name in RESOLVED_STATUSES
    )

def months_in_range(start_date, end_date):
    """start_date ~ end_date 범위의 YYYY-MM 목록 반환"""
    y1, m1 = int(start_date[:4]), int(start_date[5:7])
    y2, m2 = int(end_date[:4]),   int(end_date[5:7])
    result = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        result.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return result

def month_label(month_str):
    return f"{int(month_str[5:7])}월"

def month_end(month_str, end_date):
    y, m = map(int, month_str.split('-'))
    last = calendar.monthrange(y, m)[1]
    if month_str == end_date[:7]:
        last = int(end_date[8:])
    return f"{month_str}-{last:02d}"

def build_status_rows(cnt, base_jql, base_url):
    return "".join(
        "<tr><td>{}</td>{}</tr>".format(
            s, center(linked(str(c), jql_url(base_url, f'{base_jql} AND status = "{s}"')))
        )
        for s, c in sorted(cnt.items(), key=lambda x: -x[1])
    )

def build_monthly_rows(cnt, base_jql, base_url, months, end_date):
    return "".join(
        "<tr><td><strong>{}</strong></td>{}</tr>".format(
            month_label(m),
            center(linked(
                str(cnt.get(m, 0)),
                jql_url(base_url, f'{base_jql} AND created >= "{m}-01" AND created <= "{month_end(m, end_date)}"')
            ))
        )
        for m in months if cnt.get(m, 0) > 0
    )


# ── 메인 ─────────────────────────────────────────────────────────

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
    months     = months_in_range(start_date, end_date)
    is_current_year = (year == today.year)

    # ── 클라이언트 초기화 ─────────────────────────────────────────
    jira = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)

    # ── 사용자 정보 ───────────────────────────────────────────────
    if not quiet:
        print(f"사용자 정보 조회 중... ({user_email})")
    user_info   = conf.get_user_info(user_email)
    account_id  = user_info['accountId']
    display_name = user_info['displayName']

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
            'status':       iss.fields.status.name,
            'issuetype':    iss.fields.issuetype.name,
            'priority':     iss.fields.priority.name if iss.fields.priority else 'None',
            'project_name': iss.fields.project.name,
            'month':        str(iss.fields.created)[:7],
            'resolved':     is_resolved(iss),
        }
        if re.search(r'\[amplitude\]', iss.fields.summary, re.IGNORECASE):
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
        c    = p.get('content', {})
        hist = c.get('history', {})
        last_mod = hist.get('lastModified', {})
        pages.append({
            'title':        c.get('title', ''),
            'url':          f"{base_url}{c.get('_links', {}).get('webui', '')}",
            'created':      hist.get('createdDate', '')[:10],
            'lastModified': last_mod.get('when', '')[:10] if isinstance(last_mod, dict) else '',
        })
    if not quiet:
        print(f"  Confluence 페이지: {len(pages)}개")

    # ── 분석 ─────────────────────────────────────────────────────
    BASE_DATE    = f'AND created >= "{start_date}" AND created <= "{end_date}"'
    JQL_SQA = f'project = "SQA" {BASE_DATE}'
    JQL_DEF = (
        f'(assignee = "{user_email}" OR reporter = "{user_email}") '
        f'AND project != "SQA" {BASE_DATE}'
    )

    # SQA
    sqa_type    = Counter(i['issuetype'] for i in sqa_issues)
    sqa_status  = Counter(i['status']    for i in sqa_issues)
    sqa_monthly = Counter(i['month']     for i in sqa_issues)
    sqa_resolved = sum(1 for i in sqa_issues if i['resolved'])
    sqa_rate    = sqa_resolved / len(sqa_issues) * 100 if sqa_issues else 0
    sqa_peak    = max(sqa_monthly, key=sqa_monthly.get) if sqa_monthly else None

    # 결함
    def_project  = Counter(i['project_name'] for i in defect_issues)
    def_priority = Counter(i['priority']     for i in defect_issues)
    def_status   = Counter(i['status']       for i in defect_issues)
    def_monthly  = Counter(i['month']        for i in defect_issues)
    def_resolved = sum(1 for i in defect_issues if i['resolved'])
    def_rate     = def_resolved / len(defect_issues) * 100 if defect_issues else 0
    def_peak     = max(def_monthly, key=def_monthly.get) if def_monthly else None
    amplitude    = sum(1 for i in defect_issues if i.get('amplitude'))
    high_pri     = sum(1 for i in defect_issues if i['priority'] in ('Highest', 'High'))

    # ── HTML 구성 ─────────────────────────────────────────────────
    # 개요
    overview_rows = (
        "<tr><th>담당자</th><td>{}</td></tr>"
        "<tr><th>대상 기간</th><td>{} ~ {}</td></tr>"
        "<tr><th>작업관리 이슈 (SQA)</th><td>{}</td></tr>"
        "<tr><th>결함 이슈 (타 프로젝트)</th><td>{}</td></tr>"
        "<tr><th>Confluence 페이지 작성/수정</th><td>{}개</td></tr>"
    ).format(
        f"{display_name} ({user_email})", start_date, end_date,
        linked(f"{len(sqa_issues)}개", jql_url(base_url, JQL_SQA)),
        linked(f"{len(defect_issues)}개", jql_url(base_url, JQL_DEF)),
        len(pages)
    )

    # SQA 섹션
    sqa_type_rows = "".join(
        "<tr><td>{}</td>{}</tr>".format(
            t, center(linked(str(c), jql_url(base_url, f'{JQL_SQA} AND issuetype = "{t}"')))
        )
        for t, c in sqa_type.most_common()
    )
    sqa_summary_rows = (
        "<tr><th>총 이슈</th><td>{}</td></tr>"
        "<tr><th>완료</th><td>{}개 ({:.0f}%)</td></tr>"
        "<tr><th>가장 바쁜 달</th><td>{} ({}개)</td></tr>"
    ).format(
        linked(f"{len(sqa_issues)}개", jql_url(base_url, JQL_SQA)),
        sqa_resolved, sqa_rate,
        month_label(sqa_peak) if sqa_peak else '-', sqa_monthly.get(sqa_peak, 0)
    )

    # 결함 섹션
    def_proj_rows = "".join(
        "<tr><td>{}</td>{}</tr>".format(
            p, center(linked(str(c), jql_url(base_url, f'{JQL_DEF} AND project = "{p}"')))
        )
        for p, c in def_project.most_common()
    )
    def_prio_rows = "".join(
        "<tr><td>{}</td>{}</tr>".format(
            p, center(linked(str(def_priority[p]), jql_url(base_url, f'{JQL_DEF} AND priority = "{p}"')))
        )
        for p in PRIORITY_ORDER if p in def_priority
    )
    def_summary_rows = (
        "<tr><th>총 결함</th><td>{}</td></tr>"
        "<tr><th>해결 완료</th><td>{}개 ({:.0f}%)</td></tr>"
        "<tr><th>High 이상 우선순위</th><td>{}</td></tr>"
        "<tr><th>Amplitude 관련</th><td>{}</td></tr>"
        "<tr><th>가장 바쁜 달</th><td>{} ({}개)</td></tr>"
    ).format(
        linked(f"{len(defect_issues)}개", jql_url(base_url, JQL_DEF)),
        def_resolved, def_rate,
        linked(f"{high_pri}개", jql_url(base_url, f'{JQL_DEF} AND priority in (Highest, High)')),
        linked(f"{amplitude}개", jql_url(base_url, f'{JQL_DEF} AND summary ~ "[Amplitude]"')),
        month_label(def_peak) if def_peak else '-', def_monthly.get(def_peak, 0)
    )

    # Confluence 페이지 목록
    page_rows = "".join(
        "<tr><td><a href='{}'>{}</a></td><td>{}</td><td>{}</td></tr>".format(
            p['url'], p['title'], p['created'], p['lastModified']
        )
        for p in pages
    ) or "<tr><td colspan='3'>조회된 페이지 없음</td></tr>"

    # 총평
    proj_summary = ", ".join(f"{p}({c}건)" for p, c in def_project.most_common())
    if is_current_year:
        period_desc = f"{year}년 1월부터 {today.month}월 {today.day}일까지"
        summary_title = f"{year}년 현황 요약 (~ {today.month}월 {today.day}일)"
    else:
        period_desc = f"{year}년 한 해 동안"
        summary_title = f"{year}년 총평"

    full_body = """
<h2>개요</h2>
{overview}

<h2>작업관리 (SQA 프로젝트)</h2>
{sqa_ov}
<h3>이슈 유형별</h3>{sqa_type}
<h3>상태별</h3>{sqa_st}
<h3>월별 현황</h3>{sqa_mo}

<h2>결함 (타 프로젝트)</h2>
{def_ov}
<h3>프로젝트별</h3>{def_pj}
<h3>우선순위별</h3>{def_pr}
<h3>상태별</h3>{def_st}
<h3>월별 현황</h3>{def_mo}

<h2>Confluence 문서 현황</h2>
{pages}

<hr/>
<h2>{summary_title}</h2>
<p>{period_desc} <strong>작업관리(SQA) {sqa_n}개</strong>와 <strong>결함 {def_n}개</strong>, 총 {total}개의 이슈를 처리했습니다.</p>
<p>작업관리에서는 {sqa_n}건 중 {sqa_r}건({sqa_rate:.0f}%)을 완료했으며, {sqa_peak_label}에 가장 많은 작업({sqa_peak_n}건)이 집중되었습니다.</p>
<p>결함 영역에서는 {proj_summary} 등에서 총 {def_n}건을 발굴·추적하여 {def_rate:.0f}%의 해결률을 기록했습니다. High 이상 우선순위 {hi}건, Amplitude 관련 {amp}건을 별도 관리했습니다.</p>
<p>Confluence에 {page_n}개의 문서를 작성/수정했습니다.</p>
""".format(
        overview=ov_table(overview_rows),
        sqa_ov=ov_table(sqa_summary_rows),
        sqa_type=table(['유형', '건수'], sqa_type_rows),
        sqa_st=table(['상태', '건수'], build_status_rows(sqa_status, JQL_SQA, base_url)),
        sqa_mo=table(['월', '이슈 수'], build_monthly_rows(sqa_monthly, JQL_SQA, base_url, months, end_date)),
        def_ov=ov_table(def_summary_rows),
        def_pj=table(['프로젝트', '결함 수'], def_proj_rows),
        def_pr=table(['우선순위', '건수'], def_prio_rows),
        def_st=table(['상태', '건수'], build_status_rows(def_status, JQL_DEF, base_url)),
        def_mo=table(['월', '이슈 수'], build_monthly_rows(def_monthly, JQL_DEF, base_url, months, end_date)),
        pages=table(['제목', '생성일', '최종 수정일'], page_rows),
        summary_title=summary_title, period_desc=period_desc,
        sqa_n=len(sqa_issues), def_n=len(defect_issues), total=len(sqa_issues) + len(defect_issues),
        sqa_r=sqa_resolved, sqa_rate=sqa_rate,
        sqa_peak_label=month_label(sqa_peak) if sqa_peak else '-',
        sqa_peak_n=sqa_monthly.get(sqa_peak, 0),
        proj_summary=proj_summary,
        def_rate=def_rate, hi=high_pri, amp=amplitude, page_n=len(pages)
    )

    # ── Confluence 게시 ───────────────────────────────────────────
    if is_current_year:
        title = f"{year}년 업무 현황 보고서 (~ {today.month}월 {today.day}일) - {display_name}"
    else:
        title = f"{year}년 연간 업무 성과 보고서 - {display_name}"

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
        if quiet:
            print(f"SUCCESS: {url}")
        else:
            print(f"SUCCESS: {url}")
    else:
        print("ERROR: 게시 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
