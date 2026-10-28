#!/usr/bin/env python3
"""Read-only inspection of one existing Apify Run. Never creates, retries, or mutates a Run.

Example:
    export APIFY_TOKEN='...'
    python scripts/check_apify_run.py RUN_ID
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/python"))
from reliable_actor import ApiError, RestTransport, classify_items, normalize_segments, sanitize  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an existing Run and its Dataset (read-only).")
    parser.add_argument("run_id")
    parser.add_argument("--dataset-limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("Set APIFY_TOKEN in your environment; no request was sent.", file=sys.stderr)
        return 2

    transport = RestTransport(token.strip())
    try:
        run = transport.request("GET", f"/actor-runs/{args.run_id}").get("data", {})
        dataset_id = run.get("defaultDatasetId")
        items = []
        if dataset_id:
            items = transport.request(
                "GET", f"/datasets/{dataset_id}/items?limit={args.dataset_limit}&offset=0"
            )
    except ApiError as exc:
        print(f"Read failed: {exc}", file=sys.stderr)
        return 8

    status, message = classify_items(items)
    first_item = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
    payload = sanitize(
        {
            "runId": run.get("id"),
            "status": run.get("status"),
            "buildNumber": run.get("buildNumber"),
            "buildId": run.get("buildId"),
            "datasetId": dataset_id,
            "itemCount": len(items) if isinstance(items, list) else None,
            "classification": status,
            "classificationDetail": message,
            "textPreview": next(
                (
                    item.get("text")[:200]
                    for item in items
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                ),
                None,
            ) if isinstance(items, list) else None,
            "segments": normalize_segments(first_item.get("segments")),
        }
    )
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for key, value in payload.items():
            if key == "segments":
                print(f"segments: {len(value)}")
            elif key == "textPreview":
                print(f"textPreview: {value!r}")
            else:
                print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
