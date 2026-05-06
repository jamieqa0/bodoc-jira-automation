import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jira import JIRA
from config.settings import settings
import re

def debug_counts_2026():
    jira = JIRA(
        server=settings.ATLASSIAN_URL,
        basic_auth=(settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN),
        options={'verify': False}
    )
    
    user_email = "jamie@aijinet.com"
    year = 2026
    start_date = f"{year}-01-01"
    end_date = "2026-05-06"
    
    jql = (
        f'((assignee = "{user_email}" OR reporter = "{user_email}") OR project = "SQA") '
        f'AND created >= "{start_date}" AND created <= "{end_date}"'
    )
    
    issues = jira.search_issues(jql, maxResults=False, fields='key,summary,project,fixVersions')
    
    categories = {
        'Bodoc 4.0': 0,
        'Planner & B2B': 0,
        'SQA': 0
    }
    
    apts_breakdown = {
        'Bodoc': 0,
        'Planner': 0,
        'Other': 0
    }
    
    other_issues = []
    for iss in issues:
        project_key = iss.fields.project.key
        summary = iss.fields.summary.lower()
        versions = [v.name.lower() for v in getattr(iss.fields, 'fixVersions', [])]
        v_str = " ".join(versions)
        
        if project_key == 'SQA':
            categories['SQA'] += 1
            continue
            
        if project_key == 'APTS':
            if '플래너' in v_str or 'planner' in v_str or '플래너' in summary or 'planner' in summary:
                categories['Planner & B2B'] += 1
                apts_breakdown['Planner'] += 1
            elif '보닥' in v_str or 'bodoc' in v_str or '보닥' in summary or 'bodoc' in summary:
                categories['Bodoc 4.0'] += 1
                apts_breakdown['Bodoc'] += 1
            else:
                categories['Planner & B2B'] += 1
                apts_breakdown['Other'] += 1
                other_issues.append((iss.key, iss.fields.summary))
        elif project_key == 'BODOCRUN':
            categories['Bodoc 4.0'] += 1
        else:
            if '보닥' in iss.fields.project.name or 'Bodoc' in iss.fields.project.name:
                categories['Bodoc 4.0'] += 1
            else:
                categories['Planner & B2B'] += 1
                
    print(f"Counts for 2026:")
    print(categories)
    print(f"\nAPTS Breakdown:")
    print(apts_breakdown)
    print(f"\nAPTS 'Other' Issues ({len(other_issues)}):")
    for k, s in other_issues:
        print(f"- {k}: {s}")

if __name__ == "__main__":
    debug_counts_2026()
