# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 실행 명령어

프로젝트 루트에서 실행해야 합니다.

```bash
# 의존성 설치
pip install -r requirements.txt

# 테스트 플랜 생성 → Confluence 게시
python bin/run_test_plan.py SQA-122

# QA 결과 보고서 생성 → Confluence 게시 (차트 포함)
python bin/run_qa_report.py SQA-119

# MOR 초안 바로 Confluence에 게시 (편집용)
python bin/run_mor_report.py --month 2026-04 --user jamie@aijinet.com --publish --quiet

# MOR 초안 생성 (로컬 파일 저장)
python bin/run_mor_report.py --month 2026-04 --user jamie@aijinet.com

# MOR 최종 버전 게시 (로컬 파일에서 읽어서 게시)
python bin/publish_mor.py --month 2026-04 --user jamie@aijinet.com

# 모든 명령어에 --quiet 옵션 추가 시 간단한 출력만 표시 (SUCCESS/ERROR)
```

## 환경 설정

프로젝트 루트에 `.env` 파일이 있어야 실행됩니다. `.env.sample` 참고:

| 변수 | 필수 | 설명 |
|------|------|------|
| `ATLASSIAN_URL` | O | Jira/Confluence 도메인 (예: `https://bodocqa.atlassian.net`) |
| `ATLASSIAN_USER` | O | Atlassian 계정 이메일 |
| `ATLASSIAN_API_TOKEN` | O | Atlassian API 토큰 |
| `CONFLUENCE_SPACE_KEY` | - | Confluence 공간 키 |
| `CONFLUENCE_QA_REPORT_PARENT_ID` | - | QA Report 페이지 부모 ID |
| `CONFLUENCE_TEST_PLAN_PARENT_ID` | - | Test Plan 페이지 부모 ID |
| `CONFLUENCE_MOR_PARENT_ID` | - | MOR Report 페이지 부모 ID |

API 토큰 발급: https://id.atlassian.com/manage-profile/security/api-tokens

## MOR 워크플로우

### 추천 워크플로우 (Confluence 편집)
1. **초안 생성 및 게시**: `python bin/run_mor_report.py --month 2026-04 --user jamie@aijinet.com --publish`
2. **Confluence에서 편집**: 생성된 "MOR 초안" 페이지를 웹에서 직접 수정
3. **최종 게시**: `python bin/publish_mor.py --month 2026-04 --user jamie@aijinet.com`

### 기존 워크플로우 (로컬 편집)
1. **초안 생성**: `python bin/run_mor_report.py --month 2026-04 --user jamie@aijinet.com`
2. **로컬 편집**: `mor_draft_2026-04.md` 파일을 텍스트 에디터로 수정
3. **게시**: `python bin/publish_mor.py --month 2026-04 --user jamie@aijinet.com`

## 아키텍처

```
bin/run_*.py (진입점)
  → JiraClient.fetch_defects(qa_task_key)
      JQL: linkedIssues("QA-KEY") AND issuetype = Defect
      → pandas DataFrame (Key, Summary, Status, Priority, Reporter, Created)
  → analyze_data()  →  status_counts, priority_counts, amplitude_counts
  → generate_charts()  →  BytesIO PNG (in-memory, 파일 I/O 없음)
  → Jinja2 템플릿 렌더링 (core/templates/*.html)
  → ConfluenceClient.publish_page()  →  create/update Jira 매크로 포함 HTML 페이지
  → ConfluenceClient.attach_file()  →  PNG 차트 첨부
```

MOR 기능 아키텍처:
```
bin/run_mor_report.py --month YYYY-MM [--user email]
  → JiraClient.fetch_user_issues(user, month)
      JQL: (assignee = "user" OR reporter = "user") AND created >= "YYYY-MM-01" AND created <= "YYYY-MM-last"
      → List of issues (key, summary, status, priority, components, created, resolutiondate, comments)
  → ConfluenceClient.fetch_user_pages(user, month)
      CQL: (creator = "user" OR lastModifier = "user") AND (created >= "YYYY-MM-01" OR lastModified >= "YYYY-MM-01")
      → List of pages (title, space, created, lastModified, url, excerpt)
  → MorGenerator.generate_draft(data)
      → 템플릿 기반 MOR 5항목 서술
      → mor_draft_YYYY-MM.md 로컬 저장

bin/run_mor_report.py --month YYYY-MM [--user email] --publish
  → 위와 동일한 데이터 수집 + 초안 생성
  → Markdown → HTML 변환
  → Confluence에 "MOR 초안" 페이지 생성 (편집용)

bin/publish_mor.py --month YYYY-MM [--user email]
  → mor_draft_YYYY-MM.md 읽기
  → Markdown → HTML 변환
  → Jinja2 템플릿 렌더링 (core/templates/mor_template.html)
  → ConfluenceClient.publish_page() → MOR Report 페이지 생성/업데이트
```

### 핵심 모듈

- `config/settings.py` — `.env` 로드 및 필수값 검증. 모듈 임포트 시점에 `settings.validate()` 자동 실행
- `core/clients/jira.py` — `jira` 패키지 사용. `fetch_defects()`는 50개씩 페이지네이션, `fetch_user_issues()`는 사용자별 월간 이슈 조회
- `core/clients/confluence.py` — `atlassian` 패키지 사용. 페이지 존재 시 업데이트, 없으면 생성. `fetch_user_pages()`는 사용자별 월간 페이지 조회
- `core/mor_generator.py` — 템플릿 기반으로 MOR 5항목 자동 서술 생성
- `core/utils.py` — 버전/프로젝트명 추출 (`[보닥앱] MAINTENANCE_4.9.1` 형식 파싱)
- `core/templates/` — Jinja2 HTML 템플릿. Confluence 스토리지 형식(`<ac:structured-macro>`) 사용

## 주요 동작 특성

**Amplitude 이슈 분리**: Summary에 `[Amplitude]`가 포함된 Defect는 전체 통계와 별도 섹션 및 차트로 분리됩니다.

**해결률 계산**: `['Resolved', 'Closed', 'Done', 'Verified', '해결됨', '완료', '종료']` 상태를 해결된 것으로 집계합니다.

**PRD 링크 자동 탐색**: Jira 이슈의 linked issues 중 Summary에 "PRD"가 포함된 항목을 자동으로 연결합니다.

**MOR 5항목 자동 생성**: Jira/Confluence 데이터를 기반으로 업무 성과 보고서의 5개 항목을 템플릿 기반으로 자동 서술합니다.

**한국어 폰트**: matplotlib 차트가 한국어를 표시할 수 있도록 플랫폼별 폰트를 자동 선택합니다 (Windows: Malgun Gothic).

**SSL 검증 비활성화**: Jira/Confluence 연결 시 `verify=False`. 프로덕션 환경 전환 시 수정 필요합니다.
