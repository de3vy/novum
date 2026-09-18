"""Generate candidate integer sequences for NOVUM experiments."""

from __future__ import annotations


def generate_candidates(limit: int = 10) -> list[list[int]]:
    """Return initial candidates from polynomial-coefficient recurrences."""
    candidates: list[list[int]] = []
    for offset in range(1, limit + 1):
        terms = [1, 1]
        for index in range(2, 12):
            terms.append((index + offset) * terms[-1] - offset * terms[-2])
        candidates.append(terms)
    return candidates


if __name__ == "__main__":
    for sequence in generate_candidates():
        print(sequence)
