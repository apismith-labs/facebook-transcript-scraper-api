import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
import reliable_actor as runner  # noqa: E402
from reliable_actor import (  # noqa: E402
    APPROVED_BUILD_ID,
    APPROVED_BUILD_NUMBER,
    ApiError,
    RunJournal,
    classify_items,
    execute_input,
    load_resume_record,
    normalize_segments,
    sanitize,
    summarize,
    validate_build,
    validate_run_charge_cap,
)
from offline_support import FakeTransport, fixture_items  # noqa: E402

URL = "https://www.facebook.com/watch/?v=1000000000000001"


class ValidationTests(unittest.TestCase):
    def test_build_must_be_explicit_and_pinned(self):
        self.assertEqual(validate_build("0.0.18", required=True), "0.0.18")
        with self.assertRaises(ValueError):
            validate_build("latest", required=True)
        with self.assertRaises(ValueError):
            validate_build("0.0.17", required=True)
        with self.assertRaises(ValueError):
            validate_build("v0.0.18")

    def test_charge_cap(self):
        self.assertAlmostEqual(validate_run_charge_cap("0.10"), 0.1)
        self.assertIsNone(validate_run_charge_cap(""))
        for bad in ("0", "-1", "abc", "NaN", "Infinity"):
            with self.assertRaises(ValueError):
                validate_run_charge_cap(bad)
        with self.assertRaises(ValueError):
            validate_run_charge_cap(None, required=True)

    def test_classify_precedence(self):
        cases = {
            "empty": [],
            "actor_error": [{"text": "x", "errMsg": "boom"}],
            "success": [{"text": "hello", "errMsg": ""}],
            "no_transcript": [{"text": None, "errMsg": ""}],
            "unknown": [{"text": 7, "errMsg": ""}],
        }
        for expected, items in cases.items():
            self.assertEqual(classify_items(items)[0], expected, msg=expected)
        self.assertEqual(classify_items("not a list")[0], "unknown")
        self.assertEqual(classify_items([1])[0], "unknown")

    def test_normalize_segments_filters_invalid_entries(self):
        value = fixture_items("segments-invalid.synthetic.json")[0]["segments"]
        self.assertEqual(
            normalize_segments(value),
            [
                {"start": 0, "end": 1.2, "text": "valid one"},
                {"start": 4, "end": 5, "text": "valid two"},
            ],
        )
        self.assertEqual(normalize_segments(None), [])
        self.assertEqual(normalize_segments([{"start": True, "end": 2, "text": "x"}]), [])

    def test_sanitize_removes_credentials_recursively(self):
        payload = {
            "APIFY_TOKEN": "secret",
            "nested": [{"authorization": "Bearer abc", "text": "Bearer abcdef"}],
        }
        cleaned = sanitize(payload)
        self.assertNotIn("APIFY_TOKEN", cleaned)
        self.assertNotIn("authorization", cleaned["nested"][0])
        self.assertEqual(cleaned["nested"][0]["text"], "Bearer [REDACTED]")

    def test_summarize_counts_every_status(self):
        counts = summarize([{"status": "success"}, {"status": "actor_error"}, {"status": "weird"}])
        self.assertEqual(counts["success"], 1)
        self.assertEqual(counts["actor_error"], 1)
        self.assertEqual(counts["unknown"], 1)
        self.assertEqual(counts["processed"], 3)
        self.assertEqual(counts["failed"], 2)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.jsonl"

    def test_append_and_latest(self):
        journal = RunJournal(self.path)
        journal.append({"runId": "run-1", "stage": "creating"})
        journal.append({"runId": "run-1", "stage": "complete"})
        self.assertEqual(journal.latest("run-1")["stage"], "complete")
        self.assertIsNone(journal.latest("run-2"))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_corrupt_journal_refuses_append_and_resume(self):
        self.path.write_text('{"ok": true}\nnot json\n', encoding="utf-8")
        journal = RunJournal(self.path)
        with self.assertRaises(ValueError):
            journal.append({"runId": "run-1"})
        with self.assertRaises(ValueError):
            journal.latest("run-1")

    def test_resume_record_requires_matching_identity(self):
        journal = RunJournal(self.path)
        journal.append(
            {
                "runId": "run-1",
                "actorId": "apple_yang/facebook-transcript-scraper-api",
                "sourceUrl": URL,
                "datasetId": "ds-1",
            }
        )
        record = load_resume_record(journal, "run-1", "apple_yang/facebook-transcript-scraper-api")
        self.assertEqual(record["datasetId"], "ds-1")
        with self.assertRaises(ValueError):
            load_resume_record(journal, "run-1", "someone/else")
        with self.assertRaises(ValueError):
            load_resume_record(journal, "run-404", "apple_yang/facebook-transcript-scraper-api")


class ExecuteInputTests(unittest.TestCase):
    def make_journal(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return RunJournal(Path(tmp.name) / "journal.jsonl")

    def test_retries_transient_get_failures(self):
        transport = FakeTransport(
            [
                {"data": {"id": "run-1", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                ApiError("Apify HTTP 503", 503, None, False),
                ApiError("Apify HTTP 503", 503, None, False),
                {"data": {"id": "run-1", "status": "SUCCEEDED", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                fixture_items("transcript-success.synthetic.json"),
            ]
        )
        outcome = execute_input(
            transport=transport,
            actor_id="apple_yang/facebook-transcript-scraper-api",
            run_input={"videoUrl": URL},
            source_url=URL,
            journal=self.make_journal(),
            build="0.0.18",
            require_build=True,
            dataset_limit=100,
            sleep=lambda _seconds: None,
        )
        self.assertEqual(outcome["status"], "success")
        self.assertEqual(transport.post_count, 1)

    def test_exhausted_retries_return_transport_error(self):
        transport = FakeTransport(
            [
                {"data": {"id": "run-1", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                ApiError("Apify HTTP 503", 503, None, False),
                ApiError("Apify HTTP 503", 503, None, False),
                ApiError("Apify HTTP 503", 503, None, False),
                ApiError("Apify HTTP 503", 503, None, False),
            ]
        )
        outcome = execute_input(
            transport=transport,
            actor_id="apple_yang/facebook-transcript-scraper-api",
            run_input={"videoUrl": URL},
            source_url=URL,
            journal=self.make_journal(),
            build="0.0.18",
            require_build=True,
            dataset_limit=100,
            sleep=lambda _seconds: None,
        )
        self.assertEqual(outcome["status"], "transport_error")
        self.assertEqual(outcome["runId"], "run-1")
        self.assertEqual(transport.post_count, 1)

    def test_missing_run_id_in_create_response_is_creation_unknown(self):
        transport = FakeTransport([{"data": {"defaultDatasetId": "ds-1"}}])
        outcome = execute_input(
            transport=transport,
            actor_id="apple_yang/facebook-transcript-scraper-api",
            run_input={"videoUrl": URL},
            source_url=URL,
            journal=self.make_journal(),
            build="0.0.18",
            require_build=True,
        )
        self.assertEqual(outcome["status"], "creation_unknown")
        self.assertEqual(transport.post_count, 1)

    def test_default_build_is_the_audited_build(self):
        self.assertEqual(APPROVED_BUILD_NUMBER, "0.0.18")
        self.assertEqual(APPROVED_BUILD_ID, "fZIlpYENof2jYqIJc")
        self.assertEqual(runner.DEFAULT_ACTOR_ID, "apple_yang/facebook-transcript-scraper-api")


if __name__ == "__main__":
    unittest.main()
