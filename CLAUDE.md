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
python bin/run_mor_report.py --month 2026-04                                    # 로컬 .md 초안 생성
python bin/run_mor_report.py --month 2026-04 --publish                          # Confluence 직접 게시
python bin/run_mor_report.py --month 2026-04 --user user@example.com --publish  # 특정 사용자

# CLI — 연간 업무 보고서
python bin/run_annual_report.py --year 2025
python bin/run_annual_report.py --year 2025 --user user@example.com             # 특정 사용자
python bin/run_annual_report.py --year 2026 --user user@example.com --quiet

# 연결 디버깅
python bin/debug_jira.py
```

---

## 환경 설정

설정 경로가 두 가지 병존합니다.

| 경로 | 용도 |
|---|---|
| `.env` | CLI 실행 시 |
| `config/ui_settings.json` | Web UI 저장값 (gitignore됨) |

`config/ui_settings_loader.py`의 `load_ui_settings()`는 JSON 파일이 없으면 아래 환경변수로 fallback합니다. Render 배포 시에는 환경변수만 설정하면 됩니다.

| 환경변수 | 설명 |
|---|---|
| `ATLASSIAN_URL` | `https://xxxx.atlassian.net` |
| `ATLASSIAN_USER` | Atlassian 계정 이메일 |
| `ATLASSIAN_API_TOKEN` | API 토큰 |
| `CONFLUENCE_SPACE_KEY` | Confluence 공간 키 |
| `TEST_PLAN_PARENT_ID` | 테스트 플랜 부모 페이지 ID (선택) |
| `QA_REPORT_PARENT_ID` | QA 보고서 부모 페이지 ID (선택) |
| `MOR_PARENT_ID` | MOR/연간 보고서 부모 페이지 ID (선택) |

`config/Settings` 클래스는 **import 시점**에 `validate()`를 실행합니다. Web UI에서는 `blueprints/reports.py`의 `_patch_settings()`로 런타임에 monkey-patch하므로, `.env` 없이도 Web UI가 동작합니다.

---

## 배포

`render.yaml`에 Render 배포 설정이 있습니다. 빌드 시 `core/fonts/NanumGothic.ttf`를 curl로 다운로드해 matplotlib 한글 폰트를 설정합니다. `FLASK_SECRET_KEY`는 Render가 자동 생성합니다.

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

- **`JiraClient`** (`core/clients/jira.py`): JQL 기반 이슈 수집, `remote_links()`로 Figma/Confluence URL 추출, `fetch_defects()`는 pandas DataFrame 반환
- **`ConfluenceClient`** (`core/clients/confluence.py`): 페이지 생성/업데이트 시 `get_page_id` → CQL → 휴지통 순으로 fallback. `publish_page()`가 실패하면 traceback을 ERROR 레벨로 기록
- **`QAReportGenerator`** (`core/generators/qa_report_generator.py`): matplotlib 차트 생성 포함. 스레드 안전성을 위해 `Agg` 백엔드와 `_chart_lock` 사용. 한글 폰트는 `core/fonts/NanumGothic.ttf` 파일 경로로 직접 로드
- **`AnnualGenerator`** (`core/generators/annual_report_generator.py`): Confluence `ac:layout` 3열 레이아웃으로 연간 보고서 렌더링

### Web UI 설정 흐름

1. `/settings` — `config/ui_settings.json`에 저장
2. `/run` POST — `load_ui_settings()`로 읽어 `_patch_settings()` 호출
3. 작업 완료 후 `_restore_settings()`로 원복

> **주의**: `_patch_settings()`는 module-level 전역 singleton을 수정합니다. `_settings_lock`이 동시 실행을 직렬화하므로 두 번째 `/run` 요청은 첫 번째가 완료될 때까지 블로킹됩니다. 멀티 유저 또는 탭 동시 사용 시 이 제약을 고려해야 합니다.

### 프론트엔드 레이어

`static/app.js` 단일 파일, `static/style.css` 단일 파일. 프레임워크 없음.

- **섹션 전환**: 홈(`/`)은 4개 리포트 섹션이 한 페이지에 있고 `.is-active` 클래스로 단 하나만 표시. `sidebar__nav-item[data-section]` → `activateSection()`.
- **DOM ID 명명 규칙**: `report_type`의 `_`를 `-`로 치환. 예) `test_plan` → `form-test-plan`, `log-test-plan`, `result-test-plan`.
- **SSE 흐름**: `handleSubmit` → `startReport` (POST `/run`, job_id 수신) → `streamLogs` (EventSource `/stream/<job_id>`) → `done` 이벤트에서 `showResult`. 에러 시 `showResult`가 `formData`를 클로저로 보관해 "재시도" 버튼 생성.
- **CSS 가시성**: `.result-area`와 `.log-area`는 기본 `display: none`. `:not(:empty)` 셀렉터로 내용이 생기면 자동 표시.
- **유효성 검사 패턴**: 차단 오류는 `.input-invalid` + `.field-error`(빨간색), 비차단 경고는 `.input-warning` + `.field-warning`(주황색). 미래 날짜(`month`, `year` 필드)는 제출을 막지 않는 경고로 처리.
- **푸터 버전**: `app.py`의 `_last_commit_date()`가 앱 시작 시 `git log -1` 으로 최신 커밋 날짜를 읽어 `app_updated` context 변수에 주입. git 실패 시 현재 날짜로 fallback.

### 기타 디렉터리

- **`scratch/`**: 프로덕션 코드가 아닌 일회성 디버그/분석 스크립트. Jira/Confluence 응답 구조 확인용.
- **`skills/qa-session-kpi/`**: QA 세션 KPI 수집·집계 스크립트 (별도 독립 실행). 메인 보고서 파이프라인과 무관.

### 테스트

자동화 테스트 없음. 검증은 실제 Atlassian 연결로만 가능하며, `bin/debug_jira.py`로 연결과 데이터 구조를 확인합니다.

---

## 비즈니스 규칙

### 이슈 분류 (연간 보고서 / MOR)

- `project = SQA` → QA 작업관리
- 그 외 `issuetype = Defect` → 결함 (반드시 Defect 타입만 집계)
- **APTS 프로젝트 세분화**: fixVersions 또는 summary에 `플래너/planner` → `Planner & B2B`, `보닥/bodoc/android/ios/ai 상담사` → `Bodoc 4.0`, 해당 없으면 `Planner & B2B` 기본

### 해결률 계산

`resolutiondate`가 있거나 status가 `RESOLVED_STATUSES`(`core/utils.py`) 중 하나이면 해결 완료로 집계합니다.

### 버전/빌드번호 표시 조건

테스트 계획·QA 종료보고서 Summary 테이블에서 `버전/빌드번호` 행은 **SQA Task summary에 `보닥앱`이 포함된 경우에만** 표시합니다 (`show_version` 플래그).

### Figma / Confluence 링크 자동 추출

`JiraClient.get_issue_info()`에서 `jira.remote_links()`로 외부 링크를 조회해 URL 패턴(`figma.com`, `atlassian.net/wiki` 또는 `/wiki/`)으로 분류합니다.

### Amplitude 이슈

summary에 `Amplitude`(대소문자 무관) 포함 시 별도 섹션으로 분리합니다. QA 보고서에서는 차트도 별도 생성합니다.

### QA 보고서 자동화 항목

- **차트 자동 첨부**: 상태별(파이 차트) + 우선순위별(바 차트) 결함 분포를 PNG로 생성해 Confluence 페이지에 첨부
- **Jira 매크로**: 결함 상세 내역에 JQL Query 매크로(`ac:name="jira"`)를 삽입해 Confluence에서 실시간 이슈 상태 확인 가능
- **버전 자동 추출**: 티켓 제목에서 `[보닥앱]`, `4.9.0` 등 정보를 파싱해 요약 테이블에 반영
- **해결률 자동 계산**: 완료 상태 이슈 비중을 계산해 보고서에 포함

---

## 템플릿 작성 규칙

- 템플릿은 **Confluence Storage Format** 기준입니다 (`<ac:structured-macro>`, `<ac:layout>` 등 사용).
- `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` 태그를 **절대 사용하지 않습니다** — Confluence API가 거부합니다.
- 줄바꿈이 그대로 렌더링되므로, `td` 안의 Jinja2 조건문은 반드시 **한 줄**로 작성합니다.
- 결함 목록이 10건 초과 시 `ac:name="expand"` 매크로로 나머지를 접어 표시합니다.
- QA 상태 배지는 `ac:name="status"` 매크로 사용 (테스트 계획: Blue/진행예정, 종료보고: Yellow/진행중 + Green/종료).
