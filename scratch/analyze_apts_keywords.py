import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira import JIRA
from config.settings import settings
import re

def analyze_apts_keywords():
    jira = JIRA(
        server=settings.ATLASSIAN_URL,
        basic_auth=(settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN),
        options={'verify': False}
    )
    
    user_email = "jamie@aijinet.com"
    year = 2026
    start_date = f"{year}-01-01"
    end_date = "2026-12-31"
    jql = f'project = APTS AND created >= "{start_date}" AND created <= "{end_date}"'
    issues = jira.search_issues(jql, maxResults=False, fields='summary')
    
    keywords = {
        'planner': 0,
        'bodoc': 0,
        'other': 0
    }
    
    for iss in issues:
        summary = iss.fields.summary.lower()
        if 'planner' in summary or '플래너' in summary:
            keywords['planner'] += 1
        elif 'bodoc' in summary or '보닥' in summary:
            keywords['bodoc'] += 1
        else:
            keywords['other'] += 1
            
    print(f"APTS 2025 keyword analysis:")
    print(keywords)
    
    if keywords['other'] > 0:
        print("\nExamples of 'other' issues:")
        others = [iss for iss in issues if not ('planner' in iss.fields.summary.lower() or '플래너' in iss.fields.summary.lower() or 'bodoc' in iss.fields.summary.lower() or '보닥' in iss.fields.summary.lower())]
        for iss in others[:10]:
            print(f"- {iss.key}: {iss.fields.summary}")

if __name__ == "__main__":
    analyze_apts_keywords()
