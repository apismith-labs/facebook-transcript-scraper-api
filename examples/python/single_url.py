#!/usr/bin/env python3
"""Run one public Facebook video URL through the Actor and print its transcript.

This CLI may create one billable Actor Run. It loads ``.env`` from the current directory when
present; only ``APIFY_*`` keys are read and existing environment variables win.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__:
    from .client import (
        APPROVED_BUILD_NUMBER,
        DEFAULT_ACTOR_ID,
        ConfigurationError,
        CreationUnknownError,
        ProtocolError,
        TranscriptTransportError,
        get_transcript,
    )
    from .reliable_actor import EXIT_CODES, RunJournal, load_resume_record, sanitize, write_private
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from client import (
        APPROVED_BUILD_NUMBER,
        DEFAULT_ACTOR_ID,
        ConfigurationError,
        CreationUnknownError,
        ProtocolError,
        TranscriptTransportError,
        get_transcript,
    )
    from reliable_actor import EXIT_CODES, RunJournal, load_resume_record, sanitize, write_private

REPO_ROOT = Path(__file__).resolve().parents[2]
JOURNAL_PATH = REPO_ROOT / "sample-output" / "generated" / "python-run-journal.jsonl"


def load_env_file(path: Path) -> None:
    """Tiny ``.env`` reader: KEY=VALUE lines, comments, no interpolation. Never overrides env."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key.startswith("APIFY_") and key not in os.environ:
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one public Facebook video URL through the Facebook Transcript Actor.",
        epilog=(
            "Example: python examples/python/single_url.py "
            "'https://www.facebook.com/watch/?v=1234567890'"
        ),
    )
    parser.add_argument("url", help="Public Facebook video URL")
    parser.add_argument("--resume", metavar="RUN_ID", help="GET-only resume of an existing Run; never creates one")
    parser.add_argument("--json", action="store_true", help="Print a sanitized JSON result instead of text")
    parser.add_argument("--output", metavar="PATH", help="Also write the JSON result to PATH (mode 0600)")
    parser.add_argument("--dataset-limit", type=int, default=100, help="Maximum Dataset items to read (default 100)")
    parser.add_argument("--timeout", type=float, default=900, help="Overall deadline in seconds (default 900)")
    parser.add_argument("--build", default=APPROVED_BUILD_NUMBER, help=f"Actor Build (default {APPROVED_BUILD_NUMBER})")
    parser.add_argument("--actor-id", help="Override the Actor ID")
    parser.add_argument("--max-total-charge-usd", help="Per-Run charge cap in USD")
    parser.add_argument("--require-charge-cap", action="store_true", help="Fail before creating a Run when no cap is set")
    parser.add_argument("--no-journal", action="store_true", help="Do not append to the local run journal")
    return parser


def _result_dict(result) -> dict:
    return sanitize(
        {
            "status": result.status,
            "text": result.text,
            "segments": result.segments,
            "items": result.items,
            "runId": result.run_id,
            "datasetId": result.dataset_id,
            "sourceUrl": result.source_url,
            "canonicalUrl": result.canonical_url,
            "urlForm": result.url_form,
            "title": result.title,
            "duration": result.duration,
            "nickname": result.nickname,
            "datasetComplete": result.dataset_complete,
            "error": result.error,
        }
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(Path.cwd() / ".env")

    journal = None if args.no_journal else RunJournal(JOURNAL_PATH)
    if args.resume and journal is not None and journal.path.exists():
        try:
            record = load_resume_record(
                journal, args.resume, args.actor_id or os.getenv("APIFY_ACTOR_ID", DEFAULT_ACTOR_ID)
            )
        except ValueError as exc:
            print(f"Resume refused: {exc}", file=sys.stderr)
            return EXIT_CODES["transport_error"]
        if record.get("sourceUrl") and record["sourceUrl"] != args.url:
            print(
                "Resume refused: the journal record belongs to a different source URL",
                file=sys.stderr,
            )
            return EXIT_CODES["transport_error"]

    try:
        result = get_transcript(
            args.url,
            build=args.build,
            timeout=args.timeout,
            max_total_charge_usd=args.max_total_charge_usd,
            require_charge_cap=args.require_charge_cap,
            dataset_limit=args.dataset_limit,
            run_id=args.resume,
            actor_id=args.actor_id,
            journal=journal,
        )
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except CreationUnknownError as exc:
        print(f"Creation outcome unknown: {exc}", file=sys.stderr)
        return EXIT_CODES["creation_unknown"]
    except ProtocolError as exc:
        suffix = f" (Run {exc.run_id}, Dataset {exc.dataset_id})" if exc.run_id else ""
        print(f"Protocol error: {exc}{suffix}", file=sys.stderr)
        return 3
    except TranscriptTransportError as exc:
        suffix = f" (Run {exc.run_id})" if exc.run_id else ""
        print(f"Transport error: {exc}{suffix}", file=sys.stderr)
        return EXIT_CODES["transport_error"]

    payload = _result_dict(result)
    if args.output:
        write_private(Path(args.output), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Run ID: {result.run_id or 'unknown'}")
        print(f"Status: {result.status}")
        if result.title:
            print(f"Video: {result.title}")
        if result.duration is not None:
            print(f"Duration: {result.duration:g}s")
        if result.nickname:
            print(f"Creator: {result.nickname}")
        print(f"Segments: {len(result.segments)}")
        if result.status == "success":
            print("Transcript:")
            print(result.text)
        elif result.error:
            print(f"Detail: {result.error}")
    return EXIT_CODES.get(result.status, 1)


if __name__ == "__main__":
    raise SystemExit(main())
