"""Check verified NOVUM candidates against the OEIS search API."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

PREFIX_LENGTH = 10
DEFAULT_RETRIES = 2
RETRYABLE_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
USER_AGENT = "NOVUM/1.0 (+https://github.com/de3vy/novum)"


def _content_type(response: Any) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    get_content_type = getattr(headers, "get_content_type", None)
    if callable(get_content_type):
        return str(get_content_type())
    value = headers.get("Content-Type") if hasattr(headers, "get") else None
    return str(value) if value is not None else None


def _error_content_type(error: urllib.error.HTTPError) -> str | None:
    headers = getattr(error, "headers", None)
    if headers is None:
        return None
    value = headers.get("Content-Type") if hasattr(headers, "get") else None
    return str(value) if value is not None else None


def lookup_oeis(
    terms: list[int],
    timeout: int = 10,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = 0.25,
) -> dict[str, Any]:
    """Search OEIS with bounded retries and explicit access diagnostics."""
    if retries < 0 or retry_delay < 0:
        raise ValueError("retries and retry_delay must be nonnegative")
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
        "url": url,
        "http_status": None,
        "response_content_type": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
    }
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result["http_status"] = getattr(response, "status", None)
                result["response_content_type"] = _content_type(response)
                payload = json.load(response)
            if isinstance(payload, list):
                matches = payload
            elif isinstance(payload, dict):
                matches = payload.get("results", payload.get("matches", []))
            else:
                result["error"] = "OEIS response did not contain a result list"
                return result
            if not isinstance(matches, list):
                result["error"] = "OEIS response did not contain a result list"
                return result
            ids: list[str] = []
            for match in matches:
                if not isinstance(match, dict):
                    continue
                identifier = match.get("number") or match.get("id")
                if identifier is not None:
                    identifier_text = str(identifier)
                    if identifier_text.isdigit():
                        identifier_text = f"A{int(identifier_text):06d}"
                    ids.append(identifier_text)
            result["oeis_ids"] = ids
            result["match_found"] = bool(ids)
            result["lookup_status"] = "MATCH_FOUND" if ids else "NO_MATCH_FOUND"
            return result
        except urllib.error.HTTPError as exc:
            result["http_status"] = exc.code
            result["response_content_type"] = _error_content_type(exc)
            result["error"] = str(exc)
            retryable = exc.code in RETRYABLE_HTTP_STATUSES
        except (OSError, ValueError, urllib.error.URLError) as exc:
            result["error"] = str(exc)
            retryable = True
        if not retryable or attempt == retries:
            return result
        result["retry_count"] = attempt + 1
        time.sleep(retry_delay * (2**attempt))
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
            elif lookup["lookup_status"] == "MATCH_FOUND":
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
