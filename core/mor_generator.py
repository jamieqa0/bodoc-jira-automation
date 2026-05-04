"""
MOR Report 초안 생성 모듈
템플릿 기반으로 Jira/Confluence 데이터를 기반으로 MOR 5항목을 생성합니다.
"""

import os
from config.settings import settings


class MorGenerator:
    def __init__(self):
        # 템플릿 기반 생성만 사용
        pass

    def generate_draft(self, jira_issues, confluence_pages, user_email, year_month):
        """
        Jira/Confluence 데이터를 기반으로 MOR 초안을 생성합니다.
        템플릿 기반으로 자동 생성합니다.

        Args:
            jira_issues: Jira 이슈 리스트
            confluence_pages: Confluence 페이지 리스트
            user_email: 사용자 이메일
            year_month: 년월 (예: 2026-04)

        Returns:
            str: 마크다운 형식의 MOR 초안
        """

        return self._generate_with_template(jira_issues, confluence_pages, user_email, year_month)

    def _generate_with_template(self, jira_issues, confluence_pages, user_email, year_month):
        """템플릿 기반으로 MOR 초안 생성"""
        # 데이터 요약
        jira_summary = self._summarize_jira_issues(jira_issues)
        confluence_summary = self._summarize_confluence_pages(confluence_pages)

        # 기본 통계 계산
        total_issues = len(jira_issues)
        resolved_statuses_list = ['Resolved', 'Closed', 'Done', 'Verified', '해결됨', '완료', '종료', 'Prod 배포완료']
        resolved_issues = len([i for i in jira_issues if i.get('status') in resolved_statuses_list])
        total_pages = len(confluence_pages)
        resolution_rate = (resolved_issues / total_issues * 100) if total_issues > 0 else 0

        # JQL 링크 생성
        year, month = map(int, year_month.split('-'))
        import calendar
        from urllib.parse import quote
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year_month}-01"
        end_date = f"{year_month}-{last_day:02d}"

        # 전체 이슈 링크 (담당자 OR 보고자 OR SQA 프로젝트)
        all_issues_jql = f"((assignee = \"{user_email}\" OR reporter = \"{user_email}\") OR project = \"SQA\") AND created >= \"{start_date}\" AND created <= \"{end_date}\""
        all_issues_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/secure/IssueNavigator.jspa?jql={quote(all_issues_jql)}"

        # 해결된 이슈 링크 (담당자 OR 보고자 OR SQA 프로젝트)
        resolved_jql = f"((assignee = \"{user_email}\" OR reporter = \"{user_email}\") OR project = \"SQA\") AND created >= \"{start_date}\" AND created <= \"{end_date}\" AND status in ({', '.join(f'\"{s}\"' for s in resolved_statuses_list)})"
        resolved_issues_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/secure/IssueNavigator.jspa?jql={quote(resolved_jql)}"

        # 템플릿 기반 MOR 내용 생성
        mor_content = f"""## 📊 1. 주요 업무 성과 요약

{year_month}월 한 달간 총 **[{total_issues}건]({all_issues_url})**의 Jira 이슈를 처리하였으며, 그 중 **[{resolved_issues}건]({resolved_issues_url})**을 완료하였습니다. (해결률: **{resolution_rate:.1f}%**) 또한, **{total_pages}건**의 Confluence 문서를 작성 및 업데이트하여 팀 내 지식 공유에 기여하였습니다.

{jira_summary}

---

## 🏗️ 2. 본인의 구체적인 담당 영역

- 

---

## 🚀 3. 전문 기여 포인트

- 

---

## 🔍 4. 업무 진행의 의도 설명

- 

---

## 🛠️ 5. 문제 해결 또는 생산성 향상을 위한 노력

- 

### 📝 주요 작성/수정 문서 (Top 10)
{confluence_summary}
"""

        # 전체 초안 구성
        draft = f"""{mor_content}

---
*본 보고서는 시스템에 의해 자동 생성된 초안입니다. 검토 후 최종 내용을 확정해 주시기 바랍니다.*
"""

        return draft

    def _summarize_jira_issues(self, issues):
        """Jira 이슈를 요약 문자열로 변환 (SQA와 일반 작업 분리)"""
        if not issues:
            return "해당 월에 처리한 Jira 이슈가 없습니다."

        sqa_tasks = [i for i in issues if i['key'].startswith('SQA-')]
        general_tasks = [i for i in issues if not i['key'].startswith('SQA-')]

        def format_list(task_list, title):
            if not task_list:
                return ""
            
            lines = [f"### 🎯 {title}"]
            for issue in task_list[:10]:
                issue_url = f"https://bodocqa.atlassian.net/browse/{issue['key']}"
                lines.append(f"- [[{issue['key']}]]({issue_url}) {issue['summary']} ({issue['status']})")
            
            if len(task_list) > 10:
                lines.append(f"... 외 {len(task_list) - 10}개")
            return "\n".join(lines)

        sections = []
        if sqa_tasks:
            sections.append(format_list(sqa_tasks, "주요 SQA 작업"))
        if general_tasks:
            sections.append(format_list(general_tasks, "기타 업무 및 작업"))

        return "\n\n".join(sections)

    def _summarize_confluence_pages(self, pages):
        """Confluence 페이지를 요약 문자열로 변환 (링크 포함)"""
        if not pages:
            return "해당 월에 작성/수정한 Confluence 페이지가 없습니다."

        summary = []
        for page in pages[:10]:  # 최대 10개 요약
            page_url = f"https://bodocqa.atlassian.net/wiki/spaces/{page['space']['key']}/pages/{page['id']}"
            summary.append(f"- [{page['title']}]({page_url}) ({page['space']['name']}) - {page.get('lastModified', page.get('created', 'N/A'))}")

        if len(pages) > 10:
            summary.append(f"... 외 {len(pages) - 10}개")

        return "\n".join(summary)