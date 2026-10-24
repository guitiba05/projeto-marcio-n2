"""Fixtures compartilhadas: carrega a bateria de casos de `tests/cases/`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CASES_DIR = Path(__file__).parent / "cases"
CASES_DIR = Path(__file__).resolve().parents[1] / "data" / "cases"

def load_cases() -> list[dict]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            record = json.load(handle)
        record["slug"] = path.stem
        cases.append(record)
    return cases


CASES = load_cases()
OK_CASES = [case for case in CASES if case["expect"]["status"] == "ok"]
ERROR_CASES = [case for case in CASES if case["expect"]["status"] == "error"]


@pytest.fixture(scope="session")
def all_cases() -> list[dict]:
    return CASES
