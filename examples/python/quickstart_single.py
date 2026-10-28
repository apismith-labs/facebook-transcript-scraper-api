#!/usr/bin/env python3
"""Quick start: one public Facebook video URL in, transcript text out.

Standard library only. Set APIFY_TOKEN in the environment first. This creates one billable Run.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__:
    from .client import ConfigurationError, CreationUnknownError, ProtocolError, TranscriptTransportError, get_transcript
    from .reliable_actor import EXIT_CODES
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from client import ConfigurationError, CreationUnknownError, ProtocolError, TranscriptTransportError, get_transcript
    from reliable_actor import EXIT_CODES


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print("Usage: python examples/python/quickstart_single.py '<public Facebook video URL>'")
        return 0 if len(argv) == 2 else 2
    try:
        result = get_transcript(argv[1])
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except CreationUnknownError as exc:
        print(f"Creation outcome unknown: {exc}", file=sys.stderr)
        return EXIT_CODES["creation_unknown"]
    except ProtocolError as exc:
        print(f"Protocol error: {exc}", file=sys.stderr)
        return 3
    except TranscriptTransportError as exc:
        print(f"Transport error: {exc}", file=sys.stderr)
        return EXIT_CODES["transport_error"]

    print(f"Run ID: {result.run_id}")
    print(f"Status: {result.status}")
    if result.status == "success":
        print("Transcript:")
        print(result.text)
    else:
        print(result.error or "No transcript text")
    return EXIT_CODES.get(result.status, 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
