"""Generate deterministic integer-sequence candidates for NOVUM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_CANDIDATE_COUNT = 3
DEFAULT_TERM_COUNT = 200


def generate_sequence(offset: int, term_count: int) -> list[int]:
    """Generate a_n = (n + offset) a_(n-1) - offset a_(n-2), a_0=a_1=1."""
    if offset < 1 or term_count < 2:
        raise ValueError("offset must be positive and term_count must be at least 2")
    terms = [1, 1]
    for index in range(2, term_count):
        terms.append((index + offset) * terms[-1] - offset * terms[-2])
    return terms


def generate_candidates(
    limit: int = DEFAULT_CANDIDATE_COUNT,
    term_count: int = DEFAULT_TERM_COUNT,
) -> list[dict[str, Any]]:
    """Return a small deterministic set of fully materialized candidates."""
    if limit < 0:
        raise ValueError("limit must not be negative")
    candidates: list[dict[str, Any]] = []
    for offset in range(1, limit + 1):
        terms = generate_sequence(offset, term_count)
        candidates.append(
            {
                "id": f"poly-recurrence-offset-{offset}",
                "definition": (
                    "a_0 = 1, a_1 = 1; "
                    "a_n = (n + offset) * a_(n-1) - offset * a_(n-2) for n >= 2"
                ),
                "parameters": {"offset": offset},
                "indexing": "zero-based; terms[0] is a_0",
                "first_10_terms": terms[:10],
                "term_count": len(terms),
                "terms": terms,
            }
        )
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--term-count", type=int, default=DEFAULT_TERM_COUNT)
    args = parser.parse_args()
    candidates = generate_candidates(args.limit, args.term_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
