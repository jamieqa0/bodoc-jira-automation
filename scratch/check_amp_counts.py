import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira import JIRA
from config.settings import settings

def check_counts():
    jira = JIRA(
        server=settings.ATLASSIAN_URL,
        basic_auth=(settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN),
        options={'verify': False}
    )
    
    user_email = "jamie@aijinet.com"
    year = 2025
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    jql = (
        f'((assignee = "{user_email}" OR reporter = "{user_email}") OR project = "SQA") '
        f'AND created >= "{start_date}" AND created <= "{end_date}"'
    )
    
    # 1. Total count according to Jira
    issues = jira.search_issues(jql, maxResults=0)
    print(f"Total issues fetched with maxResults=0: {len(issues)}")
    print(f"Total issues reported by search_issues: {issues.total}")
    
    # 2. Count Amplitude issues with current regex [amplitude]
    import re
    amp_regex = re.compile(r'\[amplitude\]', re.IGNORECASE)
    amp_count_brackets = 0
    amp_count_loose = 0
    
    # Let's fetch more just in case
    all_issues = jira.search_issues(jql, maxResults=False)
    print(f"Total issues fetched with maxResults=False: {len(all_issues)}")
    
    for iss in all_issues:
        if amp_regex.search(iss.fields.summary):
            amp_count_brackets += 1
        if 'amplitude' in iss.fields.summary.lower():
            amp_count_loose += 1
            
    print(f"Amplitude count with [amplitude]: {amp_count_brackets}")
    print(f"Amplitude count with loose 'amplitude': {amp_count_loose}")

if __name__ == "__main__":
    check_counts()
