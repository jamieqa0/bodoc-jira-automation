# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 실행 명령어

프로젝트 루트에서 실행해야 합니다.

```bash
# 의존성 설치
pip install -r requirements.txt

# Jira 연결 및 설정 디버깅
python bin/debug_jira.py

# 테스트 플랜 생성 → Confluence 게시
python bin/run_test_plan.py SQA-122

# QA 결과 보고서 생성 → Confluence 게시 (차트 포함)
python bin/run_qa_report.py SQA-119

# MOR Report 초안만 로컬 파일로 생성 (mor_draft_YYYY-MM.md)
python bin/run_mor_report.py --month 2026-04

# MOR Report 생성 및 Confluence 게시
python bin/run_mor_report.py --month 2026-04 --publish

# (필요시) 로컬 마크다운 파일을 읽어서 게시
python bin/run_mor_report.py --month 2026-04 --draft mor_draft_2026-04.md --publish

# 연간 업무 성과 보고서 생성 → Confluence 게시
python bin/run_annual_report.py --year 2025
python bin/run_annual_report.py --year 2026 --user jamie@aijinet.com

# 모든 명령어에 --quiet 옵션 추가 시 간단한 출력만 표시 (SUCCESS/ERROR)
```

## 환경 설정

프로젝트 루트에 `.env` 파일이 있어야 실행됩니다. `.env.sample` 참고:

| 변수                             | 필수 | 설명                                                         |
| -------------------------------- | ---- | ------------------------------------------------------------ |
| `ATLASSIAN_URL`                  | O    | Jira/Confluence 도메인 (예: `https://bodocqa.atlassian.net`) |
| `ATLASSIAN_USER`                 | O    | Atlassian 계정 이메일                                        |
| `ATLASSIAN_API_TOKEN`            | O    | Atlassian API 토큰                                           |
| `JIRA_PROJECT_KEY`               | -    | Jira 프로젝트 키 (기본값: `APTS`)                            |
| `CONFLUENCE_SPACE_KEY`           | -    | Confluence 공간 키                                           |
| `CONFLUENCE_QA_REPORT_PARENT_ID` | -    | QA Report 페이지 부모 ID                                     |
| `CONFLUENCE_TEST_PLAN_PARENT_ID` | -    | Test Plan 페이지 부모 ID                                     |
| `CONFLUENCE_MOR_PARENT_ID`       | -    | MOR Report 및 연간 보고서 페이지 부모 ID                     |

API 토큰 발급: https://id.atlassian.com/manage-profile/security/api-tokens

## MOR 워크플로우

1. **데이터 기반 초안 생성 및 게시**: `python bin/run_mor_report.py --month 2026-04 --publish`
2. **Confluence에서 직접 편집**: 생성된 "MOR 초안" 페이지를 웹에서 직접 수정하여 최종 확정 (이후 별도 스크립트 실행 불필요)

## 아키텍처

### QA 보고서 (run_test_plan.py / run_qa_report.py)

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

### MOR 보고서 (run_mor_report.py)

```
bin/run_mor_report.py --month YYYY-MM [--user email] [--publish] [--draft file.md]
  1. 데이터 로드 (draft 미지정 시):
     → JiraClient.fetch_user_issues(user, month)
     → ConfluenceClient.fetch_user_pages(user, month)
     → MorGenerator.generate_draft(data)
  2. 출력/게시:
     → publish 지정 시: Markdown → HTML → Jinja2(mor_template.html) → Confluence 게시
     → publish 미지정 시: mor_draft_YYYY-MM.md 로컬 저장
```

### 연간 보고서 (run_annual_report.py)

```
bin/run_annual_report.py --year YYYY [--user email] [--quiet]
  → ConfluenceClient.get_user_info(email)  →  accountId + displayName 조회
  → JiraClient: SQA 프로젝트(작업관리) / 타 프로젝트(결함) 분리 수집
  → ConfluenceClient.fetch_user_pages()  →  글로벌 스페이스 페이지만 조회
  → HTML 보고서 생성 (각 수치에 JQL 링크 포함)
  → ConfluenceClient.publish_page()  →  CONFLUENCE_MOR_PARENT_ID 하위에 게시
  - 과거 연도: 1월~12월 전체 / 현재 연도: 오늘까지 자동 설정
  - 기존 페이지 있으면 업데이트, 없으면 신규 생성
```

### 핵심 모듈

- `config/settings.py` — `.env` 로드 및 필수값 검증. 모듈 임포트 시점에 `settings.validate()` 자동 실행
- `core/clients/jira.py` — `jira` 패키지 사용. `fetch_defects()`는 50개씩 페이지네이션, `fetch_user_issues()`는 사용자별 월간 이슈 조회
- `core/clients/confluence.py` — `atlassian` 패키지 사용. 페이지 존재 시 업데이트, 없으면 생성
  - `get_user_info(email)` — `/rest/api/user/current` 또는 검색 API로 `accountId`·`displayName` 반환
  - `fetch_user_pages(email, month)` — Atlassian Cloud CQL은 이메일 대신 `accountId` 필요. `type = page AND space.type = "global"` 필터로 첨부파일·댓글·개인 스페이스 제외
- `core/mor_generator.py` — 템플릿 기반으로 MOR 5항목 자동 서술 생성
- `core/utils.py` — 버전/프로젝트명 추출 (`[보닥앱] MAINTENANCE_4.9.1` 형식 파싱)
- `core/templates/` — Jinja2 HTML 템플릿. QA/테스트플랜은 Confluence 스토리지 형식(`<ac:structured-macro>`), MOR는 일반 HTML5

## 주요 동작 특성

**해결률 계산**: `resolutiondate IS NOT NULL OR status in {'Prod 배포완료', '종료', 'Resolved', ...}` 조합으로 판단. `resolutiondate` 단독으로는 부정확 — Jira에서 "Prod 배포완료" 상태가 `resolutiondate` 없이 설정되는 케이스 존재.

**SQA vs 결함 분리**: 연간 보고서에서 `project.key == 'SQA'`인 이슈는 작업관리, 나머지는 결함으로 분류.

**Amplitude 이슈 분리**: Summary에 `[Amplitude]`가 포함된 Defect는 전체 통계와 별도 섹션 및 차트로 분리됩니다.

**PRD 링크 자동 탐색**: Jira 이슈의 linked issues 중 Summary에 "PRD"가 포함된 항목을 자동으로 연결합니다.

**한국어 폰트**: matplotlib 차트가 한국어를 표시할 수 있도록 플랫폼별 폰트를 자동 선택합니다 (Windows: Malgun Gothic).

**SSL 검증 비활성화**: Jira/Confluence 연결 시 `verify=False`. 프로덕션 환경 전환 시 수정 필요합니다.
