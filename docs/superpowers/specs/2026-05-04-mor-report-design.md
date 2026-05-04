# MOR Report 기능 설계

**날짜:** 2026-05-04
**프로젝트:** bodoc-jira-automation

## Context

MOR(Monthly Operation Report)은 매월 마지막 주 목요일에 인당 5분씩 진행되는 업무 성과 발표다. 현재 수동으로 작성하는 이 보고서를 Jira/Confluence 데이터에서 자동으로 초안을 생성하고, 사용자가 검토·편집 후 Confluence에 게시하는 방식으로 자동화한다.

---

## 아키텍처

```
bin/run_mor_report.py --month 2026-04 [--user email]
  └─ JiraClient.fetch_user_issues(user, month)
  └─ ConfluenceClient.fetch_user_pages(user, month)
  └─ MorGenerator.generate_draft(data)
  └─ mor_draft_2026-04.md 로컬 저장

(사용자 편집)

bin/publish_mor.py --month 2026-04 [--user email]
  └─ mor_draft_2026-04.md 읽기
  └─ Markdown → Confluence HTML 변환
  └─ ConfluenceClient.publish_page()
  └─ 페이지 URL 출력
```

---

## 컴포넌트

### 신규 파일

| 파일 | 역할 |
|------|------|
| `bin/run_mor_report.py` | 데이터 수집 + 초안 생성 진입점 |
| `bin/publish_mor.py` | 로컬 초안 → Confluence 게시 진입점 |
| `core/mor_generator.py` | Claude API 호출, MOR 5항목 서술 생성 |
| `core/templates/mor_template.html` | Confluence 게시용 HTML 템플릿 |

### 기존 파일 수정

| 파일 | 변경 내용 |
|------|-----------|
| `core/clients/jira.py` | `fetch_user_issues(user_email, year_month)` 메서드 추가 |
| `core/clients/confluence.py` | `fetch_user_pages(user_email, year_month)` 메서드 추가 |
| `config/settings.py` | `CONFLUENCE_MOR_PARENT_ID` 추가 |
| `.env.sample` | `CONFLUENCE_MOR_PARENT_ID` 추가 |

---

## 데이터 수집 상세

### Jira: fetch_user_issues()

JQL:
```
(assignee = "{user}" OR reporter = "{user}")
AND created >= "{year_month}-01"
AND created <= "{year_month}-{last_day}"
ORDER BY created DESC
```

수집 필드: key, summary, status, priority, component, created, resolutiondate, comments

### Confluence: fetch_user_pages()

Confluence REST API를 사용해 해당 월에 생성하거나 마지막으로 수정한 페이지를 조회한다.

수집 필드: title, space, created, lastModified, url, body excerpt (300자)

---

## MOR 초안 생성 (Claude API)

`core/mor_generator.py`에서 수집 데이터를 `claude-sonnet-4-6`에 전달해 5개 항목을 한국어로 서술한다.

**MOR 5개 항목:**
1. 한 달 동안 진행한 업무
2. 본인의 구체적인 담당 영역
3. 전문 기여 포인트
4. 업무 진행의 의도 설명
5. 문제 해결 또는 생산성 향상을 위한 노력

각 항목은 3-5문장의 한국어 서술로 생성된다. 출력은 마크다운 형식으로 `mor_draft_{year_month}.md`에 저장된다.

---

## 사용자 지정

| 방식 | 명령 |
|------|------|
| 기본 (본인) | `python bin/run_mor_report.py --month 2026-04` |
| 다른 사람 | `python bin/run_mor_report.py --month 2026-04 --user other@company.com` |

기본값은 `.env`의 `ATLASSIAN_USER`.

---

## 환경 변수

`.env`에 추가 필요:
```
CONFLUENCE_MOR_PARENT_ID=<MOR 페이지 부모 ID>
```

Confluence 페이지 제목 형식: `MOR 2026-04 - Jamie`

---

## 실행 흐름

```bash
# 1단계: 초안 생성
python bin/run_mor_report.py --month 2026-04

# 2단계: 파일 편집 (VS Code 등)
# mor_draft_2026-04.md

# 3단계: Confluence 게시
python bin/publish_mor.py --month 2026-04
```

---

## 검증 방법

1. `run_mor_report.py` 실행 후 `mor_draft_2026-04.md` 생성 확인
2. 파일에 5개 MOR 항목이 한국어로 서술되어 있는지 확인
3. `publish_mor.py` 실행 후 Confluence URL 출력 확인
4. Confluence에서 페이지 제목, 내용, 부모 페이지 위치 확인
