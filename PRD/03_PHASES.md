# atlas-qa-reporter Web UI — Phase 분리 계획

---

## Phase 1: MVP (약 3일)

### 목표
`python app.py` 실행 후 브라우저에서 4개 리포트를 모두 실행하고,
실시간 로그를 보며 완료 시 Confluence 링크를 클릭할 수 있다.

### 기능
- [ ] Flask 앱 기본 구조 (app.py + blueprints/)
- [ ] 설정 페이지 (ui_settings.json R/W, .env fallback)
- [ ] 4개 리포트 폼 UI (탭 네비게이션)
  - 테스트 플랜: 태스크 키 + 이메일
  - QA 보고서: 태스크 키 + 이메일
  - MOR: 월(YYYY-MM) + 이메일 + Confluence 게시 토글
  - 연간: 연도(YYYY) + 이메일 + quiet 모드 토글
- [ ] SSE 로그 스트리밍 (Vanilla JS EventSource)
- [ ] 실행 결과 표시 + Confluence 링크 바로 열기

### 데이터
- Settings (config/ui_settings.json)
- ReportJob (in-memory, 저장 없음)

### 인증
- 없음 (로컬 전용, 이메일은 폼에서 직접 입력)

### "진짜 제품" 체크리스트
- [ ] 실제 Jira/Confluence API 연결 (목업 데이터 X)
- [ ] 기존 CLI와 동일한 결과물 생성 확인
- [ ] `python app.py`로 로컬 실행 가능

### Phase 1 시작 프롬프트
```
이 PRD를 읽고 Phase 1을 구현해주세요.
@PRD/01_PRD.md
@PRD/02_DATA_MODEL.md
@PRD/04_PROJECT_SPEC.md

Phase 1 범위:
- Flask 앱 기본 구조 (app.py + blueprints/)
- 설정 페이지 (config/ui_settings.json R/W)
- 4개 리포트 폼 (테스트 플랜 / QA 보고서 / MOR / 연간)
- SSE 로그 스트리밍 (Vanilla JS EventSource)
- 실행 결과 표시 + Confluence 링크 열기

반드시 지켜야 할 것:
- 04_PROJECT_SPEC.md의 "절대 하지 마" 목록 준수
- core/generators/ 로직 그대로 재사용 (수정 금지)
- DB 없이 인메모리 + JSON 파일만 사용
- Vanilla JS만 사용 (외부 JS 라이브러리 X)
```

---

## Phase 2: 확장 (약 2일)

### 전제 조건
Phase 1이 안정적으로 동작하는 상태.

### 목표
API 토큰 보안 강화, 기존 .env 자동 마이그레이션, 다크모드 지원.

### 기능
- [ ] API 토큰 Fernet 암호화 저장
- [ ] 첫 실행 시 .env 자동 읽어 ui_settings.json에 마이그레이션
- [ ] 다크모드 CSS 토글
- [ ] LAN 접근 가이드 (0.0.0.0 바인딩, README에 추가)

### 추가 데이터
- Settings에 `encrypted: bool` 필드 추가

### 통합 테스트
- Phase 1 기능 (4개 리포트 실행) 이상 없음 확인

---

## Phase 3: 고도화 (침선 개시 시)

### 전제 조건
Phase 1 + 2 안정 운영 중.

### 목표
실행 이력 조회, 외부 배포, 스케줄링.

### 기능
- [ ] 실행 이력 저장/조회 (SQLite)
- [ ] 무료 호스팅 배포 (Render 또는 Railway)
- [ ] 스케줄링 자동 실행 (APScheduler)

### 주의사항
- Render/Railway 무료 티어는 슬립 모드 있음 → 로컬 배포가 더 안정적일 수 있음
- 외부 배포는 반드시 Phase 2 토큰 암호화 완료 후 진행

---

## Phase 로드맵 요약

| Phase | 핵심 기능 | 상태 |
|-------|----------|------|
| Phase 1 (MVP) | 4개 리포트 폼 + SSE 로그 + 설정 페이지 | 시작 전 |
| Phase 2 | 토큰 암호화 + .env 마이그레이션 + 다크모드 | Phase 1 완료 후 |
| Phase 3 | 실행 이력 + 외부 배포 + 스케줄링 | Phase 2 완료 후 |
