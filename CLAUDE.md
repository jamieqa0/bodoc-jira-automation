# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 실행 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# Web UI (주 사용 방식)
python app.py                          # http://localhost:5000

# CLI — 테스트 플랜 / QA 종료보고서
python bin/run_test_plan.py SQA-122
python bin/run_qa_report.py SQA-119

# CLI — 월간 업무보고서(MOR)
python bin/run_mor_report.py --month 2026-04            # 로컬 .md 초안 생성
python bin/run_mor_report.py --month 2026-04 --publish  # Confluence 직접 게시
python bin/run_mor_report.py --month 2026-04 --draft mor_draft_2026-04.md --publish  # 파일로 게시

# CLI — 연간 업무 보고서
python bin/run_annual_report.py --year 2025
python bin/run_annual_report.py --year 2026 --user user@example.com --quiet

# 연결 디버깅
python bin/debug_jira.py
```

---

## 환경 설정

`.env` (CLI용) 과 `config/ui_settings.json` (Web UI용) 두 가지 설정 경로가 병존합니다.

| 변수                             | 설명                                  |
| -------------------------------- | ------------------------------------- |
| `ATLASSIAN_URL`                  | `https://xxxx.atlassian.net`          |
| `ATLASSIAN_USER`                 | Atlassian 계정 이메일                 |
| `ATLASSIAN_API_TOKEN`            | API 토큰                              |
| `CONFLUENCE_SPACE_KEY`           | Confluence 공간 키                    |
| `CONFLUENCE_TEST_PLAN_PARENT_ID` | 테스트 플랜 부모 페이지 ID (선택)     |
| `CONFLUENCE_QA_REPORT_PARENT_ID` | QA 보고서 부모 페이지 ID (선택)       |
| `CONFLUENCE_MOR_PARENT_ID`       | MOR/연간 보고서 부모 페이지 ID (선택) |

`config/Settings` 클래스는 **import 시점**에 `validate()`를 실행합니다. Web UI에서는 `blueprints/reports.py`의 `_patch_settings()`로 런타임에 설정을 monkey-patch하므로, `.env` 없이도 Web UI가 동작합니다.

---

## 아키텍처

### 보고서 생성 흐름

```
[Entry]              [Generator]                    [Output]
bin/run_*.py    →    core/generators/*_generator.py  →  ConfluenceClient.publish_page()
app.py (Flask)  →    (same generators)               →  + attach_file() for charts
```

Web UI(`app.py`)는 `blueprints/reports.py`의 `/run` 엔드포인트가 백그라운드 스레드로 `_run_report()`를 실행하고, SSE(`/stream/<job_id>`)로 진행 상황을 브라우저에 스트리밍합니다.

### 핵심 모듈

- **`JiraClient`** (`core/clients/jira.py`): JQL 기반 이슈 수집, remote_links로 Figma/Confluence URL 추출, `fetch_defects()`는 pandas DataFrame 반환
- **`ConfluenceClient`** (`core/clients/confluence.py`): CQL 페이지 검색, 페이지 생성/업데이트, 이미지 첨부
- **`QAReportGenerator`** (`core/generators/qa_report_generator.py`): matplotlib 차트 생성 포함. 스레드 안전성을 위해 `Agg` 백엔드와 `_chart_lock` 사용
- **`AnnualGenerator`** (`core/generators/annual_report_generator.py`): Confluence `ac:layout` 3열 레이아웃으로 연간 보고서 렌더링

### Web UI 설정 흐름

1. `/settings` — `config/ui_settings.json`에 저장
2. `/run` POST — `load_ui_settings()`로 읽어 `_patch_settings()` 호출
3. 작업 완료 후 `_restore_settings()`로 원복

> **주의**: `_patch_settings()`는 module-level 전역 singleton을 수정합니다. 동시 요청 시 설정이 충돌할 수 있으므로 2인 이상이 동시에 생성하지 않도록 합니다.

---

## 비즈니스 규칙

### 이슈 분류 (연간 보고서 / MOR)

- `project = SQA` → QA 작업관리
- 그 외 `issuetype = Defect` → 결함 (반드시 Defect 타입만 집계)
- **APTS 프로젝트 세분화**: fixVersions 또는 summary에 `플래너/planner` 키워드 → `Planner & B2B`, `보닥/bodoc/android/ios/ai 상담사` → `Bodoc 4.0`, 해당 없으면 `Planner & B2B` 기본

### 해결률 계산

`resolutiondate`가 있거나 status가 `RESOLVED_STATUSES`(`core/utils.py`) 중 하나이면 해결 완료로 집계합니다.

### 버전/빌드번호 표시 조건

테스트 계획·QA 종료보고서 Summary 테이블에서 `버전/빌드번호` 행은 **SQA Task summary에 `보닥앱`이 포함된 경우에만** 표시합니다 (`show_version` 플래그).

### Figma / Confluence 링크 자동 추출

`JiraClient.get_issue_info()`에서 `jira.remote_links()`로 외부 링크를 조회해 URL 패턴(`figma.com`, `atlassian.net/wiki` 또는 `/wiki/`)으로 분류합니다.

### Amplitude 이슈

summary에 `Amplitude`(대소문자 무관) 포함 시 별도 섹션으로 분리합니다. QA 보고서에서는 차트도 별도 생성합니다.

---

## 템플릿 작성 규칙

- 템플릿은 **Confluence Storage Format** 기준입니다 (`<ac:structured-macro>`, `<ac:layout>` 등 사용).
- 줄바꿈이 그대로 렌더링되므로, `td` 안의 Jinja2 조건문은 반드시 **한 줄**로 작성합니다.
- 결함 목록이 10건 초과 시 `ac:name="expand"` 매크로로 나머지를 접어 표시합니다.
- QA 상태 배지는 `ac:name="status"` 매크로 사용 (테스트 계획: Blue/진행예정, 종료보고: Yellow/진행중 + Green/종료).
