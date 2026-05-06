"""
MOR Report 초안 생성 모듈
템플릿 기반으로 Jira/Confluence 데이터를 기반으로 MOR 5항목을 생성합니다.
"""

import calendar
import os
from config.settings import settings
from core.utils import RESOLVED_STATUSES


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
        confluence_summary = self._summarize_confluence_pages(confluence_pages)

        # 세부 통계 계산
        sqa_tasks = [i for i in jira_issues if i['key'].startswith('SQA-')]
        defect_issues = [i for i in jira_issues if not i['key'].startswith('SQA-')]
        
        sqa_count = len(sqa_tasks)
        defect_count = len(defect_issues)
        
        resolved_issues = len([
            i for i in jira_issues
            if i.get('status') in RESOLVED_STATUSES or i.get('resolutiondate') is not None
        ])
        total_pages = len(confluence_pages)
        total_issues = len(jira_issues)
        resolution_rate = (resolved_issues / total_issues * 100) if total_issues > 0 else 0

        # JQL 링크 생성
        year, month = map(int, year_month.split('-'))
        from urllib.parse import quote
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year_month}-01"
        end_date = f"{year_month}-{last_day:02d}"

        # JQL 링크 (SQA / 결함 분리)
        sqa_jql = f'project = "SQA" AND created >= "{start_date}" AND created <= "{end_date}"'
        defect_jql = f'(assignee = "{user_email}" OR reporter = "{user_email}") AND project != "SQA" AND created >= "{start_date}" AND created <= "{end_date}"'
        all_jql = f'((assignee = "{user_email}" OR reporter = "{user_email}") OR project = "SQA") AND created >= "{start_date}" AND created <= "{end_date}"'
        
        sqa_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/secure/IssueNavigator.jspa?jql={quote(sqa_jql)}"
        defect_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/secure/IssueNavigator.jspa?jql={quote(defect_jql)}"
        all_issues_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/secure/IssueNavigator.jspa?jql={quote(all_jql)}"

        # 해결된 이슈 링크
        resolved_jql = f"({all_jql}) AND status in ({', '.join(f'\"{s}\"' for s in RESOLVED_STATUSES)})"
        resolved_issues_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/secure/IssueNavigator.jspa?jql={quote(resolved_jql)}"

        jira_summary = self._summarize_jira_issues(jira_issues, defect_url)

        # 템플릿 기반 MOR 내용 생성
        mor_content = f"""## 📊 1. 주요 업무 성과 요약

{year_month}월 한 달간 **QA 작업(SQA) [{sqa_count}건]({sqa_url})** 및 **프로젝트 결함 검출 [{defect_count}건]({defect_url})**을 포함하여 총 **[{total_issues}건]({all_issues_url})**의 Jira 이슈를 처리했습니다. 그 중 **[{resolved_issues}건]({resolved_issues_url})**을 완료하여 **{resolution_rate:.1f}%**의 해결률을 기록하였으며, **{total_pages}건**의 Confluence 문서를 기여했습니다.

{jira_summary}

### 📝 주요 작성/수정 문서 (Top 10)
{confluence_summary}
"""

        # 전체 초안 구성
        draft = f"""{mor_content}

---

### 🏗️ 2. 본인의 구체적인 담당 영역

- 


### 🚀 3. 전문 기여 포인트

- 


### 🔍 4. 업무 진행의 의도 설명

- 


### 🛠️ 5. 문제 해결 또는 생산성 향상을 위한 노력

- 



---

"""

        return draft

    def _summarize_jira_issues(self, issues, defect_url=None):
        """Jira 이슈를 요약 문자열로 변환 (SQA와 일반 작업 분리)"""
        if not issues:
            return "해당 월에 처리한 Jira 이슈가 없습니다."

        priority_rank = {'Highest': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Lowest': 4}

        sqa_tasks = [i for i in issues if i['key'].startswith('SQA-')]
        general_tasks = [i for i in issues if not i['key'].startswith('SQA-')]

        def format_sqa_list(task_list, title):
            if not task_list:
                return ""
            lines = [f"### 🎯 {title}"]
            for issue in task_list[:10]:
                issue_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/browse/{issue['key']}"
                assignee = issue.get('assignee') or ''
                assignee_str = f", 메인담당자 : {assignee}" if assignee else ""
                lines.append(f"- [[{issue['key']}]]({issue_url}) {issue['summary']} ({issue['status']}{assignee_str})")
            if len(task_list) > 10:
                lines.append(f"... 외 {len(task_list) - 10}개")
            return "\n".join(lines)

        def format_general_list(task_list, title):
            if not task_list:
                return ""
            sorted_tasks = sorted(task_list, key=lambda i: priority_rank.get(i.get('priority', ''), 99))
            lines = [f"### 🎯 {title}"]
            for issue in sorted_tasks[:5]:
                issue_url = f"{settings.ATLASSIAN_URL.rstrip('/')}/browse/{issue['key']}"
                priority = issue.get('priority') or ''
                priority_str = f", 우선순위 : {priority}" if priority else ""
                lines.append(f"- [[{issue['key']}]]({issue_url}) {issue['summary']} ({issue['status']}{priority_str})")
            remaining = len(task_list) - 5
            if remaining > 0 and defect_url:
                lines.append(f"- [나머지 {remaining}건 Jira에서 보기]({defect_url})")
            elif remaining > 0:
                lines.append(f"... 외 {remaining}개")
            return "\n".join(lines)

        sections = []
        if sqa_tasks:
            sections.append(format_sqa_list(sqa_tasks, "주요 QA 작업"))
        if general_tasks:
            sections.append(format_general_list(general_tasks, "프로젝트 결함 관리"))

        return "\n\n".join(sections)

    def _summarize_confluence_pages(self, pages):
        """Confluence 페이지를 요약 문자열로 변환 (링크 포함)"""
        if not pages:
            return "해당 월에 작성/수정한 Confluence 페이지가 없습니다."

        summary = []
        for page in pages[:10]:  # 최대 10개 요약
            space = page['space']
            space_str = f" ({space})" if space else ""
            date = page.get('lastModified') or page.get('created') or ''
            date_str = f" - {date}" if date else ""
            summary.append(f"- [{page['title']}]({page['url']}){space_str}{date_str}")

        if len(pages) > 10:
            summary.append(f"... 외 {len(pages) - 10}개")

        return "\n".join(summary)