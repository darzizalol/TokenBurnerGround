#!/usr/bin/env python3
"""Unit tests for token-ledger.py's month-total accounting.

Run: python3 -m unittest discover -s nightshift/tests -v
Loads token-ledger.py by path (its filename isn't a valid module name) and
points its TRANSCRIPTS/CACHE_PATH globals at a throwaway temp dir per test,
so nothing here touches the real ~/.claude transcript store or ledger cache.
"""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / "token-ledger.py"


def load_module():
    spec = importlib.util.spec_from_file_location("token_ledger", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def role_record(text, timestamp):
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {"role": "user", "content": text},
    }


def usage_record(msg_id, timestamp, input_tokens=0, output_tokens=0,
                  cache_write=0, cache_read=0, sidechain=False):
    rec = {
        "type": "assistant",
        "timestamp": timestamp,
        "message": {
            "id": msg_id,
            "role": "assistant",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_write,
                "cache_read_input_tokens": cache_read,
            },
        },
    }
    if sidechain:
        rec["isSidechain"] = True
    return rec


class TokenLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.module = load_module()
        self.transcripts = self.tmp / "transcripts"
        self.transcripts.mkdir()
        self.module.TRANSCRIPTS = self.transcripts
        self.module.CACHE_PATH = self.tmp / ".ledger-cache.json"

    def write_session(self, name, records):
        path = self.transcripts / f"{name}.jsonl"
        with open(path, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
        return path

    def engineer_session(self, name, timestamp, tokens=100, msg_id=None):
        return self.write_session(name, [
            role_record("You are the ENGINEER on the night shift.", timestamp),
            usage_record(msg_id or f"{name}-msg", timestamp,
                         input_tokens=tokens, output_tokens=0),
        ])

    def test_night_of_before_noon_belongs_to_previous_day(self):
        from datetime import datetime
        dt = datetime(2026, 8, 6, 1, 30)
        self.assertEqual(self.module.night_of(dt).isoformat(), "2026-08-05")

    def test_night_of_after_noon_belongs_to_same_day(self):
        from datetime import datetime
        dt = datetime(2026, 8, 6, 23, 0)
        self.assertEqual(self.module.night_of(dt).isoformat(), "2026-08-06")

    def test_scan_session_ignores_non_role_transcript(self):
        path = self.write_session("not-a-role", [
            role_record("just chatting, not a night shift session", "2026-08-05T23:00:00Z"),
            usage_record("m1", "2026-08-05T23:00:01Z", input_tokens=10),
        ])
        self.assertIsNone(self.module.scan_session(path))

    def test_scan_session_sums_usage_and_dedupes_by_message_id(self):
        path = self.write_session("dedupe", [
            role_record("You are the ENGINEER on the night shift.", "2026-08-05T23:00:00Z"),
            usage_record("m1", "2026-08-05T23:00:01Z", input_tokens=100, output_tokens=20),
            usage_record("m1", "2026-08-05T23:00:02Z", input_tokens=100, output_tokens=20),
            usage_record("m2", "2026-08-05T23:00:03Z", input_tokens=5, output_tokens=1),
        ])
        start, role, sums = self.module.scan_session(path)
        self.assertEqual(role, "Engineer")
        # m1's usage is counted once despite appearing on two lines.
        self.assertEqual(sums["input"], 105)
        self.assertEqual(sums["output"], 21)

    def test_scan_session_excludes_sidechain_transcripts(self):
        path = self.write_session("sidechain", [
            role_record("You are the ENGINEER on the night shift.", "2026-08-05T23:00:00Z"),
            usage_record("m1", "2026-08-05T23:00:01Z", input_tokens=100, sidechain=True),
        ])
        self.assertIsNone(self.module.scan_session(path))

    def test_month_total_sums_only_the_requested_month(self):
        # Night of 2026-07-31 (started 23:xx on the 31st) belongs to July.
        self.engineer_session("july-night", "2026-07-31T23:00:00Z", tokens=1000)
        # A session starting 01:30 on Aug 1 is still the night of July 31st.
        self.engineer_session("july-spillover", "2026-08-01T01:30:00Z", tokens=500)
        # An ordinary August session.
        self.engineer_session("august-night", "2026-08-05T23:00:00Z", tokens=2000)
        self.assertEqual(self.module.month_total("2026-07"), 1500)
        self.assertEqual(self.module.month_total("2026-08"), 2000)

    def test_month_total_zero_when_no_sessions(self):
        self.assertEqual(self.module.month_total("2026-01"), 0)

    def test_scan_all_uses_cache_to_skip_unchanged_files(self):
        path = self.engineer_session("cached", "2026-08-05T23:00:00Z", tokens=42)
        first = self.module.scan_all()
        self.assertEqual(sum(r["total"] for r in first), 42)

        calls = []
        real_scan_session = self.module.scan_session

        def counting_scan_session(p):
            calls.append(p)
            return real_scan_session(p)

        self.module.scan_session = counting_scan_session
        try:
            second = self.module.scan_all()
        finally:
            self.module.scan_session = real_scan_session

        self.assertEqual(calls, [])  # unchanged file, stat matched -> cache hit
        self.assertEqual(sum(r["total"] for r in second), 42)

    def test_scan_all_rescans_when_file_changes(self):
        path = self.engineer_session("growing", "2026-08-05T23:00:00Z", tokens=10)
        self.module.scan_all()
        # Simulate the session continuing: append more usage, changing size/mtime.
        with open(path, "a") as f:
            f.write(json.dumps(usage_record("growing-msg-2", "2026-08-05T23:05:00Z",
                                              input_tokens=90)) + "\n")
        second = self.module.scan_all()
        self.assertEqual(sum(r["total"] for r in second), 100)


if __name__ == "__main__":
    unittest.main()
