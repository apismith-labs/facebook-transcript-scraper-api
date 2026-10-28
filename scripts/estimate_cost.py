#!/usr/bin/env python3
"""Estimate the USD cost of Facebook Transcript Runs without calling Apify.

Example:
    python scripts/estimate_cost.py --videos 3 --minutes 8 --tier GOLD
    python scripts/estimate_cost.py --videos 1 --seconds 43.5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/python"))
from cost import PRICING_CAPTURED_AT, TIER_PRICES_USD_PER_MINUTE, estimate_cost_usd, format_estimate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--videos", type=int, default=1, help="Number of videos / Runs (default 1)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--minutes", type=float, help="Average duration in minutes")
    group.add_argument("--seconds", type=float, help="Average duration in seconds")
    parser.add_argument("--tier", default="FREE", help="Apify plan tier (default FREE)")
    parser.add_argument("--json", action="store_true", help="Print the estimate as JSON")
    args = parser.parse_args(argv)

    duration = args.seconds if args.seconds is not None else (args.minutes * 60 if args.minutes is not None else None)
    try:
        estimate = estimate_cost_usd(videos=args.videos, duration_seconds=duration, tier=args.tier)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    if args.json:
        print(json.dumps(estimate, indent=2))
        return 0

    print(format_estimate(estimate))
    print("")
    print(f"Dataset items      ${estimate['datasetItemUsd']:.4f}")
    print(f"Transcription      ${estimate['speechToTextUsd']:.4f} ({estimate['billedMinutesPerVideo']} min/video)")
    print(f"Total              ${estimate['totalUsd']:.4f}")
    print("")
    print(f"Tier prices (USD/min): {', '.join(f'{k}=${v}' for k, v in TIER_PRICES_USD_PER_MINUTE.items())}")
    print(f"Pricing captured {PRICING_CAPTURED_AT}. Estimate only; billing depends on actual events.")
    if estimate["lowerBound"]:
        print("Duration unknown: using the one-minute billing floor, so this is a lower bound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
