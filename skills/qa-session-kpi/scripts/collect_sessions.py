#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta


def parse_jsonl_file(filepath: Path) -> list[dict]:
    messages = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Handle multiple possible session formats
                role = entry.get("role") or entry.get("type")
                content = entry.get("content", "")

                # Some formats wrap content in a list
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in content
                    )

                if role == "user" and content:
                    messages.append({
                        "timestamp": entry.get("timestamp", ""),
                        "content": str(content)[:2000],
                        "session": filepath.stem,
                        "project": filepath.parent.name,
                    })
    except Exception as e:
        print(f"WARN: could not parse {filepath}: {e}", file=sys.stderr)
    return messages


def collect(days: int, project_filter: str | None) -> dict:
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        print(
            json.dumps({"error": f"Claude projects dir not found: {claude_dir}"}),
        )
        sys.exit(1)

    cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()
    all_messages = []

    for proj_dir in claude_dir.iterdir():
        if not proj_dir.is_dir():
            continue
        if project_filter and project_filter.lower() not in proj_dir.name.lower():
            continue

        for jsonl_file in proj_dir.glob("*.jsonl"):
            if jsonl_file.stat().st_mtime < cutoff_ts:
                continue
            all_messages.extend(parse_jsonl_file(jsonl_file))

    return {
        "messages": all_messages,
        "count": len(all_messages),
        "days": days,
        "project_filter": project_filter,
    }


def main():
    parser = argparse.ArgumentParser(description="Collect Claude Code session messages")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--project", type=str, default=None, help="Filter by project name substring")
    args = parser.parse_args()

    result = collect(args.days, args.project)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
