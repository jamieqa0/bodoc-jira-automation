# atlas-qa-reporter Web UI — 디자인 문서

> Show Me The PRD로 생성됨 (2026-05-08)

## 문서 구성

| 문서 | 내용 | 언제 읽나 |
|------|------|----------|
| [01_PRD.md](./01_PRD.md) | 뭘 만드는지, 누가 쓰는지, 성공 기준 | 프로젝트 시작 전 |
| [02_DATA_MODEL.md](./02_DATA_MODEL.md) | 데이터 구조 (Settings, ReportJob) | 구조 설계할 때 |
| [03_PHASES.md](./03_PHASES.md) | 단계별 계획 + Phase 1 시작 프롬프트 | 개발 순서 정할 때 |
| [04_PROJECT_SPEC.md](./04_PROJECT_SPEC.md) | 기술 스택, 구조, AI 행동 규칙 | AI에게 코드 시킬 때마다 |

## 다음 단계

Phase 1을 시작하려면 [03_PHASES.md](./03_PHASES.md)의 **"Phase 1 시작 프롬프트"** 를 복사해서 사용하세요.

## 미결 사항 ([NEEDS CLARIFICATION])

- [ ] 앱 첫 실행 시 ui_settings.json 없으면 설정 페이지로 자동 리디렉션 여부
- [ ] 동시 실행 시 SSE 스트림 격리 방법 (threading.Thread per request vs generator per request)
- [ ] ui_settings.json을 .gitignore에 추가할지 여부 (API 토큰 노출 위험)
