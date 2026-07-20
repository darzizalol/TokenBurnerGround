#!/usr/bin/env python3
"""token-ledger.py — the night shift's token-burn accounting. Stdlib only.

Scans the claude CLI's transcript store for this repo, keeps only night-shift
role sessions (identified by their role-prompt fingerprint), sums every token
the API processed (input + output + cache write + cache read), writes
nightshift/tokens.csv, and regenerates the burn chart between the
TOKENBURN markers in the root README.md.

Usage: python3 token-ledger.py update
Run any time; it is a full idempotent rebuild from the transcripts.
Note: subagent (sidechain) transcripts can't be attributed to a parent
session, so they are excluded — totals are a slight undercount.
"""

import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
README = REPO / "README.md"
CSV_PATH = HERE / "tokens.csv"
TRANSCRIPTS = Path.home() / ".claude" / "projects" / str(REPO).replace("/", "-").replace(" ", "-")

ROLE_RE = re.compile(
    r"You are (?:the )?(ARCHITECT|ENGINEER|REVIEWER|QA|RELEASE MANAGER) on the night shift"
)

START_MARK = "<!-- TOKENBURN:START -->"
END_MARK = "<!-- TOKENBURN:END -->"


def first_user_text(rec):
    msg = rec.get("message") or {}
    if (rec.get("type") == "user" or msg.get("role") == "user"):
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return " ".join(b.get("text", "") for b in c if isinstance(b, dict))
    return None


def scan_session(path):
    """Return (start_local_dt, role, usage-dict) or None if not a night session."""
    role = None
    start = None
    sums = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    seen_ids = set()
    sidechain = False
    with open(path, errors="replace") as f:
        for i, line in enumerate(f):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("isSidechain"):
                sidechain = True
            if start is None and rec.get("timestamp"):
                try:
                    start = datetime.fromisoformat(
                        rec["timestamp"].replace("Z", "+00:00")
                    ).astimezone()
                except ValueError:
                    pass
            if role is None:
                text = first_user_text(rec)
                if text:
                    m = ROLE_RE.search(text)
                    if not m:
                        return None  # first user message isn't a role prompt
                    role = m.group(1) if m.group(1) == "QA" else m.group(1).title()
            usage = (rec.get("message") or {}).get("usage")
            if usage:
                mid = (rec.get("message") or {}).get("id") or f"line{i}"
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                sums["input"] += usage.get("input_tokens", 0)
                sums["output"] += usage.get("output_tokens", 0)
                sums["cache_write"] += usage.get("cache_creation_input_tokens", 0)
                sums["cache_read"] += usage.get("cache_read_input_tokens", 0)
    if role is None or start is None or sidechain:
        return None
    return start, role, sums


def night_of(dt):
    """22:00-07:00 window: early-morning sessions belong to the previous date."""
    return (dt - timedelta(days=1)).date() if dt.hour < 12 else dt.date()


def rebuild():
    rows = []
    for path in sorted(TRANSCRIPTS.glob("*.jsonl")):
        got = scan_session(path)
        if not got:
            continue
        start, role, s = got
        total = s["input"] + s["output"] + s["cache_write"] + s["cache_read"]
        if total == 0:
            continue
        rows.append({
            "timestamp": start.isoformat(timespec="seconds"),
            "night": night_of(start).isoformat(),
            "role": role,
            "session": path.stem[:8],
            "input": s["input"],
            "output": s["output"],
            "cache_write": s["cache_write"],
            "cache_read": s["cache_read"],
            "total": total,
        })
    rows.sort(key=lambda r: r["timestamp"])
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ["timestamp", "night", "role", "session",
                            "input", "output", "cache_write", "cache_read", "total"])
        w.writeheader()
        w.writerows(rows)
    return rows


def human(n):
    for div, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if n >= div:
            return f"{n / div:.1f}{suffix}"
    return str(n)


def chart(rows):
    nights, roles = {}, {}
    for r in rows:
        for bucket, key in ((nights, r["night"]), (roles, r["role"])):
            b = bucket.setdefault(key, {"sessions": 0, "input": 0, "output": 0,
                                        "cache_write": 0, "cache_read": 0, "total": 0})
            b["sessions"] += 1
            for k in ("input", "output", "cache_write", "cache_read", "total"):
                b[k] += r[k]
    grand = sum(b["total"] for b in nights.values())
    peak = max((b["total"] for b in nights.values()), default=1)

    lines = [
        f"### 🔥 {grand:,} tokens burnt so far",
        "",
        "_Every token processed by the autonomous night shift (input + output +"
        " cache write + cache read), mined from session transcripts and"
        " auto-updated at each 22:00 clock-in. Subagent sessions excluded, so"
        " this slightly undercounts._",
        "",
        "| Night | Sessions | Input | Output | Cache write | Cache read | Total | Burn |",
        "|---|---:|---:|---:|---:|---:|---:|:---|",
    ]
    for night in sorted(nights):
        b = nights[night]
        bar = "█" * max(1, round(20 * b["total"] / peak))
        lines.append(
            f"| {night} | {b['sessions']} | {human(b['input'])} | {human(b['output'])} "
            f"| {human(b['cache_write'])} | {human(b['cache_read'])} | **{human(b['total'])}** | {bar} |"
        )
    lines += ["", "| Role | Sessions | Total burnt |", "|---|---:|---:|"]
    for role in sorted(roles, key=lambda r: -roles[r]["total"]):
        b = roles[role]
        lines.append(f"| {role} | {b['sessions']} | {human(b['total'])} |")
    return "\n".join(lines)


def update_readme(block):
    text = README.read_text()
    if START_MARK not in text:
        text = text.rstrip() + (
            f"\n\n## Token burn\n\n{START_MARK}\n{block}\n{END_MARK}\n"
        )
    else:
        text = re.sub(
            re.escape(START_MARK) + ".*?" + re.escape(END_MARK),
            START_MARK + "\n" + block + "\n" + END_MARK,
            text,
            flags=re.S,
        )
    README.write_text(text)


def main():
    if len(sys.argv) != 2 or sys.argv[1] != "update":
        print(__doc__)
        return 1
    if not TRANSCRIPTS.is_dir():
        print(f"token-ledger: transcript dir not found: {TRANSCRIPTS}", file=sys.stderr)
        return 1
    rows = rebuild()
    update_readme(chart(rows))
    print(f"token-ledger: {len(rows)} night sessions, "
          f"{sum(r['total'] for r in rows):,} tokens; README + tokens.csv updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
