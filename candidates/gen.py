"""Generate restricted-partition rank candidates for NOVUM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_GAPS = (1, 2, 3, 4, 5)
DEFAULT_TERM_COUNT = 200

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


def restricted_partition_value(n: int, gap: int) -> int:
    """Return a_g(n) using exact dynamic programming, without partition enumeration."""
    if n < 0 or gap < 1:
        raise ValueError("n must be nonnegative and gap must be positive")
    return generate_terms(gap, n + 1)[n]


def _generate_terms(gap: int, term_count: int) -> list[int]:
    # If lambda has k parts, subtract gap*(k-i) from lambda_i.  This
    # produces a partition mu with k positive parts and
    # n = |mu| + gap*k*(k-1)//2.
    max_sum = term_count - 1
    counts = [[0] * (max_sum + 1) for _ in range(max_sum + 1)]
    counts[0][0] = 1
    weighted = [0] * term_count
    weighted[0] = 1
    for largest in range(1, max_sum + 1):
        for parts in range(1, max_sum + 1):
            offset = gap * parts * (parts - 1) // 2
            for transformed_sum in range(largest, max_sum - offset + 1):
                delta = counts[parts - 1][transformed_sum - largest]
                if not delta:
                    continue
                total = transformed_sum + offset
                rank = largest + gap * (parts - 1) - parts
                weighted[total] += delta * (1 + rank * rank)
                counts[parts][transformed_sum] += delta
    return weighted


def generate_terms(gap: int, term_count: int) -> list[int]:
    if gap < 1 or term_count < 1:
        raise ValueError("gap must be positive and term_count must be positive")
    return _generate_terms(gap, term_count)


def brute_force_value(n: int, gap: int) -> int:
    """Reference implementation for small n only; explicitly enumerates partitions."""
    if n < 0 or gap < 1:
        raise ValueError("n must be nonnegative and gap must be positive")
    if n > 30:
        raise ValueError("brute-force reference is limited to n <= 30")
    if n == 0:
        return 1

    total = 0

    def visit(remaining: int, largest_allowed: int, parts: list[int]) -> None:
        nonlocal total
        if remaining == 0:
            rank = parts[0] - len(parts)
            total += 1 + rank * rank
            return
        for first in range(min(remaining, largest_allowed), 0, -1):
            next_allowed = first - gap
            if next_allowed < 1 and remaining != first:
                continue
            visit(remaining - first, next_allowed, parts + [first])

    visit(n, n, [])
    return total


def reproduce_candidate(candidate: dict[str, Any], term_count: int | None = None) -> list[int]:
    parameters = candidate["parameters"]
    if parameters.get("family") != "restricted-partition-rank":
        raise ValueError("unsupported candidate family")
    count = candidate["term_count"] if term_count is None else term_count
    return generate_terms(parameters["gap"], count)


def generate_candidates(
    gaps: tuple[int, ...] = DEFAULT_GAPS,
    term_count: int = DEFAULT_TERM_COUNT,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for gap in gaps:
        terms = generate_terms(gap, term_count)
        identifier = f"restricted-partition-rank-gap-{gap}"
        candidates.append(
            {
                "id": identifier,
                "candidate_id": identifier,
                "family": "restricted-partition-rank",
                "definition": (
                    "a_g(0)=1. For n>=1, sum over partitions "
                    "lambda=(lambda_1>=...>=lambda_k>0) of n with "
                    "lambda_i-lambda_(i+1)>=g of (1+(lambda_1-k)^2)."
                ),
                "parameters": {"family": "restricted-partition-rank", "gap": gap},
                "indexing": "zero-based n; terms[n] is a_g(n), for n=0..199",
                "first_10_terms": terms[:10],
                "term_count": len(terms),
                "terms": terms,
            }
        )
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--term-count", type=int, default=DEFAULT_TERM_COUNT)
    args = parser.parse_args()
    candidates = generate_candidates(term_count=args.term_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
