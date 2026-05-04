#!/usr/bin/env python3
import sys
import json
import argparse
from collections import defaultdict
from datetime import datetime


ACTIVITY_TYPES = ["issue_found", "fix_instruction", "verification", "test_case", "analysis"]


def aggregate(classified: list[dict]) -> dict:
    by_type: dict[str, int] = defaultdict(int)
    by_date: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_session: dict[str, int] = defaultdict(int)

    for msg in classified:
        activity = msg.get("activity", "other")
        date = msg.get("timestamp", "")[:10] or "unknown"
        session = msg.get("session", "unknown")

        if activity in ACTIVITY_TYPES:
            by_type[activity] += 1
            by_date[date][activity] += 1
            by_session[session] += 1

    total_qa = sum(by_type.values())
    session_count = len(by_session)

    verification_rate = 0.0
    if by_type.get("issue_found", 0) > 0:
        verification_rate = by_type.get("verification", 0) / by_type["issue_found"] * 100

    return {
        "summary": {
            "total_qa_activities": total_qa,
            "session_count": session_count,
            "session_productivity": round(total_qa / session_count, 1) if session_count else 0,
            "verification_rate_pct": round(verification_rate, 1),
        },
        "by_type": dict(by_type),
        "by_date": {date: dict(counts) for date, counts in sorted(by_date.items())},
        "top_sessions": sorted(by_session.items(), key=lambda x: x[1], reverse=True)[:5],
    }


def render_markdown(kpi: dict, days: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    s = kpi["summary"]
    bt = kpi["by_type"]

    lines = [
        f"# QA Session KPI Report ({today}, 최근 {days}일)",
        "",
        "## 요약",
        f"| 지표 | 값 |",
        f"|------|-----|",
        f"| 총 QA 활동 수 | {s['total_qa_activities']}건 |",
        f"| 세션 수 | {s['session_count']}개 |",
        f"| 세션당 생산성 | {s['session_productivity']}건/세션 |",
        f"| 검증 완료율 | {s['verification_rate_pct']}% |",
        "",
        "## 활동 유형별 분포",
        f"| 유형 | 건수 |",
        f"|------|------|",
    ]
    labels = {
        "issue_found": "이슈 발견",
        "fix_instruction": "수정 지시",
        "verification": "검증",
        "test_case": "테스트 케이스",
        "analysis": "분석",
    }
    for key in ACTIVITY_TYPES:
        lines.append(f"| {labels[key]} | {bt.get(key, 0)}건 |")

    lines += ["", "## 일별 활동량"]
    for date, counts in kpi["by_date"].items():
        total = sum(counts.values())
        lines.append(f"- **{date}**: {total}건 ({', '.join(f'{labels.get(k,k)}: {v}' for k, v in counts.items())})")

    lines += [
        "",
        "## 가장 활발했던 세션 TOP 5",
    ]
    for session, count in kpi["top_sessions"]:
        lines.append(f"- `{session}`: {count}건")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate classified QA activities into KPI report")
    parser.add_argument("input", nargs="?", help="JSON file with classified messages (default: stdin)")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    classified = data if isinstance(data, list) else data.get("messages", [])
    kpi = aggregate(classified)

    if args.output == "json":
        print(json.dumps(kpi, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(kpi, args.days))


if __name__ == "__main__":
    main()
