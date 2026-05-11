import logging
import threading
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # GUI 없는 백엔드 — 스레드 안전
import matplotlib.pyplot as plt
import io
import platform
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from core.clients.jira import JiraClient
from core.utils import extract_version, format_date, extract_project_name, RESOLVED_STATUSES

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    plt.rc('font', family='NanumGothic')
plt.rcParams['axes.unicode_minus'] = False

_chart_lock = threading.Lock()

class QAReportGenerator:
    def __init__(self, jira_client=None):
        self.jira = jira_client or JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        self.jinja_env = Environment(loader=FileSystemLoader(str(settings.TEMPLATE_DIR)))

    def analyze_data(self, df):
        """상태 및 우선순위별 데이터 분석"""
        if df.empty: return None, None, None
        
        amp_mask = df['Summary'].str.contains(r'Amplitude', case=False, na=False) if not df.empty else []
        return df['Status'].value_counts(), df['Priority'].value_counts(), df[amp_mask]['Status'].value_counts() if any(amp_mask) else None

    def generate_charts(self, status_counts, priority_counts, amp_status_counts=None):
        """통계 차트(PNG) 생성"""
        charts = {}
        with _chart_lock:
            return self._generate_charts_locked(status_counts, priority_counts, amp_status_counts)

    def _generate_charts_locked(self, status_counts, priority_counts, amp_status_counts=None):
        charts = {}
        plt.style.use('seaborn-v0_8-muted')
        
        def save_chart(filename):
            plt.tight_layout()
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight', dpi=150)
            img.seek(0)
            charts[filename] = img
            plt.close()

        if status_counts is not None and not status_counts.empty:
            plt.figure(figsize=(8, 6))
            plt.pie(status_counts, labels=status_counts.index, autopct=lambda p: f'{p:.1f}%\n({int(p/100.*sum(status_counts))})',
                    startangle=140, colors=plt.cm.Pastel1.colors, pctdistance=0.75, explode=[0.05]*len(status_counts),
                    textprops={'fontsize': 12})
            plt.title('All Defects by Status', fontsize=15, weight='bold')
            plt.gcf().gca().add_artist(plt.Circle((0,0), 0.60, fc='white'))
            save_chart('status_chart.png')

        if priority_counts is not None and not priority_counts.empty:
            plt.figure(figsize=(8, 6))
            bars = plt.bar(priority_counts.index, priority_counts.values, color=plt.cm.Paired.colors)
            plt.title('All Defects by Priority', fontsize=15, weight='bold')
            for b in bars:
                plt.text(b.get_x() + b.get_width()/2., b.get_height() + 0.1, f'{int(b.get_height())}', ha='center', va='bottom', fontweight='bold', fontsize=13)
            plt.xticks(rotation=45, fontsize=12)
            plt.yticks(fontsize=12)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            save_chart('priority_chart.png')

        if amp_status_counts is not None and not amp_status_counts.empty:
            plt.figure(figsize=(8, 6))
            plt.pie(amp_status_counts, labels=amp_status_counts.index, autopct='%1.1f%%',
                    startangle=140, colors=plt.cm.Pastel2.colors, pctdistance=0.75, explode=[0.05]*len(amp_status_counts),
                    textprops={'fontsize': 12})
            plt.title('Amplitude Issues by Status', fontsize=15, weight='bold')
            plt.gcf().gca().add_artist(plt.Circle((0,0), 0.60, fc='white'))
            save_chart('amplitude_chart.png')
            
        return charts

    def _detect_env_type(self, summary):
        """요약에서 앱/웹 환경을 감지합니다."""
        lower = summary.lower()
        if '보닥' in lower:
            return 'app'
        if '플래너웹' in lower or 'b2b' in lower:
            return 'web'
        # 일반 키워드 fallback
        if any(k in lower for k in ['앱', 'app', 'ios', 'android', '모바일']):
            return 'app'
        return 'web'

    def create_report_html(self, df, status_counts, priority_counts, test_info, charts):
        """Jinja2 템플릿을 사용하여 HTML 리포트 생성"""
        amp_mask = df['Summary'].str.contains(r'Amplitude', case=False, na=False) if not df.empty else []
        df_general = df[~amp_mask] if not df.empty else df

        total = len(df)
        total_general = len(df_general)

        # 해결률: Amplitude 이슈는 별도 관리이므로 일반 결함 기준으로만 계산
        resolved_count = len(df_general[df_general['Status'].isin(RESOLVED_STATUSES)]) if not df_general.empty else 0
        res_rate = (resolved_count / total_general * 100) if total_general > 0 else 0

        # 담당자 목록
        workers = "Unknown"
        if not df.empty and 'Reporter' in df.columns:
            w_list = [w for w in sorted(df['Reporter'].dropna().unique()) if w not in ['Unknown', 'None']]
            workers = ", ".join(w_list) if w_list else "Unknown"

        # 기간 정보
        date_range = format_date(pd.Timestamp.now())
        if not df.empty and 'Created' in df.columns:
            date_range = f"{format_date(df['Created'].min())} ~ {format_date(df['Created'].max())}"

        priority_details = f" ({', '.join([f'{p}: {c}' for p, c in priority_counts.items()])})" if priority_counts is not None else ""

        jira_base = settings.ATLASSIAN_URL.rstrip('/')
        priority_order = {'Highest': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Lowest': 4}
        def _to_list(frame):
            if frame.empty:
                return []
            rows = [
                {
                    'key': row['Key'],
                    'url': f"{jira_base}/browse/{row['Key']}",
                    'summary': row['Summary'],
                    'status': row['Status'],
                    'priority': row.get('Priority', 'None'),
                }
                for _, row in frame.iterrows()
            ]
            return sorted(rows, key=lambda r: priority_order.get(r['priority'], 99))
        defect_list = _to_list(df_general)
        amplitude_list = _to_list(df[amp_mask]) if not df.empty and any(amp_mask) else []

        render_data = {
            'report_title': f"{test_info.get('qa_summary')} Report",
            'project_name': test_info.get('project_name', 'Unknown'),
            'prd_url': test_info.get('prd_url') or "",
            'figma_url': test_info.get('figma_url') or "",
            'confluence_url': test_info.get('confluence_url') or "",
            'pm_str': '작성 필요',
            'dev_str': '작성 필요',
            'qa_str': workers,
            'show_version': '보닥앱' in test_info.get('qa_summary', ''),
            'env_type': self._detect_env_type(test_info.get('qa_summary', '')),
            'jira_url': settings.ATLASSIAN_URL,
            'qa_task_key': test_info.get('qa_task'),
            'date_range': date_range,
            'today_date': format_date(pd.Timestamp.now()),
            'version': test_info.get('version', 'N/A'),
            'total_defects': total,
            'resolution_rate': f"{res_rate:.1f}",
            'priority_details': priority_details,
            'status_counts': status_counts.to_dict() if status_counts is not None else {},
            'priority_counts': priority_counts.to_dict() if priority_counts is not None else {},
            'defects': not df[~amp_mask].empty if not df.empty else False,
            'amplitude_defects': any(amp_mask) if not df.empty else False,
            'total_amplitude': sum(amp_mask) if not df.empty else 0,
            'has_amplitude_chart': 'amplitude_chart.png' in charts,
            'defect_list': defect_list,
            'amplitude_list': amplitude_list,
        }
        template_name = 'qa_report.html'
        return self.jinja_env.get_template(template_name).render(render_data)

    def generate(self, qa_task_key):
        logging.info(f"QA Report 생성 시작: {qa_task_key}")
        task_info = self.jira.get_issue_info(qa_task_key)
        if not task_info: return None

        df = self.jira.fetch_defects(qa_task_key)
        stats = self.analyze_data(df)
        charts = self.generate_charts(*stats)
        
        info = {
            "qa_task": qa_task_key,
            "qa_summary": task_info['summary'],
            "project_name": extract_project_name(task_info['summary']),
            "prd_url": task_info.get('prd_url'),
            "figma_url": task_info.get('figma_url'),
            "confluence_url": task_info.get('confluence_url'),
            "version": extract_version(task_info['summary'])
        }
        html = self.create_report_html(df, stats[0], stats[1], info, charts)
        return html, charts, task_info['summary']
