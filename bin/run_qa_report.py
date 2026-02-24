import os
import sys
import logging
import urllib3
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import platform
import io
from jinja2 import Environment, FileSystemLoader

# 한글 폰트 설정
if platform.system() == 'Windows':
    matplotlib.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    matplotlib.rc('font', family='AppleGothic')
else:
    matplotlib.rc('font', family='NanumGothic')
matplotlib.rcParams['axes.unicode_minus'] = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from core.utils import extract_version, format_date, extract_project_name

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JiraReporter:
    def __init__(self):
        self.jira = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        self.confluence = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
        self.jinja_env = Environment(loader=FileSystemLoader(str(settings.TEMPLATE_DIR)))

    def analyze_data(self, df):
        """상태 및 우선순위별 데이터 분석"""
        if df.empty: return None, None, None
        
        amp_mask = df['Summary'].str.contains(r'\[Amplitude\]', case=False, na=False)
        return df['Status'].value_counts(), df['Priority'].value_counts(), df[amp_mask]['Status'].value_counts() if any(amp_mask) else None

    def generate_charts(self, status_counts, priority_counts, amp_status_counts=None):
        """통계 차트(PNG) 생성"""
        charts = {}
        plt.style.use('seaborn-v0_8-muted')
        
        def save_chart(filename):
            plt.tight_layout()
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
            img.seek(0)
            charts[filename] = img
            plt.close()

        if status_counts is not None and not status_counts.empty:
            plt.figure(figsize=(6, 4))
            plt.pie(status_counts, labels=status_counts.index, autopct=lambda p: f'{p:.1f}%\n({int(p/100.*sum(status_counts))})',
                    startangle=140, colors=plt.cm.Pastel1.colors, pctdistance=0.75, explode=[0.05]*len(status_counts))
            plt.title('All Defects by Status', fontsize=12, weight='bold')
            plt.gcf().gca().add_artist(plt.Circle((0,0), 0.60, fc='white'))
            save_chart('status_chart.png')

        if priority_counts is not None and not priority_counts.empty:
            plt.figure(figsize=(6, 4))
            bars = plt.bar(priority_counts.index, priority_counts.values, color=plt.cm.Paired.colors)
            plt.title('All Defects by Priority', fontsize=12, weight='bold')
            for b in bars:
                plt.text(b.get_x() + b.get_width()/2., b.get_height() + 0.1, f'{int(b.get_height())}', ha='center', va='bottom', fontweight='bold')
            plt.xticks(rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            save_chart('priority_chart.png')
            
        if amp_status_counts is not None and not amp_status_counts.empty:
            plt.figure(figsize=(6, 4))
            plt.pie(amp_status_counts, labels=amp_status_counts.index, autopct='%1.1f%%',
                    startangle=140, colors=plt.cm.Pastel2.colors, pctdistance=0.75, explode=[0.05]*len(amp_status_counts))
            plt.title('Amplitude Issues by Status', fontsize=12, weight='bold')
            plt.gcf().gca().add_artist(plt.Circle((0,0), 0.60, fc='white'))
            save_chart('amplitude_chart.png')
            
        return charts

    def create_report_html(self, df, status_counts, priority_counts, test_info, charts):
        """Jinja2 템플릿을 사용하여 HTML 리포트 생성"""
        total = len(df)
        amp_mask = df['Summary'].str.contains(r'\[Amplitude\]', case=False, na=False) if not df.empty else []
        
        # 해결률 계산
        resolved_statuses = ['Resolved', 'Closed', 'Done', 'Verified', '해결됨', '완료', '종료']
        resolved_count = len(df[df['Status'].isin(resolved_statuses)]) if not df.empty else 0
        res_rate = (resolved_count / total * 100) if total > 0 else 0

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

        render_data = {
            'report_title': f"{test_info.get('qa_summary')} Report",
            'project_name': test_info.get('project_name', 'Unknown'),
            'prd_url': test_info.get('prd_url') or "링크 필요",
            'worker_str': workers,
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
            'has_amplitude_chart': 'amplitude_chart.png' in charts
        }
        return self.jinja_env.get_template('qa_report_template.html').render(render_data)

    def run(self, qa_task_key):
        logging.info(f"QA Report 시작: {qa_task_key}")
        task_info = self.jira.get_issue_info(qa_task_key)
        if not task_info: return

        df = self.jira.fetch_defects(qa_task_key)
        stats = self.analyze_data(df)
        charts = self.generate_charts(*stats)
        
        info = {
            "qa_task": qa_task_key,
            "qa_summary": task_info['summary'],
            "project_name": extract_project_name(task_info['summary']),
            "prd_url": task_info.get('prd_url'),
            "version": extract_version(task_info['summary'])
        }
        html = self.create_report_html(df, stats[0], stats[1], info, charts)
        
        page = self.confluence.publish_page(settings.CONFLUENCE_SPACE_KEY, f"{task_info['summary']} Report", html, settings.CONFLUENCE_QA_REPORT_PARENT_ID)
        if page:
            for name, data in charts.items():
                self.confluence.attach_file(page.get('id'), name, data)
            logging.info(f"게시 완료: {settings.ATLASSIAN_URL}/wiki/pages/{page.get('id')}")

if __name__ == "__main__":
    qa_key = sys.argv[1] if len(sys.argv) > 1 else "SQA-122"
    JiraReporter().run(qa_key)
