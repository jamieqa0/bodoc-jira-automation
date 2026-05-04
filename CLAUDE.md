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

# Jira 연결 디버깅
python bin/debug_jira.py
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

API 토큰 발급: https://id.atlassian.com/manage-profile/security/api-tokens

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

### 핵심 모듈

- `config/settings.py` — `.env` 로드 및 필수값 검증. 모듈 임포트 시점에 `settings.validate()` 자동 실행
- `core/clients/jira.py` — `jira` 패키지 사용. `fetch_defects()`는 50개씩 페이지네이션
- `core/clients/confluence.py` — `atlassian` 패키지 사용. 페이지 존재 시 업데이트, 없으면 생성
- `core/utils.py` — 버전/프로젝트명 추출 (`[보닥앱] MAINTENANCE_4.9.1` 형식 파싱)
- `core/templates/` — Jinja2 HTML 템플릿. Confluence 스토리지 형식(`<ac:structured-macro>`) 사용

## 주요 동작 특성

**Amplitude 이슈 분리**: Summary에 `[Amplitude]`가 포함된 Defect는 전체 통계와 별도 섹션 및 차트로 분리됩니다.

**해결률 계산**: `['Resolved', 'Closed', 'Done', 'Verified', '해결됨', '완료', '종료']` 상태를 해결된 것으로 집계합니다.

**PRD 링크 자동 탐색**: Jira 이슈의 linked issues 중 Summary에 "PRD"가 포함된 항목을 자동으로 연결합니다.

**한국어 폰트**: matplotlib 차트가 한국어를 표시할 수 있도록 플랫폼별 폰트를 자동 선택합니다 (Windows: Malgun Gothic).

**SSL 검증 비활성화**: Jira/Confluence 연결 시 `verify=False`. 프로덕션 환경 전환 시 수정 필요합니다.
