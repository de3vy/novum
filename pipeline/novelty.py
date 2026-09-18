"""Check verified NOVUM candidates against the OEIS search API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PREFIX_LENGTH = 10


def lookup_oeis(terms: list[int], timeout: int = 10) -> dict[str, Any]:
    """Return reproducible lookup metadata without treating failures as no match."""
    query_terms = terms[:PREFIX_LENGTH]
    query = ",".join(str(term) for term in query_terms)
    url = "https://oeis.org/search?" + urllib.parse.urlencode(
        {"q": query, "fmt": "json"}
    )
    result: dict[str, Any] = {
        "source": "OEIS",
        "query_terms": query_terms,
        "query": query,
        "lookup_status": "LOOKUP_FAILED",
        "match_found": False,
        "oeis_ids": [],
    }
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        result["error"] = str(exc)
        return result
    if not isinstance(payload, dict):
        result["error"] = "OEIS response was not a JSON object"
        return result
    matches = payload.get("results", payload.get("matches", []))
    if not isinstance(matches, list):
        result["error"] = "OEIS response did not contain a result list"
        return result
    ids: list[str] = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        identifier = match.get("number") or match.get("id")
        if identifier is not None:
            ids.append(str(identifier))
    result["oeis_ids"] = ids
    result["match_found"] = bool(ids)
    result["lookup_status"] = "DUPLICATE" if ids else "NO_MATCH_FOUND"
    return result


def enrich_results(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
            raise ValueError("results must contain a candidates array")
        for candidate in payload["candidates"]:
            if not isinstance(candidate, dict) or not isinstance(candidate.get("terms"), list):
                raise ValueError("each result candidate must contain terms")
            lookup = lookup_oeis(candidate["terms"])
            candidate["novelty_check"] = lookup
            if lookup["lookup_status"] == "LOOKUP_FAILED":
                candidate["verdict"] = "LOOKUP_FAILED"
            elif lookup["lookup_status"] == "DUPLICATE":
                candidate["verdict"] = "DUPLICATE"
            else:
                candidate["verdict"] = "NOVEL-UNPROVEN"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"novelty check failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    return enrich_results(args.results)


if __name__ == "__main__":
    raise SystemExit(main())
