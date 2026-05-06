import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira import JIRA
from config.settings import settings
import json

def inspect_apts_issues():
    jira = JIRA(
        server=settings.ATLASSIAN_URL,
        basic_auth=(settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN),
        options={'verify': False}
    )
    
    jql = 'project = APTS ORDER BY created DESC'
    issues = jira.search_issues(jql, maxResults=10, fields='key,summary,components,labels')
    
    print(f"Inspecting 10 issues from APTS project:")
    for iss in issues:
        components = [c.name for c in getattr(iss.fields, 'components', [])]
        labels = getattr(iss.fields, 'labels', [])
        print(f"- {iss.key}: {iss.fields.summary}")
        print(f"  Components: {components}")
        print(f"  Labels: {labels}")
        print("-" * 20)

if __name__ == "__main__":
    inspect_apts_issues()
