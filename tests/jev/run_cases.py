#!/usr/bin/env python3
"""Run the pre-labeled Jev shadow cases, one smoke call then five small batches."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name("cases.json")
RESULTS = Path(__file__).with_name("results")
SCRIPT = ROOT / "skills/qualificar-conta/scripts/jev-shadow.py"
spec = importlib.util.spec_from_file_location("jev_shadow", SCRIPT)
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)


def run_group(group, log):
    data = {"account": group[0]["input"]["account"] if len(group) == 1 else "jev-experiment",
            "verdict": "incerto", "claims": [case["input"]["claims"][0] for case in group]}
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as temp:
        json.dump(data, temp, ensure_ascii=False)
        temp.flush()
        result = jev.evaluate(Path(temp.name), log)
    if result["status"] != "shadow_recorded":
        raise RuntimeError(f"shadow call skipped: {result.get('reason', result['status'])}")
    row = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    if row["status"] != "evaluated":
        raise RuntimeError(f"Jev unavailable: {row.get('reason', 'unknown')}")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("smoke", "experiment"))
    args = parser.parse_args()
    if os.environ.get("JEV_ENABLED") != "1" or not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("Jev shadow flag or API key absent")
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    RESULTS.mkdir(parents=True, exist_ok=True)
    log = RESULTS / "direct-jev-shadow.jsonl"
    smoke = RESULTS / "direct-smoke.json"
    if args.phase == "smoke":
        if smoke.exists():
            raise SystemExit("smoke already recorded; refusing a duplicate API call")
        row = run_group(cases[:1], log)
        smoke.write_text(json.dumps({"case": cases[0]["id"], "row": row}, ensure_ascii=False, indent=2))
        print(json.dumps({"phase": "smoke", "status": "evaluated", "model": row.get("model_returned"),
                          "choice": row["answers"][0]["choice"], "duration_ms": row["duration_ms"],
                          "usage": row.get("usage")}, ensure_ascii=False))
        return
    if not smoke.exists() or json.loads(smoke.read_text())["row"]["status"] != "evaluated":
        raise SystemExit("successful smoke required before experiment")
    output = RESULTS / "direct-experiment.json"
    if output.exists():
        raise SystemExit("experiment already recorded; refusing duplicate API calls")
    results = []
    remaining = cases[1:]
    for offset in range(0, len(remaining), 2):
        group = remaining[offset:offset + 2]
        row = run_group(group, log)
        for case, answer in zip(group, row["answers"]):
            results.append({"id": case["id"], "expected": case["expected"],
                            "milo_rule": case["milo_rule"], "choice": answer["choice"],
                            "confidence": answer["confidence"],
                            "probabilities": answer["probabilities"],
                            "duration_ms_batch": row["duration_ms"], "usage_batch": row.get("usage"),
                            "cost_batch": row.get("cost")})
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(json.dumps({"batch": offset // 2 + 1, "cases": [c["id"] for c in group],
                          "duration_ms": row["duration_ms"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
