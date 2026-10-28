import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
from reliable_actor import APPROVED_BUILD_ID, APPROVED_BUILD_NUMBER, classify_items  # noqa: E402
import cost  # noqa: E402
from offline_support import FIXTURE_DIR, load_fixture  # noqa: E402

CONTRACT = ROOT / "docs/audit/contracts/facebook-transcript-scraper-api-0.0.18.json"


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_pins_the_same_build_as_the_clients(self):
        self.assertEqual(self.contract["actor"]["buildNumber"], APPROVED_BUILD_NUMBER)
        self.assertEqual(self.contract["actor"]["buildId"], APPROVED_BUILD_ID)

    def test_actor_has_exactly_one_input_field(self):
        fields = self.contract["input"]["fields"]
        self.assertEqual(list(fields), ["videoUrl"])
        self.assertEqual(self.contract["input"]["required"], ["videoUrl"])
        for absent in ("bulkUrls", "usernames", "sessionid"):
            self.assertIn(absent, self.contract["input"]["absentFields"])

    def test_dataset_fixture_matches_the_contract_field_set(self):
        fields = set(self.contract["output"]["datasetFields"])
        item = load_fixture("transcript-success.synthetic.json")["items"][0]
        self.assertEqual(fields, set(item))
        self.assertEqual(len(fields), 17)

    def test_undocumented_fields_are_recorded(self):
        self.assertEqual(
            sorted(self.contract["output"]["documentedButNotInReadme"]), ["likesCount", "shareCount"]
        )

    def test_pricing_snapshot_matches_the_cost_model(self):
        events = self.contract["pricing"]["events"]
        self.assertAlmostEqual(events["apify-default-dataset-item"]["priceUsd"], float(cost.DATASET_ITEM_USD))
        tiers = events["speech2text"]["tieredPriceUsdPerMinute"]
        self.assertAlmostEqual(tiers["FREE"], float(cost.TIER_PRICES_USD_PER_MINUTE["FREE"]))
        self.assertAlmostEqual(tiers["GOLD"], float(cost.TIER_PRICES_USD_PER_MINUTE["GOLD"]))
        self.assertEqual(self.contract["limits"]["freePlanVideoDurationMinutes"], 5)

    def test_contract_lists_unverified_behaviour(self):
        self.assertTrue(any("short links" in entry for entry in self.contract["unverified"]))


class FixtureCoverageTests(unittest.TestCase):
    EXPECTED = {
        "transcript-success.synthetic.json": "success",
        "transcript-actor-error.synthetic.json": "actor_error",
        "dataset-empty.synthetic.json": "empty",
        "no-transcript-null.synthetic.json": "no_transcript",
        "no-transcript-missing.synthetic.json": "no_transcript",
        "unknown-text-type.synthetic.json": "unknown",
        "extra-fields.synthetic.json": "success",
        "segments-invalid.synthetic.json": "success",
    }

    def test_every_fixture_is_synthetic_and_classifies_as_expected(self):
        for name, expected in self.EXPECTED.items():
            with self.subTest(fixture=name):
                data = load_fixture(name)
                self.assertTrue(str(data["_fixture"]).startswith("SYNTHETIC"))
                self.assertEqual(classify_items(data["items"])[0], expected)

    def test_all_fixtures_are_covered_by_this_test(self):
        on_disk = {path.name for path in FIXTURE_DIR.glob("*.synthetic.json")}
        self.assertEqual(on_disk, set(self.EXPECTED))


if __name__ == "__main__":
    unittest.main()
