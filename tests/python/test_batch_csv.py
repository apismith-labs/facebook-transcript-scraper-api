import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
import batch_csv  # noqa: E402
from batch_csv import CsvRow, estimate_rows, main, parse_rows, run_batch  # noqa: E402
from reliable_actor import APPROVED_BUILD_ID, ApiError, RunJournal  # noqa: E402
from offline_support import FakeTransport, fixture_items  # noqa: E402

ITEMS = fixture_items("transcript-success.synthetic.json")


class CsvParsingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, text, name="input.csv", encoding="utf-8"):
        path = self.dir / name
        path.write_text(text, encoding=encoding)
        return path

    def test_rows_keep_line_numbers_and_canonical_urls(self):
        path = self.write(
            "videoUrl\n"
            "https://www.facebook.com/watch/?v=101\n"
            "\n"
            "https://www.facebook.com/reel/202/?mibextid=x\n"
        )
        rows = parse_rows(path)
        self.assertEqual([row.row_id for row in rows], ["2", "4"])
        self.assertEqual(rows[0].canonical_url, "https://www.facebook.com/watch/?v=101")
        self.assertEqual(rows[1].url_form, "reel")

    def test_duplicate_urls_remain_separate_rows(self):
        path = self.write(
            "videoUrl\n"
            "https://www.facebook.com/reel/303/\n"
            "https://www.facebook.com/reel/303/\n"
        )
        rows = parse_rows(path)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0].row_id, rows[1].row_id)

    def test_url_header_and_bom_are_accepted(self):
        path = self.write(
            "\ufeffurl,durationSeconds\nhttps://www.facebook.com/videos/404/,90\n",
            encoding="utf-8",
        )
        rows = parse_rows(path)
        self.assertEqual(rows[0].canonical_url, "https://www.facebook.com/videos/404/")
        self.assertEqual(rows[0].duration_seconds, 90)

    def test_invalid_row_fails_before_any_run(self):
        path = self.write("videoUrl\nhttps://www.instagram.com/reel/abc/\n")
        with self.assertRaises(batch_csv.ConfigurationError) as context:
            parse_rows(path)
        self.assertIn("CSV line 2", str(context.exception))

    def test_missing_column_is_rejected(self):
        path = self.write("links\nhttps://www.facebook.com/reel/505/\n")
        with self.assertRaises(batch_csv.ConfigurationError):
            parse_rows(path)

    def test_bad_duration_is_rejected(self):
        path = self.write("videoUrl,durationSeconds\nhttps://www.facebook.com/reel/606/,abc\n")
        with self.assertRaises(batch_csv.ConfigurationError):
            parse_rows(path)

    def test_empty_file_is_rejected(self):
        path = self.write("videoUrl\n\n")
        with self.assertRaises(batch_csv.ConfigurationError):
            parse_rows(path)


class EstimateTests(unittest.TestCase):
    def test_estimate_uses_per_row_durations(self):
        rows = [
            CsvRow("2", "https://www.facebook.com/watch/?v=1", "https://www.facebook.com/watch/?v=1", "watch", 600),
            CsvRow("3", "https://www.facebook.com/reel/2/", "https://www.facebook.com/reel/2/", "reel", None),
        ]
        estimate = estimate_rows(rows, "FREE")
        self.assertEqual(estimate["billedMinutes"], 11)
        self.assertAlmostEqual(estimate["totalUsd"], 0.002 + 0.0495)
        self.assertTrue(estimate["lowerBound"])

    def test_unknown_tier_is_rejected(self):
        rows = [CsvRow("2", "u", "u", "reel", 1)]
        with self.assertRaises(batch_csv.ConfigurationError):
            estimate_rows(rows, "ENTERPRISE")


class BatchExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.rows = [
            CsvRow("2", "https://www.facebook.com/watch/?v=701", "https://www.facebook.com/watch/?v=701", "watch", 30),
            CsvRow("3", "https://www.facebook.com/reel/702/", "https://www.facebook.com/reel/702/", "reel", 30),
        ]

    def factory(self):
        return FakeTransport(
            [
                {"data": {"id": "run-x", "defaultDatasetId": "ds-x", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                {"data": {"id": "run-x", "status": "SUCCEEDED", "defaultDatasetId": "ds-x"}},
                ITEMS,
            ]
        )

    def test_each_row_is_one_run_and_results_keep_input_order(self):
        journal = RunJournal(self.dir / "journal.jsonl", lock=threading.Lock())
        results = run_batch(
            self.rows,
            token="test-token",
            max_concurrency=2,
            journal=journal,
            transport_factory=self.factory,
        )
        self.assertEqual([row["rowId"] for row in results], ["2", "3"])
        self.assertTrue(all(row["status"] == "success" for row in results))
        self.assertTrue(all(row["text"] for row in results))
        records = [json_line for json_line in journal.path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), len(self.rows) * 5)
        self.assertEqual({json.loads(line)["rowId"] for line in records}, {"2", "3"})

    def test_one_failed_row_does_not_stop_the_others(self):
        calls = {"count": 0}
        lock = threading.Lock()

        def factory():
            with lock:
                calls["count"] += 1
                index = calls["count"]
            if index == 1:
                return FakeTransport([ApiError("Apify HTTP 400", 400, None, False)])
            return self.factory()

        results = run_batch(
            self.rows,
            token="test-token",
            max_concurrency=1,
            transport_factory=factory,
        )
        statuses = [row["status"] for row in results]
        self.assertIn("transport_error", statuses)
        self.assertIn("success", statuses)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.csv = self.dir / "input.csv"
        self.csv.write_text(
            "videoUrl,durationSeconds\n"
            "https://www.facebook.com/watch/?v=801,120\n",
            encoding="utf-8",
        )

    def test_plan_only_creates_nothing(self):
        buffer = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(buffer):
            code = main([str(self.csv)])
        self.assertEqual(code, 0)
        self.assertIn("Plan only", buffer.getvalue())
        self.assertEqual(sorted(path.name for path in self.dir.iterdir()), ["input.csv"])

    def test_execute_without_token_fails_before_writing_results(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = main([str(self.csv), "--execute"])
        self.assertEqual(code, 2)
        self.assertEqual(sorted(path.name for path in self.dir.iterdir()), ["input.csv"])

    def test_invalid_csv_exits_two(self):
        self.csv.write_text("videoUrl\nhttps://example.com/reel/1/\n", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            code = main([str(self.csv)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
