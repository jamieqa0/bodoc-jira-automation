# Jira QA Automation

이 프로젝트는 Jira의 QA Task 및 관련 Defect 데이터를 기반으로 테스트 플랜 및 QA 결과 보고서를 자동으로 생성하여 Confluence에 게시하는 도구입니다.

## 📂 파일 구조

```text
.
├── bin/                        # 실행 진입점 스크립트
│   ├── run_test_plan.py        # 테스트 플랜 생성 및 게시
│   ├── run_qa_report.py        # QA 결과 보고서 생성 (차트 포함)
│   ├── run_mor_report.py       # MOR 리포트 초안 생성 및 게시
│   ├── run_annual_report.py    # 연간 업무 성과 보고서 생성
│   └── debug_jira.py           # 연결 디버깅 도구
├── core/                       # 핵심 라이브러리
│   ├── clients/                # API 클라이언트 (Jira, Confluence)
│   ├── generators/             # 리포트 생성 엔진 (Annual, MOR, QA, Test Plan)
│   ├── templates/              # Jinja2 HTML 템플릿
│   └── utils.py                # 공통 유틸리티
├── config/                     # 설정 관리 (.env 연동)
├── data/                       # 로컬 데이터 저장소
├── requirements.txt            # 의존성 패키지
└── README.md
```

## 🛠️ 설치 방법

1. 필요한 라이브러리를 설치합니다.

   ```bash
   pip install -r requirements.txt
   ```

2. `.env` 파일을 프로젝트 루트에 생성하고 필수 값을 입력합니다. (Jira/Confluence 도메인 및 API 토큰 등)

## 🚀 사용 방법

프로젝트 루트 디렉토리에서 실행해 주세요.

### 1. 테스트 플랜 생성

```bash
python bin/run_test_plan.py SQA-122
```

### 2. QA 결과 보고서 생성

```bash
python bin/run_qa_report.py SQA-119
```

### 3. MOR 리포트 초안 생성 및 게시

```bash
# 초안 생성 및 Confluence 게시
python bin/run_mor_report.py --month 2026-04 --publish

# 특정 사용자 리포트 생성 시
python bin/run_mor_report.py --month 2026-04 --user user@example.com --publish
```

### 4. 연간 업무 성과 보고서 생성

```bash
# 특정 연도의 보고서 생성 및 게시
python bin/run_annual_report.py --year 2025

# 특정 사용자 리포트 생성 시
python bin/run_annual_report.py --year 2025 --user user@example.com
```

## 💡 주요 특징 (QA Report)

- **Amplitude 이슈 분리**: 요약에 `[Amplitude]`가 포함된 이슈를 감지하여 별도 통계 및 섹션으로 관리합니다.
- **시각적 현황 제공**: 상태별/우선순위별 결함 분포를 파이 차트 및 바 차트로 생성하여 자동 첨부합니다.
- **목록형 Jira 매크로**: 결함 상세 내역에 지라 리스트(JQL Query) 매크로를 적용하여 실시간 상태를 확인할 수 있습니다.
- **프로젝트 명/버전 자동 추출**: 티켓 제목에서 `[보닥앱]`, `4.9.0` 등 정보를 파싱하여 요약 정보에 자동 반영합니다.
- **해결률 자동 계산**: 완료 상태 이슈 비중을 계산하여 보고서에 포함합니다.

## 💡 아틀라시안 토큰 발급 주소

- [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
