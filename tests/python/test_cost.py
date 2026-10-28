import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
import cost  # noqa: E402


class BilledMinutesTests(unittest.TestCase):
    def test_floor_is_one_minute(self):
        for seconds in (0, 0.1, 59.9, 60):
            self.assertEqual(cost.billed_minutes(seconds), 1)

    def test_partial_minutes_round_up(self):
        self.assertEqual(cost.billed_minutes(61), 2)
        self.assertEqual(cost.billed_minutes(600), 10)
        self.assertEqual(cost.billed_minutes(601), 11)

    def test_invalid_durations(self):
        for bad in (-1, float("nan"), float("inf"), True, "60"):
            with self.assertRaises(ValueError):
                cost.billed_minutes(bad)


class EstimateTests(unittest.TestCase):
    def test_ten_minute_video_on_free_tier(self):
        estimate = cost.estimate_cost_usd(videos=1, duration_seconds=600, tier="FREE")
        self.assertEqual(estimate["billedMinutesPerVideo"], 10)
        self.assertAlmostEqual(estimate["datasetItemUsd"], 0.001)
        self.assertAlmostEqual(estimate["speechToTextUsd"], 0.045)
        self.assertAlmostEqual(estimate["totalUsd"], 0.046)
        self.assertFalse(estimate["lowerBound"])

    def test_paid_tier_is_cheaper(self):
        free = cost.estimate_cost_usd(videos=1, duration_seconds=600, tier="FREE")
        gold = cost.estimate_cost_usd(videos=1, duration_seconds=600, tier="GOLD")
        self.assertAlmostEqual(gold["totalUsd"], 0.021)
        self.assertLess(gold["totalUsd"], free["totalUsd"])

    def test_unknown_duration_is_a_lower_bound(self):
        estimate = cost.estimate_cost_usd(videos=3, duration_seconds=None, tier="FREE")
        self.assertTrue(estimate["lowerBound"])
        self.assertEqual(estimate["billedMinutesPerVideo"], 1)
        self.assertAlmostEqual(estimate["totalUsd"], 0.003 + 0.0135)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            cost.estimate_cost_usd(videos=0)
        with self.assertRaises(ValueError):
            cost.estimate_cost_usd(tier="PLATINUM_PLUS")

    def test_format_is_human_readable(self):
        line = cost.format_estimate(cost.estimate_cost_usd(videos=2, duration_seconds=30, tier="SILVER"))
        self.assertIn("2 video(s)", line)
        self.assertIn("$", line)


if __name__ == "__main__":
    unittest.main()
