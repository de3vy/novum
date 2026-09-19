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


def test_generator_returns_five_200_integer_candidates():
    candidates = generator.generate_candidates()
    assert len(candidates) == 5
    assert [candidate["parameters"]["gap"] for candidate in candidates] == [1, 2, 3, 4, 5]
    assert all(candidate["term_count"] == 200 for candidate in candidates)
    assert all(type(term) is int for candidate in candidates for term in candidate["terms"])


def test_restricted_partition_reference_matches_optimized():
    for gap in range(1, 6):
        assert [
            generator.restricted_partition_value(n, gap) for n in range(16)
        ] == [generator.brute_force_value(n, gap) for n in range(16)]


def test_first_values_and_zero_case():
    assert generator.restricted_partition_value(0, 1) == 1
    assert generator.restricted_partition_value(1, 1) == 1
    assert generator.restricted_partition_value(2, 1) == 2
    assert generator.restricted_partition_value(2, 2) == 2


def test_candidates_are_reproducible_and_not_q_binomial():
    candidates = generator.generate_candidates(gaps=(1, 3), term_count=20)
    assert candidates == generator.generate_candidates(gaps=(1, 3), term_count=20)
    assert all(candidate["family"] == "restricted-partition-rank" for candidate in candidates)
    assert all("q-binomial" not in json.dumps(candidate) for candidate in candidates)
    assert all(generator.reproduce_candidate(candidate) == candidate["terms"] for candidate in candidates)


def test_results_json_is_valid(tmp_path):
    candidate_path = tmp_path / "candidates.json"
    results_path = tmp_path / "results.json"
    candidate_path.write_text(json.dumps(generator.generate_candidates()), encoding="utf-8")

    assert verify_file(candidate_path, results_path) == 0
    result = json.loads(results_path.read_text(encoding="utf-8"))
    assert result["candidate_count"] == 5
    assert result["pipeline_status"] == "OK"
    assert all(candidate["status"] == "VERIFIED-FINITE" for candidate in result["candidates"])
    assert all(candidate["verification"]["proven_theorem"] is False for candidate in result["candidates"])


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
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(novelty.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    monkeypatch.setattr(novelty.json, "load", lambda response: {"results": []})
    no_match = novelty.lookup_oeis([1, 2, 3], retry_delay=0)
    assert no_match["lookup_status"] == "NO_MATCH_FOUND"

    def fail(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(novelty.urllib.request, "urlopen", fail)
    failed = novelty.lookup_oeis([1, 2, 3], retries=0)
    assert failed["lookup_status"] == "LOOKUP_FAILED"
    assert failed["lookup_status"] != no_match["lookup_status"]


def test_novelty_known_q2_sequence_match(monkeypatch):
    class Response:
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(novelty.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    monkeypatch.setattr(novelty.json, "load", lambda response: [{"number": 6116}])
    result = novelty.lookup_oeis([1, 2, 5], retry_delay=0)
    assert result["lookup_status"] == "MATCH_FOUND"
    assert result["oeis_ids"] == ["A006116"]


def test_novelty_http_403_is_lookup_failure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise novelty.urllib.error.HTTPError(
            "https://oeis.org/search", 403, "Forbidden", {"Content-Type": "text/html"}, None
        )

    monkeypatch.setattr(novelty.urllib.request, "urlopen", forbidden)
    result = novelty.lookup_oeis([1, 2, 3], retries=2, retry_delay=0)
    assert result["lookup_status"] == "LOOKUP_FAILED"
    assert result["http_status"] == 403
    assert result["retry_count"] == 0
    assert result["lookup_status"] != "NO_MATCH_FOUND"


def test_novelty_timeout_retries_and_fails(monkeypatch):
    calls = 0

    def timeout(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("timed out")

    monkeypatch.setattr(novelty.urllib.request, "urlopen", timeout)
    result = novelty.lookup_oeis([1, 2, 3], retries=2, retry_delay=0)
    assert result["lookup_status"] == "LOOKUP_FAILED"
    assert result["retry_count"] == 2
    assert calls == 3
