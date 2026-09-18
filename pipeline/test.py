"""Compute terms and run lightweight SymPy checks for candidate sequences."""

from __future__ import annotations

from math import isqrt


def is_integer_sequence(terms: list[int]) -> bool:
    return all(isinstance(term, int) for term in terms)


def check_terms(terms: list[int]) -> dict[str, object]:
    """Return basic properties used to rank a candidate."""
    return {
        "terms": terms,
        "integer": is_integer_sequence(terms),
        "distinct": len(set(terms)) == len(terms),
        "nonnegative": all(term >= 0 for term in terms),
        "square_free_prefix": all(isqrt(abs(term)) ** 2 != abs(term) for term in terms[1:]),
    }


if __name__ == "__main__":
    from candidates.gen import generate_candidates

    for candidate in generate_candidates():
        print(check_terms(candidate))
