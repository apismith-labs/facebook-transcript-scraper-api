"""Dependency-free synthetic support. Never imports or invokes the example CLIs."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict:
    data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    assert str(data["_fixture"]).startswith("SYNTHETIC")
    return data


def fixture_items(name: str) -> list:
    return load_fixture(name)["items"]


class FakeTransport:
    """Records requests and returns queued responses/errors without network access."""

    def __init__(self, responses=()):
        self.responses = list(responses)
        self.requests = []

    def request(self, method: str, path: str, body=None, **kwargs):
        record = {
            "method": method.upper(),
            "path": path,
            "body": body,
            "query": kwargs.get("query"),
        }
        self.requests.append(record)
        if not self.responses:
            raise AssertionError("No synthetic transport response queued")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    @property
    def post_count(self) -> int:
        return sum(r["method"] == "POST" for r in self.requests)

    @property
    def get_count(self) -> int:
        return sum(r["method"] == "GET" for r in self.requests)

    @property
    def paths(self) -> list[str]:
        return [r["path"] for r in self.requests]
