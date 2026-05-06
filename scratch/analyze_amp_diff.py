import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira import JIRA
from config.settings import settings
import re

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
    
    all_issues = jira.search_issues(jql, maxResults=False)
    
    loose_amp = []
    strict_amp = []
    
    amp_regex = re.compile(r'\[amplitude\]', re.IGNORECASE)
    
    for iss in all_issues:
        summary = iss.fields.summary
        if amp_regex.search(summary):
            strict_amp.append(iss)
        if 'amplitude' in summary.lower():
            loose_amp.append(iss)
            
    print(f"Strict count: {len(strict_amp)}")
    print(f"Loose count: {len(loose_amp)}")
    
    # Check if any are in SQA
    sqa_amp = [iss for iss in loose_amp if iss.fields.project.key == 'SQA']
    print(f"Loose Amplitude issues in SQA: {len(sqa_amp)}")
    
    # Difference
    diff = [iss for iss in loose_amp if iss.key not in [s.key for s in strict_amp]]
    print("\nExample of loose matches NOT caught by strict regex:")
    for iss in diff[:10]:
        print(f"- {iss.key}: {iss.fields.summary}")

if __name__ == "__main__":
    check_counts()
