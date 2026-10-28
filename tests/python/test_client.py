import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
import client as api_client  # noqa: E402
from client import ConfigurationError, CreationUnknownError, ProtocolError, TranscriptTransportError, get_transcript  # noqa: E402
from reliable_actor import APPROVED_BUILD_ID, ApiError  # noqa: E402
from offline_support import FakeTransport, fixture_items  # noqa: E402

URL = "https://www.facebook.com/watch/?v=1000000000000001"
CANONICAL = "https://www.facebook.com/watch/?v=1000000000000001"


def success_transport(items, *, build_number="0.0.18", build_id=APPROVED_BUILD_ID, polls=("SUCCEEDED",)):
    responses = [
        {
            "data": {
                "id": "run-synthetic",
                "defaultDatasetId": "dataset-synthetic",
                "buildNumber": build_number,
                "buildId": build_id,
            }
        }
    ]
    for status in polls:
        responses.append({"data": {"id": "run-synthetic", "status": status, "defaultDatasetId": "dataset-synthetic"}})
    responses.append(items)
    return FakeTransport(responses)


class SuccessTests(unittest.TestCase):
    def test_success_returns_text_segments_and_metadata(self):
        transport = success_transport(fixture_items("transcript-success.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "success")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.text, "This is a synthetic transcript used only by offline tests.")
        self.assertEqual(len(result.segments), 2)
        self.assertEqual(result.segments[0], {"start": 0, "end": 2.4, "text": "This is a synthetic transcript"})
        self.assertEqual(result.title, "Synthetic video for offline tests")
        self.assertEqual(result.duration, 43.5)
        self.assertEqual(result.nickname, "Synthetic Creator")
        self.assertEqual(result.run_id, "run-synthetic")
        self.assertEqual(result.dataset_id, "dataset-synthetic")
        self.assertEqual(result.canonical_url, CANONICAL)
        self.assertEqual(result.url_form, "watch")
        self.assertIsNone(result.error)

    def test_request_is_a_single_pinned_post_with_canonical_input(self):
        transport = success_transport(fixture_items("transcript-success.synthetic.json"))
        get_transcript(URL + "&mibextid=tracking", token="test-token", transport=transport)

        self.assertEqual(transport.post_count, 1)
        post = transport.requests[0]
        self.assertEqual(post["path"], "/acts/apple_yang~facebook-transcript-scraper-api/runs")
        self.assertEqual(post["body"], {"videoUrl": CANONICAL})
        self.assertEqual(post["query"], {"restartOnError": "false", "build": "0.0.18"})
        self.assertTrue(all(item["method"] == "GET" for item in transport.requests[1:]))

    def test_charge_cap_is_sent_as_a_run_option_not_as_input(self):
        transport = success_transport(fixture_items("transcript-success.synthetic.json"))
        get_transcript(URL, token="test-token", transport=transport, max_total_charge_usd="0.10")

        post = transport.requests[0]
        self.assertEqual(post["query"]["maxTotalChargeUsd"], 0.1)
        self.assertEqual(post["body"], {"videoUrl": CANONICAL})

    def test_raw_items_keep_unknown_and_undocumented_fields(self):
        transport = success_transport(fixture_items("extra-fields.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "success")
        raw = result.items[0]
        self.assertEqual(raw["someFutureField"], {"nested": True})
        self.assertEqual(raw["transcriptLanguage"], "en")
        self.assertEqual(raw["likesCount"], 3)
        self.assertEqual(raw["shareCount"], 2)

    def test_malformed_segments_are_dropped_only_from_the_normalized_view(self):
        transport = success_transport(fixture_items("segments-invalid.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "success")
        self.assertEqual(
            result.segments,
            [
                {"start": 0, "end": 1.2, "text": "valid one"},
                {"start": 4, "end": 5, "text": "valid two"},
            ],
        )
        self.assertEqual(len(result.items[0]["segments"]), 7)

    def test_dataset_visibility_lag_is_rechecked_on_the_same_dataset(self):
        items = fixture_items("transcript-success.synthetic.json")
        transport = FakeTransport(
            [
                {"data": {"id": "run-1", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                {"data": {"id": "run-1", "status": "SUCCEEDED", "defaultDatasetId": "ds-1"}},
                [],
                [],
                items,
            ]
        )
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "success")
        dataset_reads = [path for path in transport.paths if path.startswith("/datasets/")]
        self.assertEqual(len(dataset_reads), 3)
        self.assertTrue(all("/datasets/ds-1/items" in path for path in dataset_reads))


class BusinessStatusTests(unittest.TestCase):
    def test_actor_error_wins_even_when_text_is_present(self):
        transport = success_transport(fixture_items("transcript-actor-error.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "actor_error")
        self.assertFalse(result.succeeded)
        self.assertIn("not available in this region", result.error or "")
        self.assertEqual(result.items[0]["errMsg"], "Video is not available in this region")

    def test_empty_dataset(self):
        transport = FakeTransport(
            [
                {"data": {"id": "run-1", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                {"data": {"id": "run-1", "status": "SUCCEEDED", "defaultDatasetId": "ds-1"}},
                [],
                [],
                [],
            ]
        )
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "empty")
        self.assertIsNone(result.text)
        self.assertEqual(result.items, [])

    def test_running_status_is_polled_until_success(self):
        transport = success_transport(
            fixture_items("transcript-success.synthetic.json"), polls=("RUNNING", "RUNNING", "SUCCEEDED")
        )
        result = get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(result.status, "success")
        self.assertEqual(transport.post_count, 1)
        self.assertEqual(sum(1 for path in transport.paths if path.startswith("/actor-runs/")), 3)

    def test_null_text_is_no_transcript(self):
        transport = success_transport(fixture_items("no-transcript-null.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(result.status, "no_transcript")
        self.assertIsNone(result.text)

    def test_missing_text_is_no_transcript(self):
        transport = success_transport(fixture_items("no-transcript-missing.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(result.status, "no_transcript")

    def test_unsupported_text_type_is_unknown(self):
        transport = success_transport(fixture_items("unknown-text-type.synthetic.json"))
        result = get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(result.status, "unknown")

    def test_run_failed_status_is_returned_not_raised(self):
        transport = FakeTransport(
            [
                {"data": {"id": "run-1", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                {"data": {"id": "run-1", "status": "FAILED", "defaultDatasetId": "ds-1"}},
            ]
        )
        result = get_transcript(URL, token="test-token", transport=transport)

        self.assertEqual(result.status, "run_failed")
        self.assertIn("FAILED", result.error or "")
        self.assertEqual(transport.post_count, 1)

    def test_page_limit_marks_completeness_unknown(self):
        items = fixture_items("transcript-success.synthetic.json") * 2
        transport = success_transport(items)
        result = get_transcript(URL, token="test-token", transport=transport, dataset_limit=2)

        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.dataset_complete)


class FailureTests(unittest.TestCase):
    def test_missing_token_sends_no_request(self):
        transport = FakeTransport([])
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                get_transcript(URL, transport=transport)
        self.assertEqual(transport.requests, [])

    def test_required_charge_cap_fails_before_creation(self):
        transport = FakeTransport([])
        with self.assertRaises(ConfigurationError):
            get_transcript(URL, token="test-token", transport=transport, require_charge_cap=True)
        self.assertEqual(transport.post_count, 0)

    def test_ambiguous_create_is_not_retried(self):
        transport = FakeTransport([ApiError("timed out", None, None, True)])
        with self.assertRaises(CreationUnknownError):
            get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(transport.post_count, 1)

    def test_http_500_on_create_is_treated_as_ambiguous(self):
        transport = FakeTransport([ApiError("Apify HTTP 500", 500, None, True)])
        with self.assertRaises(CreationUnknownError):
            get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(transport.post_count, 1)

    def test_definite_create_rejection_is_a_transport_error(self):
        transport = FakeTransport([ApiError("Apify HTTP 400", 400, None, False)])
        with self.assertRaises(TranscriptTransportError):
            get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(transport.post_count, 1)

    def test_build_mismatch_raises_protocol_error_with_run_id(self):
        transport = success_transport(
            fixture_items("transcript-success.synthetic.json"), build_number="0.0.17"
        )
        with self.assertRaises(ProtocolError) as context:
            get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(context.exception.run_id, "run-synthetic")
        self.assertEqual(transport.post_count, 1)

    def test_post_run_retrieval_failure_keeps_the_run_id(self):
        transport = FakeTransport(
            [
                {"data": {"id": "run-1", "defaultDatasetId": "ds-1", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                ApiError("Apify HTTP 400", 400),
            ]
        )
        with self.assertRaises(TranscriptTransportError) as context:
            get_transcript(URL, token="test-token", transport=transport)
        self.assertEqual(context.exception.run_id, "run-1")
        self.assertEqual(transport.post_count, 1)

    def test_resume_never_posts(self):
        transport = FakeTransport(
            [
                {"data": {"id": "run-existing", "status": "SUCCEEDED", "defaultDatasetId": "ds-existing", "buildNumber": "0.0.18", "buildId": APPROVED_BUILD_ID}},
                fixture_items("transcript-success.synthetic.json"),
            ]
        )
        result = get_transcript(URL, token="test-token", transport=transport, run_id="run-existing")

        self.assertEqual(result.status, "success")
        self.assertEqual(transport.post_count, 0)
        self.assertEqual(transport.requests[0]["path"], "/actor-runs/run-existing")

    def test_invalid_run_id_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            get_transcript(URL, token="test-token", run_id=" run-1", transport=FakeTransport([]))


if __name__ == "__main__":
    unittest.main()
