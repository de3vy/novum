"""Look up candidate sequences in the OEIS API."""

from __future__ import annotations

import json
import argparse
from pathlib import Path
import urllib.parse
import urllib.request


def lookup_oeis(terms: list[int], timeout: int = 10) -> list[dict[str, object]]:
    """Return matching OEIS entries, or an empty list when lookup is unavailable."""
    query = ",".join(str(term) for term in terms[:10])
    url = "https://oeis.org/search?" + urllib.parse.urlencode(
        {"q": f"{query}", "fmt": "json"}
    )
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
    except (OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    matches = payload.get("matches", [])
    return matches if isinstance(matches, list) else []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.results.read_text(encoding="utf-8"))
    for candidate in payload.get("candidates", []):
        matches = lookup_oeis(candidate["terms"])
        candidate["oeis_matches"] = [
            {key: match[key] for key in ("number", "name") if key in match}
            for match in matches
            if isinstance(match, dict)
        ]
        candidate["novelty"] = "duplicate" if matches else "unmatched"
    args.results.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
