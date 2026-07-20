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
    """Animated burn counter: flickering flame + odometer roll-up of the total.

    Robustness rules learned the hard way:
    - no clip-path (browsers disagree on whether it follows CSS transforms);
      each digit rolls inside its own nested <svg> viewport, which clips
      natively everywhere.
    - digits animate with SMIL, and the RESTING state is the final number,
      so a renderer without animation still shows the correct total.
    """
    text = f"{total:,}"
    comma_w = 18
    widths = [DIGIT_W if ch.isdigit() else comma_w for ch in text]
    num_w = sum(widths)
    width = max(560, 150 + num_w + 40)
    cx = 150  # number block start x
    top = 84  # digit window top; baseline inside a column is 50

    cols, x = [], cx
    for i, ch in enumerate(text):
        if ch.isdigit():
            d = int(ch)
            off = d * DIGIT_H  # roll distance
            delay = 0.12 * i
            dur = delay + 0.9 + 0.07 * d
            t1 = f"{delay / dur:.3f}" if dur else "0"
            strip = "".join(
                f'<text x="{DIGIT_W // 2}" y="{50 + n * DIGIT_H}" class="num" '
                f'text-anchor="middle">{n}</text>'
                for n in range(10)
            )
            cols.append(
                f'<svg x="{x}" y="{top}" width="{DIGIT_W}" height="{DIGIT_H}" '
                f'viewBox="0 0 {DIGIT_W} {DIGIT_H}">'
                f'<g transform="translate(0,{-off})"><g>'
                f'<animateTransform attributeName="transform" type="translate" '
                f'values="0 {off};0 {off};0 0" keyTimes="0;{t1};1" '
                f'dur="{dur:.2f}s" begin="0s" fill="freeze" additive="sum" '
                f'calcMode="spline" keySplines="0 0 1 1;.2 .7 .3 1"/>'
                f"{strip}</g></g></svg>"
            )
        else:
            cols.append(
                f'<text x="{x + comma_w // 2}" y="{top + 50}" class="num comma" '
                f'text-anchor="middle">{ch}</text>'
            )
        x += widths[i]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="200" viewBox="0 0 {width} 200" role="img" aria-label="{text} tokens burnt">
<style>
.num{{font:700 56px ui-monospace,'Cascadia Code',Menlo,Consolas,monospace;fill:#ffd166}}
.comma{{fill:#8b6a2b}}
.label{{font:600 15px -apple-system,'Segoe UI',sans-serif;fill:#e8883a;letter-spacing:4px}}
.sub{{font:400 12px -apple-system,'Segoe UI',sans-serif;fill:#6e5a3a}}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#1c1208"/>
</linearGradient>
<linearGradient id="fg" x1="0" y1="1" x2="0" y2="0">
<stop offset="0" stop-color="#ff5a00"/><stop offset=".6" stop-color="#ff9e2c"/><stop offset="1" stop-color="#ffd166"/>
</linearGradient>
<radialGradient id="halo"><stop offset="0" stop-color="#ff7b00"/><stop offset="1" stop-color="#ff7b00" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{width}" height="200" rx="16" fill="url(#bg)" stroke="#3a2a12"/>
<circle cx="60" cy="105" r="70" fill="url(#halo)" opacity=".35">
<animate attributeName="opacity" values=".25;.55;.25" dur="2.2s" repeatCount="indefinite"/>
</circle>
<g transform="translate(60,128)"><g>
<animateTransform attributeName="transform" type="scale" values="1 1;.95 1.1;1 1" dur="1.6s" repeatCount="indefinite" additive="sum" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1"/>
<path d="M0 -80c4 16 22 24 22 46a22 22 0 1 1-44 0c0-10 5-16 10-22 1 8 3 11 7 14-2-14 1-26 5-38z" fill="url(#fg)"/>
<path d="M0 -42c2 8 10 12 10 22a10 10 0 1 1-20 0c0-9 7-13 10-22z" fill="#fff3c4">
<animateTransform attributeName="transform" type="scale" values="1 1;1.06 .92;1 1" dur="1.1s" repeatCount="indefinite" additive="sum" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1"/>
</path>
</g></g>
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
