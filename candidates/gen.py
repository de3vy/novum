"""Generate binomial-transform Hankel determinant candidates for NOVUM."""

from __future__ import annotations

import argparse
import json
import sys
from math import comb, factorial
from pathlib import Path
from typing import Any

DEFAULT_SHIFTS = (0, 1, 2, 3, 4)
DEFAULT_TERM_COUNT = 200

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


def base_sequence(n: int, shift: int) -> int:
    """Return the inverse binomial transform of (n + shift)! exactly."""
    if n < 0 or shift < 0:
        raise ValueError("n and shift must be nonnegative")
    return sum(
        (-1) ** (n - k) * comb(n, k) * factorial(k + shift)
        for k in range(n + 1)
    )


def binomial_transform(n: int, shift: int) -> int:
    """Return sum_k binomial(n,k) * base_sequence(k, shift)."""
    return sum(comb(n, k) * base_sequence(k, shift) for k in range(n + 1))


def hankel_determinant(shift: int, size: int) -> int:
    """Return det((B(i+j))_(0 <= i,j < size)) for this family.

    The binomial transform is B(n) = (n + shift)!. The factorial Hankel
    determinant has the exact product form prod(i! * (shift+i)!), which avoids
    an expensive 200-by-200 symbolic determinant.
    """
    if shift < 0 or size < 0:
        raise ValueError("shift and size must be nonnegative")
    result = 1
    for index in range(size):
        result *= factorial(index) * factorial(shift + index)
    return result


def bareiss_determinant(matrix: list[list[int]]) -> int:
    """Compute a small integer determinant by fraction-free elimination."""
    if not matrix:
        return 1
    values = [row[:] for row in matrix]
    size = len(values)
    sign = 1
    previous = 1
    for pivot in range(size - 1):
        pivot_row = next((row for row in range(pivot, size) if values[row][pivot]), None)
        if pivot_row is None:
            return 0
        if pivot_row != pivot:
            values[pivot], values[pivot_row] = values[pivot_row], values[pivot]
            sign *= -1
        pivot_value = values[pivot][pivot]
        for row in range(pivot + 1, size):
            for column in range(pivot + 1, size):
                values[row][column] = (
                    values[row][column] * pivot_value
                    - values[row][pivot] * values[pivot][column]
                ) // previous
        previous = pivot_value
    return sign * values[-1][-1]


def generate_terms(shift: int, term_count: int) -> list[int]:
    if shift < 0 or term_count < 1:
        raise ValueError("shift must be nonnegative and term_count must be positive")
    terms: list[int] = []
    determinant = 1
    for size in range(1, term_count + 1):
        index = size - 1
        determinant *= factorial(index) * factorial(shift + index)
        terms.append(determinant)
    return terms


def reproduce_candidate(candidate: dict[str, Any], term_count: int | None = None) -> list[int]:
    parameters = candidate["parameters"]
    if parameters.get("family") != "binomial-factorial-hankel":
        raise ValueError("unsupported candidate family")
    count = candidate["term_count"] if term_count is None else term_count
    return generate_terms(parameters["shift"], count)


def generate_candidates(
    shifts: tuple[int, ...] = DEFAULT_SHIFTS,
    term_count: int = DEFAULT_TERM_COUNT,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for shift in shifts:
        terms = generate_terms(shift, term_count)
        candidates.append(
            {
                "id": f"binomial-factorial-hankel-shift-{shift}",
                "definition": (
                    "B(n) = sum(k=0..n) binomial(n,k)b(k); "
                    "H_m = det(B(i+j)) for i,j=0..m-1"
                ),
                "base_sequence": (
                    "b(n) = sum(k=0..n) (-1)^(n-k) binomial(n,k)(k+shift)!"
                ),
                "parameters": {
                    "family": "binomial-factorial-hankel",
                    "shift": shift,
                },
                "indexing": "one-based determinant size; terms[m-1] is H_m",
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
