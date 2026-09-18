"""Look up candidate sequences in the OEIS API."""

from __future__ import annotations

import json
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
    return payload if isinstance(payload, list) else []


if __name__ == "__main__":
    print(lookup_oeis([1, 1, 2, 3, 5]))
