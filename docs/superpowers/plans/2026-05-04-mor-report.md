# MOR Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jira/Confluence 데이터를 수집하고 Claude API로 MOR 5항목 초안을 생성한 뒤, 사용자가 편집 후 Confluence에 게시하는 2단계 자동화 파이프라인을 구현한다.

**Architecture:** `run_mor_report.py`가 Jira+Confluence 데이터를 수집하고 `MorGenerator`가 Claude API로 초안 마크다운을 생성한다. 사용자가 편집 후 `publish_mor.py`가 마크다운을 Confluence HTML로 변환해 게시한다.

**Tech Stack:** Python 3.12, `anthropic`, `atlassian-python-api`, `jira`, `python-dotenv`, `markdown` (new dependency)

---

## 파일 구조

| 파일 | 역할 |
|------|------|
| `bin/run_mor_report.py` (신규) | 데이터 수집 + 초안 생성 진입점 |
| `bin/publish_mor.py` (신규) | 로컬 초안 → Confluence 게시 진입점 |
| `core/mor_generator.py` (신규) | Claude API 호출, MOR 5항목 서술 생성 |
| `core/templates/mor_template.html` (신규) | Confluence 게시용 HTML 템플릿 |
| `core/clients/jira.py` (수정) | `fetch_user_issues()` 메서드 추가 |
| `core/clients/confluence.py` (수정) | `fetch_user_pages()` 메서드 추가 |
| `config/settings.py` (수정) | `CONFLUENCE_MOR_PARENT_ID` 추가 |
| `.env.sample` (수정) | `CONFLUENCE_MOR_PARENT_ID` 추가 |
| `requirements.txt` (수정) | `anthropic`, `markdown` 패키지 추가 |

---

## Task 1: 의존성 및 설정 추가

**Files:**
- Modify: `requirements.txt`
- Modify: `config/settings.py`
- Modify: `.env.sample`

- [ ] **Step 1: requirements.txt에 패키지 추가**

```
anthropic>=0.49.0
markdown>=3.8
```

`requirements.txt` 하단에 추가한다:

```
atlassian-python-api>=4.0.7
jira>=3.10.5
pandas>=3.0.0
matplotlib>=3.10.8
Jinja2>=3.1.6
python-dotenv>=1.2.1
requests>=2.32.5
urllib3>=2.5.0
anthropic>=0.49.0
markdown>=3.8
```

- [ ] **Step 2: settings.py에 MOR 설정 추가**

`config/settings.py`의 `CONFLUENCE_TEST_PLAN_PARENT_ID` 줄 바로 아래에 추가한다:

```python
CONFLUENCE_MOR_PARENT_ID = os.getenv("CONFLUENCE_MOR_PARENT_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

- [ ] **Step 3: .env.sample에 MOR 변수 추가**

`.env.sample` 하단에 추가한다:

```
CONFLUENCE_MOR_PARENT_ID=your_mor_parent_page_id_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

- [ ] **Step 4: 패키지 설치 확인**

```bash
pip install anthropic markdown
```

Expected: `Successfully installed anthropic-...` 또는 `already satisfied`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt config/settings.py .env.sample
git commit -m "feat: add anthropic, markdown deps and MOR env settings"
```

---

## Task 2: JiraClient에 fetch_user_issues() 추가

**Files:**
- Modify: `core/clients/jira.py:84` (끝 부분)
- Test: 직접 실행으로 확인 (Task 6에서 통합 검증)

- [ ] **Step 1: fetch_user_issues 메서드 작성**

`core/clients/jira.py`의 `fetch_defects` 메서드 뒤에 추가한다:

```python
def fetch_user_issues(self, user_email, year_month):
    """지정한 월에 사용자가 담당하거나 보고한 이슈를 가져옵니다."""
    import calendar
    year, month = map(int, year_month.split('-'))
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year_month}-01"
    end_date = f"{year_month}-{last_day:02d}"

    jql = (
        f'(assignee = "{user_email}" OR reporter = "{user_email}") '
        f'AND created >= "{start_date}" '
        f'AND created <= "{end_date}" '
        f'ORDER BY created DESC'
    )
    try:
        issues = self.jira.search_issues(jql, maxResults=100,
                                         fields='key,summary,status,priority,components,created,resolutiondate,comment')
        result = []
        for issue in issues:
            comments = []
            comment_field = getattr(issue.fields, 'comment', None)
            if comment_field:
                for c in comment_field.comments[:3]:
                    comments.append(c.body[:200])
            result.append({
                'key': issue.key,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                'components': [comp.name for comp in getattr(issue.fields, 'components', [])],
                'created': str(issue.fields.created)[:10],
                'resolutiondate': str(issue.fields.resolutiondate)[:10] if issue.fields.resolutiondate else None,
                'comments': comments,
            })
        logging.info(f"{year_month} {user_email} 이슈 {len(result)}개 조회 완료")
        return result
    except Exception as e:
        logging.error(f"fetch_user_issues 실패: {e}")
        return []
```

- [ ] **Step 2: 빠른 수동 검증**

```bash
python -c "
import sys, os
sys.path.append('.')
from config.settings import settings
from core.clients.jira import JiraClient
import urllib3; urllib3.disable_warnings()
jira = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
issues = jira.fetch_user_issues(settings.ATLASSIAN_USER, '2026-04')
print(f'이슈 수: {len(issues)}')
if issues: print(issues[0])
"
```

Expected: `이슈 수: N` (N >= 0, 오류 없음)

- [ ] **Step 3: Commit**

```bash
git add core/clients/jira.py
git commit -m "feat: add fetch_user_issues() to JiraClient"
```

---

## Task 3: ConfluenceClient에 fetch_user_pages() 추가

**Files:**
- Modify: `core/clients/confluence.py:67` (끝 부분)

- [ ] **Step 1: fetch_user_pages 메서드 작성**

`core/clients/confluence.py` 끝에 추가한다:

```python
def fetch_user_pages(self, user_email, year_month):
    """지정한 월에 사용자가 생성하거나 수정한 Confluence 페이지를 조회합니다."""
    year, month = year_month.split('-')
    start = f"{year_month}-01T00:00:00.000Z"
    import calendar
    last_day = calendar.monthrange(int(year), int(month))[1]
    end = f"{year_month}-{last_day:02d}T23:59:59.000Z"

    try:
        # CQL로 해당 월에 기여한 페이지 조회
        cql = (
            f'type = "page" AND contributor = "{user_email}" '
            f'AND lastModified >= "{year_month}-01" '
            f'AND lastModified <= "{year_month}-{last_day:02d}"'
        )
        pages = self.confluence.cql(cql, limit=50, expand='version,space,body.view')
        result = []
        if not pages or 'results' not in pages:
            return result
        for page in pages['results']:
            body_text = ''
            try:
                body_html = page.get('body', {}).get('view', {}).get('value', '')
                import re
                body_text = re.sub(r'<[^>]+>', '', body_html)[:300]
            except Exception:
                pass
            result.append({
                'title': page.get('title', ''),
                'space': page.get('space', {}).get('name', ''),
                'created': page.get('version', {}).get('when', '')[:10],
                'url': f"{self.url}/wiki{page.get('_links', {}).get('webui', '')}",
                'excerpt': body_text.strip(),
            })
        logging.info(f"{year_month} Confluence 페이지 {len(result)}개 조회 완료")
        return result
    except Exception as e:
        logging.error(f"fetch_user_pages 실패: {e}")
        return []
```

- [ ] **Step 2: 빠른 수동 검증**

```bash
python -c "
import sys
sys.path.append('.')
from config.settings import settings
from core.clients.confluence import ConfluenceClient
import urllib3; urllib3.disable_warnings()
conf = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
pages = conf.fetch_user_pages(settings.ATLASSIAN_USER, '2026-04')
print(f'페이지 수: {len(pages)}')
if pages: print(pages[0])
"
```

Expected: `페이지 수: N` (N >= 0, 오류 없음)

- [ ] **Step 3: Commit**

```bash
git add core/clients/confluence.py
git commit -m "feat: add fetch_user_pages() to ConfluenceClient"
```

---

## Task 4: MorGenerator 구현

**Files:**
- Create: `core/mor_generator.py`

- [ ] **Step 1: mor_generator.py 작성**

```python
import os
import anthropic
import logging


MOR_PROMPT_TEMPLATE = """다음은 {user}의 {year_month} 업무 데이터입니다.

[Jira 이슈 목록]
{jira_data}

[Confluence 페이지 목록]
{confluence_data}

아래 5개 항목을 각각 3-5문장의 한국어 서술로 작성해주세요.
각 항목은 "## 항목N. 제목" 형식의 마크다운 헤더로 시작하세요.

## 항목1. 한 달 동안 진행한 업무

## 항목2. 본인의 구체적인 담당 영역

## 항목3. 전문 기여 포인트

## 항목4. 업무 진행의 의도 설명

## 항목5. 문제 해결 또는 생산성 향상을 위한 노력
"""


class MorGenerator:
    def __init__(self, api_key=None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        self.client = anthropic.Anthropic(api_key=key)

    def _format_jira(self, issues):
        if not issues:
            return "(데이터 없음)"
        lines = []
        for i in issues:
            comp = ', '.join(i['components']) if i['components'] else '-'
            lines.append(
                f"- [{i['key']}] {i['summary']} | 상태: {i['status']} | 우선순위: {i['priority']} | 컴포넌트: {comp}"
            )
        return '\n'.join(lines)

    def _format_confluence(self, pages):
        if not pages:
            return "(데이터 없음)"
        lines = []
        for p in pages:
            excerpt = p['excerpt'][:150] if p['excerpt'] else '-'
            lines.append(f"- {p['title']} ({p['space']}) | {p['created']}\n  {excerpt}")
        return '\n'.join(lines)

    def generate_draft(self, user_email, year_month, jira_issues, confluence_pages):
        """Claude API를 호출해 MOR 5항목 초안 마크다운을 반환합니다."""
        prompt = MOR_PROMPT_TEMPLATE.format(
            user=user_email,
            year_month=year_month,
            jira_data=self._format_jira(jira_issues),
            confluence_data=self._format_confluence(confluence_pages),
        )
        logging.info("Claude API로 MOR 초안 생성 중...")
        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
```

- [ ] **Step 2: 직접 실행으로 클래스 로드 확인**

```bash
python -c "
import sys
sys.path.append('.')
from core.mor_generator import MorGenerator
print('MorGenerator import OK')
"
```

Expected: `MorGenerator import OK`

- [ ] **Step 3: Commit**

```bash
git add core/mor_generator.py
git commit -m "feat: add MorGenerator using Claude API"
```

---

## Task 5: HTML 템플릿 작성

**Files:**
- Create: `core/templates/mor_template.html`

- [ ] **Step 1: mor_template.html 작성**

Confluence에 게시할 HTML 구조다. `{{ content }}` 자리에 마크다운을 변환한 HTML이 들어간다.

```html
<h1>MOR {{ year_month }} - {{ user_name }}</h1>
<p><strong>작성일:</strong> {{ today }}</p>
<hr />
{{ content }}
```

- [ ] **Step 2: 템플릿 파일 확인**

```bash
python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('core/templates'))
t = env.get_template('mor_template.html')
print(t.render(year_month='2026-04', user_name='Jamie', today='2026-04-30', content='<p>test</p>'))
"
```

Expected: `<h1>MOR 2026-04 - Jamie</h1>` 포함된 HTML 출력

- [ ] **Step 3: Commit**

```bash
git add core/templates/mor_template.html
git commit -m "feat: add MOR HTML template for Confluence"
```

---

## Task 6: run_mor_report.py 작성 (초안 생성 진입점)

**Files:**
- Create: `bin/run_mor_report.py`

- [ ] **Step 1: run_mor_report.py 작성**

```python
import os
import sys
import argparse
import logging
import urllib3
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.clients.jira import JiraClient
from core.clients.confluence import ConfluenceClient
from core.mor_generator import MorGenerator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_args():
    parser = argparse.ArgumentParser(description='MOR 초안 생성')
    parser.add_argument('--month', required=True, help='대상 월 (예: 2026-04)')
    parser.add_argument('--user', default=None, help='대상 사용자 이메일 (기본: ATLASSIAN_USER)')
    return parser.parse_args()


def main():
    args = parse_args()
    user_email = args.user or settings.ATLASSIAN_USER
    year_month = args.month

    logging.info(f"MOR 초안 생성 시작: {year_month} / {user_email}")

    jira = JiraClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    confluence = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)

    jira_issues = jira.fetch_user_issues(user_email, year_month)
    confluence_pages = confluence.fetch_user_pages(user_email, year_month)

    logging.info(f"Jira 이슈: {len(jira_issues)}개, Confluence 페이지: {len(confluence_pages)}개")

    generator = MorGenerator(api_key=settings.ANTHROPIC_API_KEY)
    draft = generator.generate_draft(user_email, year_month, jira_issues, confluence_pages)

    output_path = Path(settings.BASE_DIR) / f"mor_draft_{year_month}.md"
    output_path.write_text(draft, encoding='utf-8')
    logging.info(f"초안 저장 완료: {output_path}")
    print(f"\n초안이 생성되었습니다: {output_path}")
    print("파일을 편집한 후 publish_mor.py로 Confluence에 게시하세요.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 실행 테스트 (실제 API 호출)**

```bash
python bin/run_mor_report.py --month 2026-04
```

Expected:
- 로그에 `Jira 이슈: N개, Confluence 페이지: M개` 출력
- `mor_draft_2026-04.md` 파일 생성됨
- 파일 내용에 `## 항목1.` ~ `## 항목5.` 포함

- [ ] **Step 3: 파일 내용 확인**

```bash
python -c "print(open('mor_draft_2026-04.md', encoding='utf-8').read()[:500])"
```

Expected: 한국어 서술이 포함된 MOR 5항목 마크다운

- [ ] **Step 4: Commit**

```bash
git add bin/run_mor_report.py
git commit -m "feat: add run_mor_report.py entry point"
```

---

## Task 7: publish_mor.py 작성 (Confluence 게시 진입점)

**Files:**
- Create: `bin/publish_mor.py`

- [ ] **Step 1: publish_mor.py 작성**

```python
import os
import sys
import argparse
import logging
import urllib3
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.clients.confluence import ConfluenceClient
from jinja2 import Environment, FileSystemLoader
import markdown as md

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_args():
    parser = argparse.ArgumentParser(description='MOR 초안을 Confluence에 게시')
    parser.add_argument('--month', required=True, help='대상 월 (예: 2026-04)')
    parser.add_argument('--user', default=None, help='대상 사용자 이메일 (기본: ATLASSIAN_USER)')
    return parser.parse_args()


def get_user_name(user_email):
    return user_email.split('@')[0].split('.')[0].capitalize()


def main():
    args = parse_args()
    user_email = args.user or settings.ATLASSIAN_USER
    year_month = args.month
    user_name = get_user_name(user_email)

    draft_path = Path(settings.BASE_DIR) / f"mor_draft_{year_month}.md"
    if not draft_path.exists():
        print(f"초안 파일을 찾을 수 없습니다: {draft_path}")
        print(f"먼저 run_mor_report.py를 실행하세요.")
        sys.exit(1)

    draft_markdown = draft_path.read_text(encoding='utf-8')
    content_html = md.markdown(draft_markdown, extensions=['extra'])

    from core.utils import get_today_str
    jinja_env = Environment(loader=FileSystemLoader(str(settings.TEMPLATE_DIR)))
    template = jinja_env.get_template('mor_template.html')
    page_html = template.render(
        year_month=year_month,
        user_name=user_name,
        today=get_today_str(),
        content=content_html,
    )

    confluence = ConfluenceClient(settings.ATLASSIAN_URL, settings.ATLASSIAN_USER, settings.ATLASSIAN_API_TOKEN)
    page_title = f"MOR {year_month} - {user_name}"
    result = confluence.publish_page(
        space=settings.CONFLUENCE_SPACE_KEY,
        title=page_title,
        body=page_html,
        parent_id=settings.CONFLUENCE_MOR_PARENT_ID,
    )

    if result and result.get('id'):
        url = f"{settings.ATLASSIAN_URL}/wiki/spaces/{settings.CONFLUENCE_SPACE_KEY}/pages/{result['id']}"
        logging.info(f"게시 완료: {url}")
        print(f"\nConfluence 페이지가 게시되었습니다:")
        print(url)
    else:
        logging.error("게시에 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 초안 없을 때 오류 처리 확인**

```bash
python bin/publish_mor.py --month 2099-01
```

Expected: `초안 파일을 찾을 수 없습니다` 메시지 출력 후 종료

- [ ] **Step 3: 실제 게시 테스트 (CONFLUENCE_MOR_PARENT_ID 설정 필요)**

`.env`에 `CONFLUENCE_MOR_PARENT_ID`를 실제 값으로 설정한 후:

```bash
python bin/publish_mor.py --month 2026-04
```

Expected:
- `Confluence 페이지가 게시되었습니다:` 뒤에 URL 출력
- 브라우저에서 URL 확인: 제목 `MOR 2026-04 - Jamie`, 5개 항목 내용, 부모 페이지 위치 정상

- [ ] **Step 4: Commit**

```bash
git add bin/publish_mor.py
git commit -m "feat: add publish_mor.py to post MOR draft to Confluence"
```

---

## Task 8: CLAUDE.md 업데이트

**Files:**
- Modify: `CLAUDE.md` (프로젝트 루트 또는 전역)

- [ ] **Step 1: bodoc-jira-automation 섹션에 MOR 명령 추가**

전역 `CLAUDE.md`의 `bodoc-jira-automation` 섹션 명령 목록에 추가한다:

```bash
# MOR 초안 생성
python bin/run_mor_report.py --month 2026-04

# MOR Confluence 게시
python bin/publish_mor.py --month 2026-04
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md  # 또는 경로에 맞게 조정
git commit -m "docs: add MOR commands to CLAUDE.md"
```

---

## 최종 검증 체크리스트

```bash
# 1. 초안 생성
python bin/run_mor_report.py --month 2026-04

# 2. 생성 파일 확인
python -c "
content = open('mor_draft_2026-04.md', encoding='utf-8').read()
items = ['항목1', '항목2', '항목3', '항목4', '항목5']
for item in items:
    found = item in content
    print(f'{item}: {\"OK\" if found else \"MISSING\"}')"

# 3. 게시
python bin/publish_mor.py --month 2026-04
```

완료 기준:
- [ ] `mor_draft_2026-04.md` 생성, 5개 항목 한국어 서술 포함
- [ ] `publish_mor.py` 실행 후 Confluence URL 출력
- [ ] Confluence에서 제목 `MOR 2026-04 - Jamie`, 올바른 부모 페이지 위치 확인
