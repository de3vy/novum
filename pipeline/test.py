"""Compute terms and run lightweight SymPy checks for candidate sequences."""

from __future__ import annotations

import argparse
import json
from math import isqrt
from pathlib import Path
from datetime import date


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    results = {
        "date": date.today().isoformat(),
        "candidates": [check_terms(candidate) for candidate in candidates],
    }
    json.dump(results, fp=__import__("sys").stdout, indent=2)
    print()
