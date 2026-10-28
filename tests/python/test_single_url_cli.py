import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
import single_url  # noqa: E402
from client import TranscriptResult  # noqa: E402

URL = "https://www.facebook.com/watch/?v=901"


class CliTests(unittest.TestCase):
    def setUp(self):
        # A developer's real .env must never turn these tests into billable Runs.
        patcher = patch.dict(os.environ, {"APIFY_SKIP_DOTENV": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_help_exits_zero(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as context:
            single_url.main(["--help"])
        self.assertEqual(context.exception.code, 0)

    def test_invalid_url_exits_two_without_network(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            code = single_url.main(["https://example.com/reel/1/", "--no-journal"])
        self.assertEqual(code, 2)
        self.assertIn("Configuration error", error.getvalue())

    def test_missing_token_exits_two(self):
        # clear=True wipes the setUp flag too, so the skip flag has to be restated here.
        cleared = {"APIFY_SKIP_DOTENV": "1"}
        with patch.dict(os.environ, cleared, clear=True), contextlib.redirect_stderr(io.StringIO()) as error:
            code = single_url.main([URL, "--no-journal"])
        self.assertEqual(code, 2)
        self.assertIn("APIFY_TOKEN", error.getvalue())

    def test_dotenv_is_ignored_when_the_skip_flag_is_set(self):
        # Repo root is the test cwd, so a real .env would be visible here.
        if not (ROOT / ".env").is_file():
            self.skipTest("no .env in the repository root; nothing to ignore")
        with patch.dict(os.environ, {"APIFY_SKIP_DOTENV": "1"}, clear=True):
            single_url.load_env_file(ROOT / ".env")
            self.assertNotIn("APIFY_TOKEN", os.environ)

    def test_json_output_uses_the_result_shape(self):
        result = TranscriptResult(
            status="success",
            text="synthetic text",
            segments=[{"start": 0, "end": 1, "text": "synthetic text"}],
            items=[{"text": "synthetic text", "errMsg": ""}],
            run_id="run-1",
            dataset_id="ds-1",
            source_url=URL,
            canonical_url=URL,
            url_form="watch",
            error=None,
            dataset_complete=True,
            title="Synthetic",
            duration=1.0,
            nickname="Creator",
        )
        buffer = io.StringIO()
        with patch.object(single_url, "get_transcript", return_value=result), contextlib.redirect_stdout(buffer):
            code = single_url.main([URL, "--json", "--no-journal"])
        payload = json.loads(buffer.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["runId"], "run-1")
        self.assertEqual(payload["canonicalUrl"], URL)
        self.assertEqual(payload["segments"][0]["text"], "synthetic text")

    def test_non_success_exit_code_matches_status(self):
        result = TranscriptResult(
            status="no_transcript",
            text=None,
            segments=[],
            items=[{"text": None, "errMsg": ""}],
            run_id="run-2",
            dataset_id="ds-2",
            source_url=URL,
            canonical_url=URL,
            url_form="watch",
            error="Transcript text is null",
            dataset_complete=True,
        )
        with patch.object(single_url, "get_transcript", return_value=result), contextlib.redirect_stdout(io.StringIO()):
            code = single_url.main([URL, "--no-journal"])
        self.assertEqual(code, 6)


if __name__ == "__main__":
    unittest.main()
