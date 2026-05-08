# atlas-qa-reporter Web UI — 데이터 모델

> DB 없이 설정 JSON 파일 + 인메모리 작업 객체만 사용합니다.

---

## 전체 구조

```
[Settings]  ──읽기/쓰기──▶  [ReportJob]  ──SSE 스트림──▶  [브라우저 클라이언트]
(ui_settings.json)          (in-memory, per request)
```

---

## 엔티티 상세

### Settings
Atlassian 연결 정보와 Confluence 게시 경로를 저장하는 설정 파일.
`config/ui_settings.json`에 JSON으로 저장. Phase 2에서 API 토큰 암호화 예정.

| 필드 | 설명 | 예시 | 필수 |
|------|------|------|------|
| atlassian_url | Atlassian 도메인 | https://company.atlassian.net | O |
| atlassian_api_token | API 토큰 (현재 평문, Phase 2에서 암호화) | ATA... | O |
| confluence_space_key | Confluence 공간 키 | QA | O |
| qa_report_parent_id | QA 리포트 부모 페이지 ID | 123456 | X |
| mor_parent_id | MOR/연간 보고서 부모 페이지 ID | 789012 | X |

### ReportJob
리포트 실행 요청 1건을 나타내는 인메모리 객체. HTTP 요청 처리 중에만 존재하며 저장되지 않음.

| 필드 | 설명 | 예시 | 필수 |
|------|------|------|------|
| job_id | 요청별 고유 ID (UUID) | a1b2-c3d4 | O |
| report_type | 리포트 종류 | test_plan / qa / mor / annual | O |
| user_email | 실행자 이메일 | jamieqa0@gmail.com | O |
| task_key | Jira 태스크 키 (test_plan/qa 전용) | SQA-122 | X |
| month | 대상 월 (mor 전용) | 2026-04 | X |
| year | 대상 연도 (annual 전용) | 2025 | X |
| publish | Confluence 게시 여부 | true | O |
| quiet | 요약 모드 (annual 전용) | false | X |
| status | 현재 상태 | running / success / failed | O |
| log_lines | SSE로 스트리밍할 로그 줄 목록 | ["수집 시작...", "완료"] | O |
| confluence_url | 완료 시 생성된 페이지 URL | https://... | X |

---

## 왜 이 구조인가

**DB를 쓰지 않는 이유**
- 이력 조회가 Phase 3 요구사항이라 지금은 불필요
- 나중에 SQLite 추가 시 스키마 마이그레이션 없이 append만 하면 되므로 확장 용이

**Settings를 .env 대신 JSON으로 관리하는 이유**
- UI에서 필드 단위로 읽고 쓰기 위해 구조화된 형식 필요
- Phase 2에서 필드별 Fernet 암호화 적용이 쉬움

**우선순위**: ui_settings.json이 있으면 .env보다 우선 적용.

---

## [NEEDS CLARIFICATION]

- [ ] 동시 실행 시 job_id별 SSE 스트림 격리 방법 (threading.Thread per request vs generator per request)
- [ ] ui_settings.json을 .gitignore에 추가할지 여부 (API 토큰 노출 위험)
