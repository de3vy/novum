"""Generate determinant-based integer-sequence candidates for NOVUM."""

from __future__ import annotations

from math import comb


def _determinant(matrix: list[list[int]]) -> int:
    """Compute an exact determinant by fraction-free elimination."""
    n = len(matrix)
    if n == 0:
        return 1
    a = [row[:] for row in matrix]
    sign = 1
    previous = 1
    for pivot in range(n - 1):
        pivot_row = next((r for r in range(pivot, n) if a[r][pivot]), None)
        if pivot_row is None:
            return 0
        if pivot_row != pivot:
            a[pivot], a[pivot_row] = a[pivot_row], a[pivot]
            sign = -sign
        pivot_value = a[pivot][pivot]
        for row in range(pivot + 1, n):
            for col in range(pivot + 1, n):
                a[row][col] = (
                    a[row][col] * pivot_value - a[row][pivot] * a[pivot][col]
                ) // previous
        previous = pivot_value
        for row in range(pivot + 1, n):
            a[row][pivot] = 0
    return sign * a[-1][-1]


def generate_candidates(limit: int = 6) -> list[list[int]]:
    """Return determinants of shifted Pascal-plus-identity matrices.

    Candidate ``offset`` uses the n-by-n matrix
    A[i,j] = C(i+j+offset, i) + 1 for zero-based i,j.
    """
    candidates: list[list[int]] = []
    for offset in range(1, limit + 1):
        terms: list[int] = []
        for size in range(1, 13):
            matrix = [
                [comb(i + j + offset, i) + 1 for j in range(size)]
                for i in range(size)
            ]
            terms.append(_determinant(matrix))
        candidates.append(terms)
    return candidates


if __name__ == "__main__":
    for sequence in generate_candidates():
        print(sequence)
