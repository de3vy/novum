import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

import candidates.gen as generator
import pipeline.novelty as novelty
from pipeline.test import verify_file


def test_generator_returns_200_integer_terms():
    candidates = generator.generate_candidates()
    assert candidates
    assert all(candidate["term_count"] >= 200 for candidate in candidates)
    assert all(type(term) is int for candidate in candidates for term in candidate["terms"])


def test_binomial_transform_matches_factorial():
    assert [generator.binomial_transform(n, 0) for n in range(6)] == [1, 1, 2, 6, 24, 120]


def test_hankel_determinant_matches_manual_matrix():
    matrix = [[generator.binomial_transform(i + j, 0) for j in range(3)] for i in range(3)]
    assert generator.bareiss_determinant(matrix) == generator.hankel_determinant(0, 3)
    assert generator.hankel_determinant(1, 2) == 2


def test_hankel_candidates_are_reproducible():
    candidates = generator.generate_candidates(shifts=(0, 2), term_count=8)
    assert candidates == generator.generate_candidates(shifts=(0, 2), term_count=8)
    assert all(generator.reproduce_candidate(candidate) == candidate["terms"] for candidate in candidates)


def test_gaussian_binomial_known_values():
    assert generator.gaussian_binomial(4, 2, 2) == 35
    assert generator.gaussian_binomial(5, 2, 1) == 10
    assert generator.q_binomial_sum(0, 2) == 1
    assert [generator.q_binomial_sum(n, 2) for n in range(5)] == [1, 2, 5, 16, 67]


def test_q_binomial_candidates_are_reproducible_and_have_200_terms():
    candidates = generator.generate_q_candidates(q_values=(2, 3), term_count=200)
    assert candidates == generator.generate_q_candidates(q_values=(2, 3), term_count=200)
    assert all(candidate["term_count"] >= 200 for candidate in candidates)
    assert all(type(term) is int for candidate in candidates for term in candidate["terms"])
    assert all(generator.reproduce_candidate(candidate) == candidate["terms"] for candidate in candidates)


def test_results_json_is_valid(tmp_path):
    candidate_path = tmp_path / "candidates.json"
    results_path = tmp_path / "results.json"
    candidate_path.write_text(json.dumps(generator.generate_candidates()), encoding="utf-8")

    assert verify_file(candidate_path, results_path) == 0
    result = json.loads(results_path.read_text(encoding="utf-8"))
    assert result["candidate_count"] == len(result["candidates"])
    assert all(candidate["term_count"] >= 200 for candidate in result["candidates"])


def test_q_binomial_results_are_accepted_by_pipeline(tmp_path):
    candidate_path = tmp_path / "candidates.json"
    results_path = tmp_path / "results.json"
    candidate_path.write_text(
        json.dumps(generator.generate_q_candidates(q_values=(2,))),
        encoding="utf-8",
    )

    assert verify_file(candidate_path, results_path) == 0
    result = json.loads(results_path.read_text(encoding="utf-8"))
    assert result["pipeline_status"] == "OK"
    assert result["candidates"][0]["status"] == "VERIFIED-FINITE"


def test_malformed_candidate_is_detected_and_writes_pipeline_error(tmp_path):
    candidate_path = tmp_path / "bad.json"
    results_path = tmp_path / "results.json"
    candidate_path.write_text(json.dumps([{"id": "broken", "terms": [1, 2]}]), encoding="utf-8")

    assert verify_file(candidate_path, results_path) != 0
    result = json.loads(results_path.read_text(encoding="utf-8"))
    assert result["pipeline_status"] == "PIPELINE-ERROR"
    assert result["candidates"] == []


def test_cli_pipeline_failure_returns_nonzero(tmp_path):
    results_path = tmp_path / "results.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipeline" / "test.py"),
            str(tmp_path / "missing.json"),
            "--output",
            str(results_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert json.loads(results_path.read_text(encoding="utf-8"))["pipeline_status"] == "PIPELINE-ERROR"


def test_novelty_lookup_failure_is_distinct_from_no_match(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"results": []}'

    monkeypatch.setattr(novelty.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    monkeypatch.setattr(novelty.json, "load", lambda response: {"results": []})
    no_match = novelty.lookup_oeis([1, 2, 3])
    assert no_match["lookup_status"] == "NO_MATCH_FOUND"

    def fail(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(novelty.urllib.request, "urlopen", fail)
    failed = novelty.lookup_oeis([1, 2, 3])
    assert failed["lookup_status"] == "LOOKUP_FAILED"
    assert failed["lookup_status"] != no_match["lookup_status"]
