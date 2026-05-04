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
        resolved_issues = len([i for i in jira_issues if i.get('status') in ['Resolved', 'Closed', 'Done', 'Verified', '해결됨', '완료', '종료']])
        total_pages = len(confluence_pages)

        # JQL 링크 생성
        year, month = map(int, year_month.split('-'))
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year_month}-01"
        end_date = f"{year_month}-{last_day:02d}"

        # 전체 이슈 링크
        all_issues_jql = f"assignee = \"{user_email}\" AND created >= \"{start_date}\" AND created <= \"{end_date}\""
        all_issues_url = f"https://bodocqa.atlassian.net/issues/?jql={all_issues_jql.replace(' ', '%20').replace('\"', '%22')}"

        # 해결된 이슈 링크
        resolved_statuses = ['Resolved', 'Closed', 'Done', 'Verified', '해결됨', '완료', '종료']
        resolved_jql = f"assignee = \"{user_email}\" AND created >= \"{start_date}\" AND created <= \"{end_date}\" AND status in ({', '.join(f'\"{s}\"' for s in resolved_statuses)})"
        resolved_issues_url = f"https://bodocqa.atlassian.net/issues/?jql={resolved_jql.replace(' ', '%20').replace('\"', '%22')}"

        # 템플릿 기반 MOR 내용 생성
        mor_content = f"""## 1. 한 달 동안 진행한 업무

{year_month}월 동안 총 [{total_issues}개의 Jira 이슈]({all_issues_url})를 처리하였습니다. 이 중 [{resolved_issues}개가 해결]({resolved_issues_url})되었으며, {total_pages}개의 Confluence 페이지를 작성하거나 수정하였습니다.

주요 업무 내용:
{jira_summary}

## 2. 본인의 구체적인 담당 영역

프로젝트 관리 및 품질 보증 업무를 담당하였습니다. Jira 티켓 관리, 테스트 계획 수립, 그리고 Confluence를 통한 문서화 작업을 수행하였습니다.

## 3. 전문 기여 포인트

자동화 스크립트 개발을 통해 업무 효율성을 향상시켰습니다. 특히 QA 보고서 자동 생성 기능과 테스트 플랜 자동화 기능을 구현하여 반복 작업을 줄였습니다.

## 4. 업무 진행의 의도 설명

효율적인 프로젝트 관리를 위해 자동화 도구를 도입하고, 체계적인 문서화를 통해 팀 협업을 강화하고자 하였습니다. 데이터 기반 의사결정을 지원하기 위해 각종 지표 수집 및 분석 기능을 개발하였습니다.

## 5. 문제 해결 또는 생산성 향상을 위한 노력

반복적인 업무를 자동화하여 생산성을 향상시키고, 실수 가능성을 줄였습니다. 특히 Jira/Confluence 연동을 통해 업무 흐름을 최적화하였습니다.

작성/수정한 문서:
{confluence_summary}
"""

        # 전체 초안 구성
        draft = f"""# MOR Report 초안 - {year_month}

**사용자:** {user_email}
**생성일:** {settings.get_current_date()}

{mor_content}

---
*이 초안은 템플릿 기반으로 자동 생성되었습니다. 검토 후 편집해주세요.*
"""

        return draft

    def _summarize_jira_issues(self, issues):
        """Jira 이슈를 요약 문자열로 변환 (링크 포함)"""
        if not issues:
            return "해당 월에 처리한 Jira 이슈가 없습니다."

        summary = []
        for issue in issues[:10]:  # 최대 10개 요약
            issue_url = f"https://bodocqa.atlassian.net/browse/{issue['key']}"
            summary.append(f"- [{issue['key']}: {issue['summary']}]({issue_url}) ({issue['status']})")

        if len(issues) > 10:
            summary.append(f"... 외 {len(issues) - 10}개")

        return "\n".join(summary)

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