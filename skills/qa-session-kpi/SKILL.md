---
name: qa-session-kpi
description: This skill MUST be used whenever the user asks about their own QA work, contributions, or performance in Claude Code sessions. Trigger phrases include: "QA 활동 요약", "내 KPI", "QA 성과 측정", "내 기여", "session 기반", "qa kpi", "이번 주 뭐 했어", "활동량 분석", "발견한 버그 몇 개", "검증 완료율", "QA report", "session qa". This skill collects Claude Code session logs and classifies user messages (issue_found, fix_instruction, verification, test_case, analysis) to compute KPI metrics that prove a QA engineer's contribution in AI-assisted development - where traditional metrics (bug count, fix time) fail to capture the real value. IMPORTANT: Use this skill any time the user asks what they did, how much they contributed, or wants a performance report from their Claude Code work sessions.
---

# QA Session KPI

> Claude Code 세션 로그를 분석하여 바이브코딩 환경에서 QA 엔지니어의 실제 기여도를 KPI로 측정합니다.

## 배경

전통적인 QA KPI(결함 수, 해결 시간)는 AI가 개발 속도를 높이면서 QA의 가치를 오히려 숨깁니다. 버그를 발견해도 AI가 10초 만에 고치면 "수정 소요 시간"은 QA의 기여가 아니라 AI 속도를 측정하게 됩니다.

이 스킬은 다른 질문을 합니다: **QA 엔지니어가 Claude와 함께 실제로 무엇을 했는가?** Claude Code 세션 로그에서 직접 추출하여 측정합니다.

---

## 워크플로우

### Step 1: 세션 로그 수집 (script)

`scripts/collect_sessions.py`를 실행하여 Claude Code 세션 파일에서 사용자 메시지를 추출한다.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/qa-session-kpi/scripts/collect_sessions.py" \
  --days 7
```

수집 대상:
- 경로: `~/.claude/projects/` 하위의 모든 `.jsonl` 파일
- 기간: 기본 최근 7일 (Settings에서 조정 가능)
- 대상: `role=user` 메시지만 추출 (AI 응답 제외)
- 프로젝트 필터: `--project` 인수로 특정 프로젝트만 선택 가능

출력은 JSON 형식으로 stdout에 출력된다:
```json
{
  "messages": [
    {"timestamp": "2026-05-01T10:30:00", "content": "...", "session": "abc123", "project": "bodoc-jira-automation"}
  ],
  "count": 42
}
```

수집 실패 시 처리:
- `~/.claude/projects/` 디렉토리가 없으면 오류 메시지를 출력하고 종료한다
- 개별 파일 파싱 오류는 경고(WARN)만 출력하고 계속 진행한다
- 빈 결과(0건)이면 "해당 기간 내 메시지 없음" 메시지를 출력한다

### Step 2: QA 활동 분류 (prompt)

수집된 메시지를 읽고 `references/activity-categories.md`의 기준에 따라 각 메시지를 5개 유형으로 분류한다.

분류 유형:

| 유형 | 의미 | 예시 패턴 |
|------|------|-----------|
| `issue_found` | 이슈·버그·이상 동작 발견 및 보고 | "이거 안 돼", "에러 나", "여기 누락됨" |
| `fix_instruction` | AI에게 수정·변경·구현 지시 | "고쳐줘", "수정해줘", "이렇게 바꿔줘" |
| `verification` | 수정 결과 확인, 재테스트, 승인 | "됐어", "확인했어", "통과" |
| `test_case` | 테스트 케이스·시나리오·체크리스트 작성 | "테케 만들어줘", "어떤 경우 테스트해야 해?" |
| `analysis` | 원인 분석, 로그 조사, 재현 조건 파악 | "왜 이래?", "원인이 뭐야?", "로그 분석해줘" |

분류 프롬프트 (Step 1 결과물을 받아 실행):

```
아래는 QA 엔지니어가 Claude Code 세션에서 작성한 메시지 목록입니다.
각 메시지를 다음 5개 유형 중 하나로 분류해주세요:

- issue_found: 이슈·버그·이상 동작을 처음 발견하거나 보고하는 메시지
- fix_instruction: AI에게 코드·동작·설정 수정을 지시하는 메시지
- verification: 수정 결과를 직접 확인하거나 승인하는 메시지
- test_case: 테스트 케이스·시나리오·체크리스트를 작성하거나 요청하는 메시지
- analysis: 문제 원인을 분석하거나 동작 이해를 위한 조사 메시지

QA와 무관한 메시지(잡담, 환경설정 질문, 비관련 요청)는 "other"로 분류하세요.
하나의 메시지에 복수 의도가 있으면 가장 주요한 QA 의도를 선택하세요.

입력 형식: [{"session": "...", "timestamp": "...", "content": "..."}]
출력 형식: 입력 배열에 "activity" 필드를 추가한 JSON 배열만 출력하세요.
```

분류 시 주의사항:
- 하나의 메시지에 복수 의도가 있으면 가장 주요한 QA 의도를 선택한다
- 판단 기준이 애매한 케이스는 `references/activity-categories.md`를 참조한다
- QA와 무관한 메시지(잡담, 비관련 질문)는 `other`로 분류하며 KPI 집계에서 제외한다
- 분류 결과를 메시지마다 `activity` 필드로 추가하여 JSON 배열로 반환한다
- 메시지 수가 많으면 50개씩 나눠서 분류하고 결과를 합친다

### Step 3: KPI 집계 (script)

분류 결과 JSON을 `scripts/aggregate_kpi.py`에 파이프하여 KPI를 계산한다.

```bash
# 수집 → 분류 → 집계 파이프라인 예시
python collect_sessions.py --days 7 | \
  (classify with Claude) | \
  python aggregate_kpi.py --days 7
```

계산되는 KPI 항목:

**활동량 지표:**
- **발견 활동량**: 기간 내 `issue_found` 메시지 총 수 (일별 추세 포함)
- **수정 지시 수**: `fix_instruction` 총 수
- **테스트 케이스 수**: `test_case` 총 수
- **분석 깊이**: `analysis` 총 수

**품질 지표:**
- **검증 완료율 (%)**: `verification` 수 ÷ `issue_found` 수 × 100
  - 100% 이상이면 발견한 이슈보다 더 많이 검증 (회귀 검증 포함)
  - 50% 미만이면 발견했지만 검증하지 않은 이슈가 많음을 의미

**생산성 지표:**
- **세션 생산성**: 총 QA 활동 수 ÷ 세션 수
- **활동 분포**: 유형별 비율 (발견:수정:검증:테케:분석)

### Step 4: 시각화 + 보고서 생성 (generate)

집계 결과를 Markdown 보고서로 생성하여 프로젝트 루트에 저장한다.

기본 출력: `qa_kpi_{날짜}.md`

보고서 구성:
1. **요약 테이블**: KPI 핵심 지표 한눈에 보기
2. **활동 유형별 분포**: 5개 유형별 건수와 비율
3. **일별 활동량 추세**: 날짜별 활동 내역
4. **하이라이트**: 가장 활발했던 날, 가장 활발했던 세션 TOP 5
5. **인사이트**: 검증 완료율이 낮으면 자동으로 "미검증 이슈 있음" 경고 표시

**Confluence 게시 옵션:**
사용자가 "Confluence에 올려줘"라고 요청하면, 기존 `bodoc-jira-automation`의 `ConfluenceClient`를 활용하여 `CONFLUENCE_QA_REPORT_PARENT_ID` 하위에 게시한다.

---

## KPI 해석 기준

수치 자체보다 **패턴**이 중요하다. 보고서 생성 후 다음 기준으로 인사이트를 제시한다.

**검증 완료율 해석:**

| 범위 | 의미 | 권고 |
|------|------|------|
| 0~30% | 발견만 하고 검증이 거의 없음 | 수정 후 재테스트 루틴 부재 가능성 |
| 30~70% | 일부 이슈만 검증 | 우선순위 높은 이슈에 검증 집중 권고 |
| 70~100% | 대부분 검증 완료 | 건강한 QA 사이클 |
| 100%+ | 발견 이상으로 검증 | 회귀 테스트나 추가 검증 포함 (긍정적) |

**활동 분포 해석:**

발견(issue_found)과 수정지시(fix_instruction) 비율이 비슷하면 QA가 개발 과정을 주도적으로 이끌고 있음을 의미한다.
분석(analysis) 비율이 지나치게 높으면(30% 이상) 재현이 어려운 이슈가 많거나 맥락 파악에 시간이 많이 소요되고 있음을 의미한다.
테스트케이스(test_case)가 0이면 탐색적 테스트 위주이며, 구조화된 테스트 케이스 작성이 추가 기여 기회임을 알린다.

**세션 생산성 해석:**

세션당 QA 활동이 3건 미만이면 해당 세션에서 QA 목적 외 작업(환경 설정, 코드 탐색 등)이 많았을 가능성이 있다. 이 지표는 QA 집중도의 간접 지표로 활용한다.

---

## 실행 시 단계 요약

```
1. scripts/collect_sessions.py 실행 → 원시 메시지 수집
2. 메시지 분류 (Claude prompt) → activity 태그 부여
3. scripts/aggregate_kpi.py 실행 → KPI 수치 계산
4. Markdown 보고서 생성 → 파일 저장 또는 Confluence 게시
5. (선택) 인사이트 한 줄 요약 출력
```

---

## 트러블슈팅

**메시지가 0건 수집되는 경우:**
`~/.claude/projects/` 경로를 직접 확인한다. Windows에서는 `C:\Users\{사용자명}\.claude\projects\`에 위치한다. 해당 경로에 `.jsonl` 파일이 있는지 확인하고, 없으면 Claude Code 세션이 해당 기간에 없었거나 경로가 다를 수 있다.

**파싱 오류가 많이 발생하는 경우:**
Claude Code 버전 업데이트 후 JSONL 포맷이 변경되었을 가능성이 있다. `scripts/collect_sessions.py` 상단의 `parse_jsonl_file` 함수에서 파싱 로직을 확인하고 새 포맷에 맞게 조정한다.

**분류 결과가 부정확한 경우:**
메시지가 매우 짧거나("OK", "됐어", "ㅇㅇ") 맥락 없이 단독으로 있으면 오분류될 수 있다. 이런 메시지는 직전 세션 메시지와 함께 묶어서 분류하면 정확도가 높아진다. Step 2의 분류 프롬프트에 "직전 메시지 맥락도 참고하세요"라는 지시를 추가한다.

**Confluence 게시 실패 시:**
`bodoc-jira-automation`의 `.env` 파일에 `CONFLUENCE_QA_REPORT_PARENT_ID`가 설정되어 있는지 확인한다. 미설정 시 Markdown 파일로만 저장된다. Confluence 인증 실패 시 `python bin/debug_jira.py`로 연결 상태를 확인한다.

---

## 자동화 옵션

이 스킬을 주간 리포트로 자동화하려면 Claude Code의 `/schedule` 기능을 활용한다:

```
/schedule 매주 월요일 오전 9시 QA session KPI 지난 7일 분석해줘
```

또는 Claude Code 설정의 cron hook에 주간 실행을 등록하여 Confluence에 자동 게시할 수 있다.

---

## 기존 프로젝트 연동

이 스킬은 `bodoc-jira-automation`의 기존 클라이언트를 재사용할 수 있다:

- **Confluence 게시**: `core/clients/confluence.py`의 `ConfluenceClient.publish_page()` 활용
- **차트 첨부**: `core/clients/confluence.py`의 `ConfluenceClient.attach_file()` 활용
- **설정 로드**: `config/settings.py`의 `Settings` 클래스 활용 (`.env`의 Atlassian 자격증명)

Confluence 게시 시 환경 변수 `CONFLUENCE_QA_REPORT_PARENT_ID`를 부모 페이지 ID로 사용한다.

---

## 한계와 주의사항

**Claude Code 세션 포맷 의존성:** `.jsonl` 파일 포맷은 Claude Code 버전에 따라 변경될 수 있다. 파싱 오류 시 `scripts/collect_sessions.py`를 확인한다.

**분류 정확도:** Claude의 메시지 분류는 맥락 기반이므로 100% 정확하지 않다. 짧거나 모호한 메시지("OK", "됐어")는 오분류될 수 있다.

**AI 기여도 미포함:** 이 스킬은 QA 엔지니어의 활동만 측정한다. AI(Claude)가 자율적으로 발견한 이슈나 수정은 별도 추적이 필요하다.

---

## 예시 출력

아래는 `qa_kpi_2026-05-04.md` 보고서의 예시 구조다:

```markdown
# QA Session KPI Report (2026-05-04, 최근 7일)

## 요약
| 지표 | 값 |
|------|-----|
| 총 QA 활동 수 | 47건 |
| 세션 수 | 12개 |
| 세션당 생산성 | 3.9건/세션 |
| 검증 완료율 | 72.7% |

## 활동 유형별 분포
| 유형 | 건수 |
|------|------|
| 이슈 발견 | 11건 |
| 수정 지시 | 18건 |
| 검증 | 8건 |
| 테스트 케이스 | 6건 |
| 분석 | 4건 |

## 일별 활동량
- 2026-04-28: 8건 (이슈발견: 3, 수정지시: 4, 검증: 1)
- 2026-04-29: 5건 ...
...

## 가장 활발했던 세션 TOP 5
- `session_abc123`: 12건
- `session_def456`: 9건
...

## 인사이트
- 검증 완료율 72.7% — 양호하나 8개 이슈가 미검증 상태입니다.
- 테스트 케이스 6건 작성됨 — 구조화된 테스트 기여 확인됩니다.
```

Confluence 게시 시 동일 내용이 HTML 형식으로 변환되어 게시된다.

---

## References
- **`references/activity-categories.md`** — QA 활동 유형별 분류 기준 및 애매한 케이스 판단 가이드

## Scripts
- **`scripts/collect_sessions.py`** — Claude Code 세션 JSONL 파일 파싱 및 사용자 메시지 추출
- **`scripts/aggregate_kpi.py`** — 분류 결과 집계, KPI 계산, Markdown 보고서 생성

## Settings

| 설정 | 기본값 | 변경 방법 |
|------|--------|-----------|
| 분석 기간 | 최근 7일 | "최근 30일로 분석해줘" 또는 `--days 30` |
| 프로젝트 필터 | 전체 프로젝트 | "bodoc-jira-automation만 봐줘" |
| 출력 형식 | Markdown 파일 | "Confluence에 올려줘" |
