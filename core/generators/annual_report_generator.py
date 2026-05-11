import calendar
import re
import urllib.parse
from collections import Counter
from jinja2 import Environment, FileSystemLoader
import os
from config.settings import settings

class AnnualGenerator:
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
        account_id = user_info.get('accountId', user_email)

        BASE_DATE_JQL = f'AND created >= "{start_date}" AND created <= "{end_date}"'
        JQL_SQA = f'project = "SQA" {BASE_DATE_JQL}'
        JQL_DEF = f'(assignee = "{user_email}" OR reporter = "{user_email}") AND project != "SQA" AND issuetype = Defect {BASE_DATE_JQL}'

        # SQA 분석
        _SUBTASK_TYPES = {'sub-task', 'subtask', '하위 작업', 'child issue'}
        sqa_main_issues = [i for i in sqa_issues if i['issuetype'].lower() not in _SUBTASK_TYPES]
        sqa_monthly_counts = Counter(i['month'] for i in sqa_main_issues)
        sqa_resolved = sum(1 for i in sqa_main_issues if i['resolved'])
        sqa_rate = (sqa_resolved / len(sqa_main_issues) * 100) if sqa_main_issues else 0
        sqa_peak = max(sqa_monthly_counts, key=sqa_monthly_counts.get) if sqa_monthly_counts else None
        sqa_main_task_count = sum(1 for i in sqa_main_issues if i.get('is_main'))
        sqa_sub_task_count = len(sqa_main_issues) - sqa_main_task_count

        # 결함 분석
        def_project_counts = Counter(i['project_name'] for i in defect_issues)
        def_priority_counts = Counter(i['priority'] for i in defect_issues)
        def_status_counts = Counter(i['status'] for i in defect_issues)
        def_monthly_counts = Counter(i['month'] for i in defect_issues)
        def_resolved = sum(1 for i in defect_issues if i['resolved'])
        def_rate = (def_resolved / len(defect_issues) * 100) if defect_issues else 0
        def_peak = max(def_monthly_counts, key=def_monthly_counts.get) if def_monthly_counts else None
        amplitude_count = sum(1 for i in defect_issues if i.get('amplitude'))
        ai_count = sum(1 for i in defect_issues if re.search(r'AI\s*상담사', i['summary'], re.IGNORECASE))
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

        # 비율 계산
        total_defects = len(defect_issues)
        defect_project_ratios = [
            (p, c, (c / total_defects * 100)) 
            for p, c in def_project_counts.most_common()
        ] if total_defects > 0 else []
        amplitude_ratio = (amplitude_count / total_defects * 100) if total_defects > 0 else 0
        ai_ratio = (ai_count / total_defects * 100) if total_defects > 0 else 0

        # 카테고리별 이슈 키 그룹화
        cat_keys = {}
        for iss in defect_issues:
            cat = iss['project_name']
            if cat not in cat_keys:
                cat_keys[cat] = []
            cat_keys[cat].append(iss['key'])

        def get_cat_jql(cat_name):
            keys = cat_keys.get(cat_name, [])
            if not keys:
                return "key is EMPTY"
            return f"key in ({', '.join(keys)})"

        context = {
            'title': title,
            'display_name': display_name,
            'user_email': user_email,
            'account_id': account_id,
            'start_date': start_date,
            'end_date': end_date,
            'sqa_count': len(sqa_issues),
            'sqa_main_count': len(sqa_main_issues),
            'sqa_main_task_count': sqa_main_task_count,
            'sqa_sub_task_count': sqa_sub_task_count,
            'defect_count': len(defect_issues),
            'page_count': len(pages),
            'sqa_all_url': self._jql_url(JQL_SQA),
            'defect_all_url': self._jql_url(JQL_DEF),
            'sqa_resolved': sqa_resolved,
            'sqa_rate': sqa_rate,
            'sqa_peak_label': month_label(sqa_peak),
            'sqa_peak_count': sqa_monthly_counts.get(sqa_peak, 0),
            'defect_resolved': def_resolved,
            'defect_rate': def_rate,
            'high_prio_count': high_prio_count,
            'high_prio_url': self._jql_url(f'{JQL_DEF} AND priority in (Highest, High)'),
            'amplitude_count': amplitude_count,
            'amplitude_ratio': amplitude_ratio,
            'amplitude_url': self._jql_url(f'{JQL_DEF} AND summary ~ "Amplitude"'),
            'ai_count': ai_count,
            'ai_ratio': ai_ratio,
            'ai_url': self._jql_url(f'{JQL_DEF} AND summary ~ "AI 상담사"'),
            'defect_peak_label': month_label(def_peak),
            'defect_peak_count': def_monthly_counts.get(def_peak, 0),
            'defect_projects': [(p, c, self._jql_url(get_cat_jql(p))) for p, c in def_project_counts.most_common()],
            'defect_project_ratios': defect_project_ratios,
            'defect_priorities': [(p, def_priority_counts[p], self._jql_url(f'{JQL_DEF} AND priority = "{p}"')) for p in self.PRIORITY_ORDER if p in def_priority_counts],
            'defect_statuses': [(s, c, self._jql_url(f'{JQL_DEF} AND status = "{s}"')) for s, c in def_status_counts.most_common()],
            'defect_monthly': [(month_label(m), c, self._jql_url(f'{JQL_DEF} AND created >= "{m}-01" AND created <= "{m}-{calendar.monthrange(int(m[:4]), int(m[5:]))[1]:02d}"')) for m, c in sorted(def_monthly_counts.items())],
            'pages': pages,
            'summary_title': summary_title,
            'period_desc': period_desc,
            'proj_summary': ", ".join(f"{p}({c}건, {c/total_defects*100:.1f}%)" for p, c in def_project_counts.most_common()) if total_defects > 0 else "없음",
        }

        return title, self.template.render(context)
