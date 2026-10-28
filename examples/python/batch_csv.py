#!/usr/bin/env python3
"""Process a CSV of Facebook video URLs: one independent Actor Run per non-empty row.

Without ``--execute`` this script only validates the file and prints a plan; it does not read the
token and does not create any Run. Result files are written with owner-only permissions and never
overwrite an earlier batch.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .client import (
        APPROVED_BUILD_NUMBER,
        ConfigurationError,
        CreationUnknownError,
        ProtocolError,
        TranscriptTransportError,
        get_transcript,
        validate_video_url,
    )
    from .cost import DATASET_ITEM_USD, TIER_PRICES_USD_PER_MINUTE, billed_minutes
    from .reliable_actor import RunJournal, sanitize, summarize, write_private
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from client import (
        APPROVED_BUILD_NUMBER,
        ConfigurationError,
        CreationUnknownError,
        ProtocolError,
        TranscriptTransportError,
        get_transcript,
        validate_video_url,
    )
    from cost import DATASET_ITEM_USD, TIER_PRICES_USD_PER_MINUTE, billed_minutes
    from reliable_actor import RunJournal, sanitize, summarize, write_private

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CsvRow:
    row_id: str
    url: str
    canonical_url: str
    url_form: str
    duration_seconds: float | None


def parse_rows(path: Path) -> list[CsvRow]:
    """Validate every non-empty data row before any Run is created.

    The header must contain ``videoUrl`` or ``url`` (case-insensitive). ``durationSeconds`` is
    optional and only used for cost estimates. The CSV line number becomes ``rowId`` so duplicate
    URLs stay traceable to their input line.
    """
    if not path.is_file():
        raise ConfigurationError(f"CSV file not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {name.strip().lower(): name for name in (reader.fieldnames or [])}
        url_key = fields.get("videourl") or fields.get("url")
        if url_key is None:
            raise ConfigurationError("CSV must have a 'videoUrl' or 'url' column")
        duration_key = fields.get("durationseconds")
        rows: list[CsvRow] = []
        for raw in reader:
            row_id = str(reader.line_num)
            url = (raw.get(url_key) or "").strip()
            if not url:
                continue
            try:
                canonical, form = validate_video_url(url)
            except ConfigurationError as exc:
                raise ConfigurationError(f"CSV line {row_id}: {exc}") from None
            duration: float | None = None
            if duration_key:
                value = (raw.get(duration_key) or "").strip()
                if value:
                    try:
                        duration = float(value)
                    except ValueError:
                        raise ConfigurationError(
                            f"CSV line {row_id}: durationSeconds must be a number"
                        ) from None
                    if duration < 0:
                        raise ConfigurationError(
                            f"CSV line {row_id}: durationSeconds must not be negative"
                        )
            rows.append(CsvRow(row_id, url, canonical, form, duration))
    if not rows:
        raise ConfigurationError("CSV contains no non-empty URL rows")
    return rows


def estimate_rows(rows: list[CsvRow], tier: str) -> dict:
    """Sum per-row estimates; rows without a duration use the one-minute billing floor."""
    selected = (tier or "FREE").strip().upper()
    if selected not in TIER_PRICES_USD_PER_MINUTE:
        raise ConfigurationError("tier must be one of " + ", ".join(TIER_PRICES_USD_PER_MINUTE))
    minutes = sum(billed_minutes(row.duration_seconds or 0) for row in rows)
    item_cost = DATASET_ITEM_USD * len(rows)
    speech_cost = TIER_PRICES_USD_PER_MINUTE[selected] * minutes
    return {
        "tier": selected,
        "videos": len(rows),
        "billedMinutes": minutes,
        "datasetItemUsd": float(item_cost),
        "speechToTextUsd": float(speech_cost),
        "totalUsd": float(item_cost + speech_cost),
        "lowerBound": any(row.duration_seconds is None for row in rows),
    }


def run_batch(
    rows: list[CsvRow],
    *,
    token: str,
    actor_id: str | None = None,
    build: str | None = APPROVED_BUILD_NUMBER,
    max_concurrency: int = 3,
    timeout: float = 900,
    max_total_charge_usd: str | float | None = None,
    require_charge_cap: bool = False,
    dataset_limit: int = 100,
    journal=None,
    transport_factory=None,
) -> list[dict]:
    """Run every row concurrently and return per-row result records."""
    if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or max_concurrency < 1:
        raise ConfigurationError("max_concurrency must be a positive integer")

    def one(row: CsvRow) -> dict:
        base = {
            "rowId": row.row_id,
            "sourceUrl": row.url,
            "canonicalUrl": row.canonical_url,
            "urlForm": row.url_form,
        }
        try:
            result = get_transcript(
                row.url,
                token=token,
                actor_id=actor_id,
                build=build,
                timeout=timeout,
                max_total_charge_usd=max_total_charge_usd,
                require_charge_cap=require_charge_cap,
                dataset_limit=dataset_limit,
                row_id=row.row_id,
                transport=transport_factory() if transport_factory else None,
                journal=journal,
            )
        except CreationUnknownError as exc:
            return {**base, "status": "creation_unknown", "error": str(exc)}
        except (ConfigurationError, ProtocolError, TranscriptTransportError) as exc:
            status = "transport_error" if isinstance(exc, TranscriptTransportError) else "unknown"
            row = {**base, "status": status, "error": str(exc)}
            if getattr(exc, "run_id", None):
                row["runId"] = exc.run_id
            if getattr(exc, "dataset_id", None):
                row["datasetId"] = exc.dataset_id
            return row
        return {
            **base,
            "status": result.status,
            "runId": result.run_id,
            "datasetId": result.dataset_id,
            "title": result.title,
            "duration": result.duration,
            "nickname": result.nickname,
            "text": result.text,
            "segments": result.segments,
            "items": result.items,
            "datasetComplete": result.dataset_complete,
            "error": result.error,
        }

    # Preserve input order in the returned list via executor.map.
    with ThreadPoolExecutor(max_workers=min(max_concurrency, len(rows))) as pool:
        return list(pool.map(one, rows))


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise ConfigurationError("could not allocate a unique result filename")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one Facebook Transcript Actor Run per CSV row. Plan-only unless --execute.",
    )
    parser.add_argument("csv", help="CSV file with a videoUrl (or url) column")
    parser.add_argument("--execute", action="store_true", help="Actually create Runs; without it nothing is billed")
    parser.add_argument("--limit", type=int, help="Process only the first N rows")
    parser.add_argument("--max-concurrency", type=int, default=3, help="Concurrent Runs (default 3)")
    parser.add_argument("--output", metavar="PATH", help="Result JSON path (default: beside the CSV)")
    parser.add_argument("--tier", default="FREE", help="Apify plan tier for the cost estimate (default FREE)")
    parser.add_argument("--timeout", type=float, default=900, help="Per-Run deadline in seconds")
    parser.add_argument("--build", default=APPROVED_BUILD_NUMBER, help=f"Actor Build (default {APPROVED_BUILD_NUMBER})")
    parser.add_argument("--actor-id", help="Override the Actor ID")
    parser.add_argument("--dataset-limit", type=int, default=100, help="Maximum Dataset items per Run")
    parser.add_argument("--max-total-charge-usd", help="Per-Run charge cap in USD")
    parser.add_argument("--require-charge-cap", action="store_true", help="Fail before any Run when no cap is set")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    csv_path = Path(args.csv).expanduser().resolve()
    try:
        rows = parse_rows(csv_path)
        if args.limit is not None:
            if args.limit < 1:
                raise ConfigurationError("--limit must be a positive integer")
            rows = rows[: args.limit]
        estimate = estimate_rows(rows, args.tier)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    estimate_line = (
        f"{estimate['videos']} video(s), {estimate['billedMinutes']} billed minute(s), "
        f"{estimate['tier']} tier -> ${estimate['totalUsd']:.4f} estimated "
        f"(dataset ${estimate['datasetItemUsd']:.4f} + speech ${estimate['speechToTextUsd']:.4f})"
    )
    print(f"CSV: {csv_path}")
    print(f"Rows: {len(rows)}")
    print(f"Estimate: {estimate_line}{' [lower bound: some durations unknown]' if estimate['lowerBound'] else ''}")

    if not args.execute:
        print("Plan only. No Run was created and no token was read.")
        print("Re-run with --execute to process these rows.")
        return 0

    token = os.getenv("APIFY_TOKEN")
    if not token or not token.strip():
        print("Configuration error: APIFY_TOKEN is required when --execute is used", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_name = f"facebook-batch-results-{stamp}.json"
    result_path = _unique_path(
        Path(args.output).expanduser().resolve()
        if args.output
        else csv_path.parent / default_name
    )
    journal = RunJournal(result_path.parent / "python-run-journal.jsonl", lock=threading.Lock())

    try:
        results = run_batch(
            rows,
            token=token,
            actor_id=args.actor_id,
            build=args.build,
            max_concurrency=args.max_concurrency,
            timeout=args.timeout,
            max_total_charge_usd=args.max_total_charge_usd,
            require_charge_cap=args.require_charge_cap,
            dataset_limit=args.dataset_limit,
            journal=journal,
        )
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    counts = summarize(results)
    payload = sanitize(
        {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "actorId": args.actor_id or os.getenv("APIFY_ACTOR_ID", "apple_yang/facebook-transcript-scraper-api"),
            "build": args.build,
            "source": str(csv_path),
            "estimate": estimate,
            "counts": counts,
            "results": results,
        }
    )
    write_private(result_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"Result: {result_path}")
    print(
        "Counts: "
        + ", ".join(f"{name}={value}" for name, value in counts.items())
    )
    failed = [row["rowId"] for row in results if row["status"] != "success"]
    if failed:
        print(f"Non-success rows: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
