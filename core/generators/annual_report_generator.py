import urllib.parse
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import os
from config.settings import settings

class AnnualGenerator:
    RESOLVED_STATUSES = {
        'Prod 배포완료', '종료', 'Resolved', 'Closed', 'Done',
        'Verified', '해결됨', '완료', '종료됨',
    }
    PRIORITY_ORDER = ['Highest', 'High', 'Medium', 'Low', 'Lowest', 'None']

    def __init__(self):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template('annual_report.html')

    def _jql_url(self, jql):
        base_url = settings.ATLASSIAN_URL.rstrip('/')
        return f"{base_url}/secure/IssueNavigator.jspa?jql={urllib.parse.quote(jql)}"

    def _is_resolved(self, issue_data):
        # raw 이슈 객체가 아니라 이미 파싱된 딕셔너리 데이터를 받는다고 가정
        return issue_data.get('resolved', False)

    def generate_html(self, sqa_issues, defect_issues, pages, user_info, year, start_date, end_date, is_current_year):
        base_url = settings.ATLASSIAN_URL.rstrip('/')
        user_email = user_info['email']
        display_name = user_info['displayName']

        BASE_DATE_JQL = f'AND created >= "{start_date}" AND created <= "{end_date}"'
        JQL_SQA = f'project = "SQA" {BASE_DATE_JQL}'
        JQL_DEF = f'(assignee = "{user_email}" OR reporter = "{user_email}") AND project != "SQA" {BASE_DATE_JQL}'

        # SQA 분석
        sqa_type_counts = Counter(i['issuetype'] for i in sqa_issues)
        sqa_status_counts = Counter(i['status'] for i in sqa_issues)
        sqa_monthly_counts = Counter(i['month'] for i in sqa_issues)
        sqa_resolved = sum(1 for i in sqa_issues if i['resolved'])
        sqa_rate = (sqa_resolved / len(sqa_issues) * 100) if sqa_issues else 0
        sqa_peak = max(sqa_monthly_counts, key=sqa_monthly_counts.get) if sqa_monthly_counts else None

        # 결함 분석
        def_project_counts = Counter(i['project_name'] for i in defect_issues)
        def_priority_counts = Counter(i['priority'] for i in defect_issues)
        def_status_counts = Counter(i['status'] for i in defect_issues)
        def_monthly_counts = Counter(i['month'] for i in defect_issues)
        def_resolved = sum(1 for i in defect_issues if i['resolved'])
        def_rate = (def_resolved / len(defect_issues) * 100) if defect_issues else 0
        def_peak = max(def_monthly_counts, key=def_monthly_counts.get) if def_monthly_counts else None
        amplitude_count = sum(1 for i in defect_issues if i.get('amplitude'))
        high_prio_count = sum(1 for i in defect_issues if i['priority'] in ('Highest', 'High'))

        # 템플릿용 데이터 구성
        def month_label(m):
            return f"{int(m[5:7])}월" if m else "-"

        from datetime import datetime
        today = datetime.now()
        
        if is_current_year:
            summary_title = f"{year}년 현황 요약 (~ {today.month}월 {today.day}일)"
            period_desc = f"{year}년 1월부터 {today.month}월 {today.day}일까지"
            title = f"{year}년 업무 현황 보고서 (~ {today.month}월 {today.day}일) - {display_name}"
        else:
            summary_title = f"{year}년 총평"
            period_desc = f"{year}년 한 해 동안"
            title = f"{year}년 연간 업무 성과 보고서 - {display_name}"

        # 월 목록 생성 (데이터가 있는 달만)
        sorted_months = sorted(set(list(sqa_monthly_counts.keys()) + list(def_monthly_counts.keys())))

        context = {
            'title': title,
            'display_name': display_name,
            'user_email': user_email,
            'start_date': start_date,
            'end_date': end_date,
            'sqa_count': len(sqa_issues),
            'defect_count': len(defect_issues),
            'page_count': len(pages),
            'sqa_all_url': self._jql_url(JQL_SQA),
            'defect_all_url': self._jql_url(JQL_DEF),
            'sqa_resolved': sqa_resolved,
            'sqa_rate': sqa_rate,
            'sqa_peak_label': month_label(sqa_peak),
            'sqa_peak_count': sqa_monthly_counts.get(sqa_peak, 0),
            'sqa_types': [(t, c, self._jql_url(f'{JQL_SQA} AND issuetype = "{t}"')) for t, c in sqa_type_counts.most_common()],
            'sqa_statuses': [(s, c, self._jql_url(f'{JQL_SQA} AND status = "{s}"')) for s, c in sqa_status_counts.most_common()],
            'sqa_monthly': [(month_label(m), c, self._jql_url(f'{JQL_SQA} AND created >= "{m}-01" AND created <= "{m}-31"')) for m, c in sorted(sqa_monthly_counts.items())],
            'defect_resolved': def_resolved,
            'defect_rate': def_rate,
            'high_prio_count': high_prio_count,
            'high_prio_url': self._jql_url(f'{JQL_DEF} AND priority in (Highest, High)'),
            'amplitude_count': amplitude_count,
            'amplitude_url': self._jql_url(f'{JQL_DEF} AND summary ~ "[Amplitude]"'),
            'defect_peak_label': month_label(def_peak),
            'defect_peak_count': def_monthly_counts.get(def_peak, 0),
            'defect_projects': [(p, c, self._jql_url(f'{JQL_DEF} AND project = "{p}"')) for p, c in def_project_counts.most_common()],
            'defect_priorities': [(p, def_priority_counts[p], self._jql_url(f'{JQL_DEF} AND priority = "{p}"')) for p in self.PRIORITY_ORDER if p in def_priority_counts],
            'defect_statuses': [(s, c, self._jql_url(f'{JQL_DEF} AND status = "{s}"')) for s, c in def_status_counts.most_common()],
            'defect_monthly': [(month_label(m), c, self._jql_url(f'{JQL_DEF} AND created >= "{m}-01" AND created <= "{m}-31"')) for m, c in sorted(def_monthly_counts.items())],
            'pages': pages,
            'summary_title': summary_title,
            'period_desc': period_desc,
            'proj_summary': ", ".join(f"{p}({c}건)" for p, c in def_project_counts.most_common()),
        }

        return title, self.template.render(context)
