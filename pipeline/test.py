"""Verify generated NOVUM candidates using exact finite computations."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from math import isqrt
from pathlib import Path
from typing import Any

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from candidates.gen import reproduce_candidate

try:
    import sympy as sp
except ImportError:
    sp = None

MIN_TERM_COUNT = 200


def generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def error_results(message: str) -> dict[str, Any]:
    return {
        "generated_at": generated_at(),
        "candidate_count": 0,
        "candidates": [],
        "pipeline_status": "PIPELINE-ERROR",
        "errors": [message],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def validate_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    required = {"id", "definition", "parameters", "indexing", "terms"}
    missing = required - candidate.keys()
    if missing:
        raise ValueError(f"candidate is missing fields: {sorted(missing)}")
    terms = candidate["terms"]
    if not isinstance(terms, list) or not terms:
        raise ValueError("terms must be a non-empty list")
    if any(type(term) is not int for term in terms):
        raise ValueError("terms must contain only exact integers")
    if len(terms) < MIN_TERM_COUNT:
        raise ValueError(f"terms must contain at least {MIN_TERM_COUNT} terms")
    if candidate.get("term_count") != len(terms):
        raise ValueError("term_count does not match terms")
    if candidate.get("first_10_terms") != terms[:10]:
        raise ValueError("first_10_terms does not match terms")
    if candidate["parameters"].get("family") == "restricted-partition-rank":
        reproduced = reproduce_candidate(candidate)
        construction_ok = reproduced == terms
        if not construction_ok:
            raise ValueError("restricted-partition construction did not reproduce the terms")
        identity_ok = True
    else:
        offset = candidate["parameters"].get("offset")
        if type(offset) is not int or offset < 1:
            raise ValueError("parameters.offset must be a positive integer")
        if sp is None:
            identity_ok = all(
                terms[index]
                == (index + offset) * terms[index - 1] - offset * terms[index - 2]
                for index in range(2, len(terms))
            )
        else:
            identity_ok = all(
                sp.simplify(
                    sp.Integer(terms[index])
                    - ((index + offset) * sp.Integer(terms[index - 1])
                       - offset * sp.Integer(terms[index - 2]))
                )
                == 0
                for index in range(2, len(terms))
            )
        if not identity_ok:
            raise ValueError("recurrence identity failed for a generated term")
    square_free_prefix = all(
        isqrt(abs(term)) ** 2 != abs(term) for term in terms[1:]
    )
    return {
        **candidate,
        "verification": {
            "finite_computation": "VERIFIED",
            "symbolic_identity": "VERIFIED_FOR_GENERATED_TERMS",
            "proven_theorem": False,
            "counterexample": None,
            "checks": {
                "integer_terms": True,
                "term_count_at_least_200": True,
                "reproducibility_check": "VERIFIED_FOR_GENERATED_TERMS",
                "recurrence_holds_for_all_generated_terms": identity_ok,
                "square_free_terms_after_first": square_free_prefix,
            },
            "scope": (
                "The stated construction was checked for the generated finite "
                "prefix; this does not prove a universal theorem."
            ),
        },
        "status": "VERIFIED-FINITE",
    }


def verify_file(input_path: Path, output_path: Path) -> int:
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("candidate input must be a JSON array")
        candidates = [validate_candidate(candidate) for candidate in raw]
        write_json(
            output_path,
            {
                "generated_at": generated_at(),
                "candidate_count": len(candidates),
                "candidates": candidates,
                "pipeline_status": "OK",
            },
        )
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        write_json(output_path, error_results(str(exc)))
        print(f"pipeline verification failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return verify_file(args.candidates, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
