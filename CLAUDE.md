# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 실행 명령어 (Quick Start)

모든 명령어는 프로젝트 루트에서 실행해야 합니다.

```bash
# 1. 의존성 설치 및 연결 확인
pip install -r requirements.txt
python bin/debug_jira.py

# 2. 테스트 플랜 / QA 보고서 생성
python bin/run_test_plan.py SQA-122           # 테스트 플랜
python bin/run_qa_report.py SQA-119           # QA 결과 보고서 (차트 포함)

# 3. MOR 리포트 생성
python bin/run_mor_report.py --month 2026-04            # 로컬 초안 생성 (.md)
python bin/run_mor_report.py --month 2026-04 --publish  # Confluence 직접 게시
python bin/run_mor_report.py --month 2026-04 --user user@example.com --publish # 특정 사용자 지정

# 4. 연간 업무 성과 보고서
python bin/run_annual_report.py --year 2025             # 2025년 전체
python bin/run_annual_report.py --year 2026 --quiet     # 진행 중인 2026년 요약
python bin/run_annual_report.py --year 2025 --user user@example.com # 특정 사용자 지정
```

---

## ⚙️ 환경 설정 (Configuration)

프로젝트 루트의 `.env` 파일이 필수입니다. (`.env.sample` 참고)

| 변수                             | 필수 | 설명                                                                         |
| :------------------------------- | :--: | :--------------------------------------------------------------------------- |
| `ATLASSIAN_URL`                  |  O   | Jira/Confluence 도메인 (`https://xxxx.atlassian.net`)                        |
| `ATLASSIAN_USER`                 |  O   | Atlassian 계정 이메일                                                        |
| `ATLASSIAN_API_TOKEN`            |  O   | [API 토큰 발급](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `CONFLUENCE_SPACE_KEY`           |  O   | Confluence 공간 키                                                           |
| `CONFLUENCE_QA_REPORT_PARENT_ID` |  -   | QA Report 부모 페이지 ID                                                     |
| `CONFLUENCE_MOR_PARENT_ID`       |  -   | MOR/연간 보고서 부모 페이지 ID                                               |

---

## 📂 프로젝트 구조 (Project Structure)

```text
.
├── bin/                # 실행 진입점 스크립트 (CLI)
├── config/             # 설정 로드 및 유효성 검증 (settings.py)
├── core/               # 핵심 비즈니스 로직
│   ├── clients/        # Jira/Confluence API 클라이언트
│   ├── generators/     # 보고서 생성 엔진 (리팩토링 완료)
│   ├── templates/      # Jinja2 HTML 템플릿 (.html)
│   └── utils.py        # 유틸리티 (데이터 파싱, 날짜 등)
├── data/               # 로컬 수집 데이터 (collected_raw.json 등)
└── docs/               # 기술 및 기획 문서
```

---

## 🏗️ 아키텍처 및 모듈 (Architecture)

### 🔄 보고서 생성 흐름

1. **Entry**: `bin/run_*.py` 실행
2. **Logic**: `core/generators/*_generator.py`에서 데이터 수집 및 분석
3. **View**: `core/templates/*.html`을 통한 리포트 렌더링
4. **Output**: `ConfluenceClient`를 통해 페이지 게시 및 이미지 첨부

### 🛠️ 핵심 모듈 역할

- **`JiraClient`**: JQL 기반 이슈 수집 (Pagination 대응), 결함 데이터 분석용 DataFrame 생성
- **`ConfluenceClient`**: CQL 기반 페이지 검색, 페이지 생성/업데이트, 파일 첨부
- **`Generators`**: 비즈니스 로직 분리 (Annual, MOR, QA, Test Plan 전용 엔진)
- **`Templates`**: Confluence Storage Format(`<ac:macro>`) 및 HTML5 대응

---

## 💡 주요 동작 및 비즈니스 규칙

> [!IMPORTANT]
> **해결률(Resolution Rate) 계산 방식**
> `resolutiondate`가 있거나 상태가 `Prod 배포완료`, `종료`, `Resolved`, `Done`, `Verified` 중 하나인 경우 해결된 것으로 간주합니다.

- **SQA vs 결함 분류**: 연간 보고서에서 `SQA` 프로젝트 이슈는 '작업관리', 타 프로젝트 이슈는 '결함'으로 자동 분류됩니다.
- **Amplitude 대응**: 요약에 `[Amplitude]`가 포함된 이슈는 별도의 통계 세션과 전용 차트로 분리 관리됩니다.
- **폰트 설정**: `matplotlib` 차트 렌더링 시 OS별 한글 폰트를 자동 선택합니다 (Windows: `Malgun Gothic`, Mac: `AppleGothic`).
- **보안**: 개발 편의를 위해 `verify=False`(SSL 무시) 설정이 되어 있습니다. 사내 보안 정책에 따라 수정이 필요할 수 있습니다.
- **자동 링크**: Jira 이슈의 linked issues 중 `PRD` 단어가 포함된 항목을 찾아 자동으로 PRD 링크를 연결합니다.
- **보안**: `verify=False`(SSL 무시) 설정이 되어 있습니다.

---

## ⚠️ 사용 시 참고사항

> - **산출물 생성 지원 (Process Support)**: 본 도구는 Jira/Confluence 데이터를 기반으로 테스트 계획서(Test Plan), QA 종료보고서(QA Report) 등 각 단계별 산출물 작성을 지원하는 보조 도구입니다. 자동화를 통해 업무 효율을 높일 수 있으나, 최종 산출물의 품질과 제품의 신뢰성은 사용자의 검토와 전문적인 판단을 통해 완성됩니다.
> - **성과 측정의 정성적 보완 (Qualitative Achievements)**: 기획 결함 예방(Shift-left), 리스크 기반 테스트 전략 수립, 피그마(Figma) 리뷰, 구두 협의 및 커뮤니케이션 등 플랫폼 외부에서 수행된 정성적 품질 활동은 자동 반영되지 않습니다. 실제 성과를 균형 있게 전달하기 위해서는 이러한 활동들을 사용자가 직접 보완하여 작성해야 합니다.
