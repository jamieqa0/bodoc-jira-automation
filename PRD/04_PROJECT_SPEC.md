# atlas-qa-reporter Web UI — 프로젝트 스펙

> AI가 코드를 짤 때 지켜야 할 규칙.
> 이 문서를 항상 함께 공유하세요.

---

## 기술 스택

| 영역 | 선택 | 이유 |
|------|------|------|
| 백엔드 | Flask | 기존 프로젝트 Python 환경, 최소 의존성 |
| 템플릿 엔진 | Jinja2 | Flask 기본 내장, core/templates에서 이미 사용 중 |
| 프론트엔드 | Vanilla JS | 빌드 툴 없음, 외부 라이브러리 없음, 가장 단순 |
| 스타일링 | 인라인 CSS + 단일 stylesheet | npm/빌드 불필요 |
| SSE | Flask stream_with_context | 추가 의존성 없음 |
| 설정 저장 | JSON 파일 (config/ui_settings.json) | DB 불필요, 읽기/쓰기 단순 |
| 로컬 서버 | Flask 개발 서버 | 로컬 Phase 1은 단순하게 |

---

## 프로젝트 구조

```
atlas-qa-reporter/
├── app.py                    # Flask 진입점
├── blueprints/
│   ├── reports.py            # 리포트 실행 라우트 + SSE 엔드포인트
│   └── settings.py           # 설정 페이지 라우트
├── templates/
│   ├── base.html             # 공통 레이아웃 (탭 네비게이션 + 헤더)
│   ├── index.html            # 메인 (4개 리포트 폼 탭)
│   └── settings.html         # 설정 페이지
├── static/
│   ├── app.js                # SSE 연결, 폼 제출, 결과 표시 (Vanilla JS)
│   └── style.css             # 공통 스타일
├── config/
│   ├── settings.py           # 기존 .env 설정 로더 (수정 금지)
│   └── ui_settings.json      # 웹 UI 설정 파일 (브라우저에서 편집)
├── core/                     # 기존 로직 — 수정 금지
│   ├── clients/
│   ├── generators/
│   ├── templates/
│   └── utils.py
└── bin/                      # 기존 CLI — 수정 금지
```

---

## 절대 하지 마 (DO NOT)

- `core/` 폴더 안의 파일을 수정하지 마 (CLI와 공유하는 로직)
- `bin/` 폴더 안의 파일을 수정하지 마
- API 토큰이나 비밀번호를 코드에 직접 쓰지 마 (ui_settings.json 또는 .env 사용)
- React, Vue, HTMX, Alpine.js 등 외부 JS 프레임워크/라이브러리 추가하지 마 (Vanilla JS만)
- npm, node_modules, package.json 추가하지 마 (Python/pip 환경만)
- SQLite 또는 다른 DB 추가하지 마 (Phase 3 전까지)
- 기존 `.env` 파일을 삭제하거나 덮어쓰지 마 (UI 설정과 병존)
- SSE 엔드포인트에서 blocking I/O를 메인 스레드에서 직접 실행하지 마 (threading 사용)

---

## 항상 해 (ALWAYS DO)

- 변경 전에 무엇을 할지 먼저 설명
- 새 라우트 추가 시 blueprints/ 아래에 배치
- ui_settings.json 없으면 빈 딕셔너리로 초기화 후 설정 페이지로 리디렉션
- SSE 스트림 종료 시 `data: [DONE]\n\n` 이벤트 전송
- 리포트 실행 오류 발생 시 로그 스트림에 에러 메시지 포함 후 status=failed 반환

---

## 테스트 방법

```bash
# 로컬 실행
python app.py
# 브라우저: http://localhost:5000

# 기존 CLI 회귀 테스트 (웹 UI 작업 후 동작 확인)
python bin/run_test_plan.py SQA-122
python bin/run_qa_report.py SQA-119
python bin/run_mor_report.py --month 2026-04
```

---

## 배포 방법

### 로컬 (Phase 1)
```bash
python app.py
# 기본: http://localhost:5000
```

### LAN 접근 (Phase 2)
```bash
python app.py --host 0.0.0.0
# 같은 네트워크: http://{내 IP}:5000
```

---

## 설정 우선순위

| 설정 파일 | 설명 | 우선순위 |
|-----------|------|----------|
| `config/ui_settings.json` | 웹 UI에서 편집한 설정 | 높음 (우선 적용) |
| `.env` | 기존 CLI 설정 (fallback) | 낮음 |

> ui_settings.json은 .gitignore에 추가 권장 (API 토큰 포함).

---

## [NEEDS CLARIFICATION]

- [ ] 동시 실행 요청 처리: 두 사람이 동시에 실행할 때 SSE 스트림 격리 방법 확정 필요
- [ ] ui_settings.json .gitignore 포함 여부 결정
