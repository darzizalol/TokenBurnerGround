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


SVG_PATH = HERE / "burn.svg"
DIGIT_H = 64          # odometer line height
DIGIT_W = 34          # monospace digit advance at font-size 56


def burn_svg(total, as_of):
    """Animated burn counter: flickering flame + odometer roll-up of the total."""
    text = f"{total:,}"
    # layout: flame block (~120px) + digits/commas
    widths = [DIGIT_W if ch.isdigit() else 16 for ch in text]
    num_w = sum(widths)
    width = max(560, 150 + num_w + 60)
    cx = 150  # number block start x

    cols, keyframes, x = [], [], cx
    for i, ch in enumerate(text):
        if ch.isdigit():
            d = int(ch)
            strip = "".join(
                f'<text x="{x}" y="{132 + n * DIGIT_H}" class="num">{n}</text>'
                for n in range(10)
            )
            delay = 0.15 * i
            keyframes.append(
                f"@keyframes r{i}{{from{{transform:translateY(0)}}"
                f"to{{transform:translateY({-d * DIGIT_H}px)}}}}"
                f".c{i}{{animation:r{i} {0.9 + 0.08 * d:.2f}s "
                f"cubic-bezier(.2,.7,.3,1) {delay:.2f}s forwards}}"
            )
            cols.append(f'<g class="c{i}" clip-path="url(#w)">{strip}</g>')
        else:
            cols.append(f'<text x="{x}" y="132" class="num comma">{ch}</text>')
        x += widths[i]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="200" viewBox="0 0 {width} 200" role="img" aria-label="{text} tokens burnt">
<style>
.num{{font:700 56px ui-monospace,'Cascadia Code',Menlo,monospace;fill:#ffd166}}
.comma{{fill:#8b6a2b}}
.label{{font:600 15px -apple-system,'Segoe UI',sans-serif;fill:#e8883a;letter-spacing:4px}}
.sub{{font:400 12px -apple-system,'Segoe UI',sans-serif;fill:#6e5a3a}}
.flame{{transform-origin:60px 128px;animation:fl 1.6s ease-in-out infinite}}
.flame2{{transform-origin:60px 124px;animation:fl 1.1s ease-in-out .4s infinite}}
@keyframes fl{{0%,100%{{transform:scaleY(1) scaleX(1)}}50%{{transform:scaleY(1.12) scaleX(.94)}}}}
.glow{{animation:gl 2.2s ease-in-out infinite}}
@keyframes gl{{0%,100%{{opacity:.25}}50%{{opacity:.55}}}}
{"".join(keyframes)}
</style>
<defs>
<clipPath id="w"><rect x="0" y="84" width="{width}" height="{DIGIT_H}"/></clipPath>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#1c1208"/>
</linearGradient>
<linearGradient id="fg" x1="0" y1="1" x2="0" y2="0">
<stop offset="0" stop-color="#ff5a00"/><stop offset=".6" stop-color="#ff9e2c"/><stop offset="1" stop-color="#ffd166"/>
</linearGradient>
<radialGradient id="halo"><stop offset="0" stop-color="#ff7b00"/><stop offset="1" stop-color="#ff7b00" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{width}" height="200" rx="16" fill="url(#bg)" stroke="#3a2a12"/>
<circle class="glow" cx="60" cy="105" r="70" fill="url(#halo)"/>
<g class="flame"><path d="M60 48c4 16 22 24 22 46a22 22 0 1 1-44 0c0-10 5-16 10-22 1 8 3 11 7 14-2-14 1-26 5-38z" fill="url(#fg)"/></g>
<g class="flame2"><path d="M60 86c2 8 10 12 10 22a10 10 0 1 1-20 0c0-9 7-13 10-22z" fill="#fff3c4"/></g>
<text x="{cx}" y="62" class="label">TOKENS BURNT</text>
{"".join(cols)}
<text x="{cx}" y="172" class="sub">by the autonomous night shift · updated nightly · as of {as_of}</text>
</svg>'''


def chart(rows):
    total = sum(r["total"] for r in rows)
    as_of = datetime.now().date().isoformat()
    SVG_PATH.write_text(burn_svg(total, as_of))
    return (
        f'<p align="center">\n'
        f'  <img src="nightshift/burn.svg" alt="{total:,} tokens burnt so far" width="560">\n'
        f'</p>'
    )


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
