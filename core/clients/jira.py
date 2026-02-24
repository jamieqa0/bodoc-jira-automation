from jira import JIRA
import pandas as pd
import logging

class JiraClient:
    def __init__(self, url, user, token):
        self.url = url.rstrip('/')
        self.user = user
        self.token = token
        try:
            self.jira = JIRA(
                server=self.url,
                basic_auth=(self.user, self.token),
                options={'verify': False}
            )
            logging.info("Jira 연결 성공")
        except Exception as e:
            logging.error(f"Jira 연결 실패: {e}")
            raise

    def get_issue_info(self, issue_key):
        """이슈 정보를 가져옵니다."""
        try:
            issue = self.jira.issue(issue_key)
            
            # PRD 링크 찾기 시도 (링크된 이슈 중 'PRD' 관련이 있거나 특정 필드 확인)
            prd_url = ""
            for link in getattr(issue.fields, 'issuelinks', []):
                if hasattr(link, 'outwardIssue'):
                    if 'PRD' in link.outwardIssue.fields.summary.upper():
                        prd_url = f"{self.url}/browse/{link.outwardIssue.key}"
                elif hasattr(link, 'inwardIssue'):
                    if 'PRD' in link.inwardIssue.fields.summary.upper():
                        prd_url = f"{self.url}/browse/{link.inwardIssue.key}"
            
            return {
                'key': issue.key,
                'summary': issue.fields.summary,
                'reporter': issue.fields.reporter.displayName if issue.fields.reporter else "Unknown",
                'status': issue.fields.status.name,
                'project_name': issue.fields.project.name,
                'prd_url': prd_url,
                'id': issue.id
            }
        except Exception as e:
            logging.error(f"이슈 정보 조회 실패 ({issue_key}): {e}")
            return None

    def fetch_defects(self, qa_task_key):
        """특정 QA 태스크와 연결된 Defect 데이터를 가져와 DataFrame으로 반환합니다."""
        jql = f'issue in linkedIssues("{qa_task_key}") AND issuetype = Defect'
        try:
            data = []
            next_token = None
            page_size = 50
            while True:
                kwargs = {'maxResults': page_size}
                if next_token:
                    kwargs['nextPageToken'] = next_token
                
                issues = self.jira.enhanced_search_issues(jql, **kwargs)
                if not issues:
                    break
                    
                for issue in issues:
                    data.append({
                        'Key': issue.key,
                        'Summary': issue.fields.summary,
                        'Status': issue.fields.status.name,
                        'Priority': issue.fields.priority.name if issue.fields.priority else 'None',
                        'Reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
                        'Created': pd.to_datetime(issue.fields.created)
                    })
                
                next_token = getattr(issues, 'nextPageToken', None)
                if not next_token:
                    break
                    
            logging.info(f"총 {len(data)}개 Defect 조회 완료 (프로젝트 무관, 링크 기반)")
            return pd.DataFrame(data)
        except Exception as e:
            logging.error(f"Defect 데이터 가져오기 실패: {e}")
            return pd.DataFrame()

