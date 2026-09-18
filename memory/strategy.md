# NOVUM Strategy (v1)
Domain: integer sequences.
Current approach: linear recurrences with polynomial coefficients.
Explore next: sums of binomial coefficients, determinant sequences.
Avoid: anything already dense in OEIS (Fibonacci variants, etc.)
Success rate so far: 0/0 days.

## 2026-09-18 update
The determinant-family generator was pushed and the GitHub explore job completed successfully, but the existing pipeline.test only prints checks and never writes results/results.json, leaving candidates empty. Tomorrow repair the result-writer and require at least 200 exact terms per candidate before judging; avoid novelty claims until OEIS and arXiv checks are actually completed.
