#!/usr/bin/env python3
"""Replay recorded Milo claim decisions through the unchanged Jev shadow client."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[2]
DATASET = Path(__file__).with_name("real_replay_cases.json")
RESULTS = Path(__file__).with_name("results")
BASELINE = RESULTS / "real-replay-baseline.json"
OUTPUT = RESULTS / "real-replay.json"
LOG = RESULTS / "real-replay-shadow.jsonl"
CLIENT = ROOT / "skills/qualificar-conta/scripts/jev-shadow.py"
spec = importlib.util.spec_from_file_location("jev_shadow", CLIENT)
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)


def normalize(value):
    return re.sub(r"\s+", " ", value).strip()


def recovered_text(item):
    payload = item.get("payload", {})
    if payload.get("type") == "message":
        return "\n".join(part.get("text", "") for part in payload.get("content", [])
                         if part.get("type") == "input_text")
    if payload.get("type") == "custom_tool_call_output":
        parts = []
        for part in payload.get("output", []):
            raw = part.get("text", "")
            try:
                wrapped = json.loads(raw)
                if isinstance(wrapped, dict):
                    raw = wrapped.get("value", wrapped).get("output", raw)
            except (TypeError, ValueError):
                pass
            parts.append(raw)
        return "\n".join(parts)
    return ""


def checked_dataset():
    data_bytes = DATASET.read_bytes()
    data = json.loads(data_bytes)
    cases = data["cases"]
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("duplicate_case_id")
    counts = {}
    for case in cases:
        counts[case["account"]] = counts.get(case["account"], 0) + 1
        jev.validate({"account": case["account"], "verdict": case["milo_verdict"],
                      "claims": [case["input"]]})
        if case["ground_truth"] not in jev.OPTIONS or case["milo_classification"] not in jev.OPTIONS:
            raise ValueError("invalid_label")
    if any(count > jev.MAX_CLAIMS for count in counts.values()):
        raise ValueError("claim_cap_exceeded")
    needed = {case["milo_output_ordinal"] for case in cases}
    found = {}
    session = os.environ.get("JEV_HISTORICAL_SESSION")
    if not session or Path(session).name != data["historical_session_ref"]:
        raise ValueError("historical_session_path_required")
    with open(session, encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            if item.get("ordinal") in needed:
                found[item["ordinal"]] = recovered_text(item)
    for case in cases:
        if normalize(case["milo_output"]) not in normalize(found.get(case["milo_output_ordinal"], "")):
            raise ValueError("historical_output_not_found:" + case["id"])
    return data, hashlib.sha256(data_bytes).hexdigest()


def baseline():
    data, digest = checked_dataset()
    cases = data["cases"]
    primary = [case for case in cases if case["primary_scored"]]
    row = {"dataset_sha256": digest, "cases": len(cases), "primary_cases": len(primary),
           "primary_milo_correct": sum(c["milo_classification"] == c["ground_truth"] for c in primary),
           "primary_milo_wrong": sum(c["milo_classification"] != c["ground_truth"] for c in primary),
           "ambiguous_excluded": [c["id"] for c in cases if not c["primary_scored"]],
           "verdicts": {account: next(c["milo_verdict"] for c in cases if c["account"] == account)
                        for account in sorted({c["account"] for c in cases})}}
    RESULTS.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(row, ensure_ascii=False))


def experiment():
    data, digest = checked_dataset()
    if not BASELINE.exists() or json.loads(BASELINE.read_text())["dataset_sha256"] != digest:
        raise SystemExit("matching baseline required before any live request")
    if OUTPUT.exists() or LOG.exists():
        raise SystemExit("replay already started; refusing duplicate live requests")
    if os.environ.get("JEV_ENABLED") != "1" or os.environ.get("JEV_MODE") != "shadow" or not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit("shadow flag or private credential absent")
    cases = data["cases"]
    results = []
    accounts = list(dict.fromkeys(case["account"] for case in cases))
    for account in accounts:
        group = [case for case in cases if case["account"] == account]
        request = {"account": account, "verdict": group[0]["milo_verdict"],
                   "claims": [case["input"] for case in group]}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as temp:
            os.chmod(temp.name, 0o600)
            json.dump(request, temp, ensure_ascii=False)
            temp.flush()
            outcome = jev.evaluate(Path(temp.name), LOG)
        if outcome.get("status") != "shadow_recorded":
            raise RuntimeError("shadow call skipped: " + outcome.get("reason", outcome["status"]))
        row = json.loads(LOG.read_text(encoding="utf-8").splitlines()[-1])
        if row.get("status") != "evaluated":
            raise RuntimeError("Jev unavailable; status=" + str(row.get("http_status")) +
                               " reason=" + str(row.get("reason")))
        for case, answer in zip(group, row["answers"]):
            results.append({"id": case["id"], "account": account,
                            "primary_scored": case["primary_scored"],
                            "milo": case["milo_classification"], "expected": case["ground_truth"],
                            "jev": answer["choice"], "confidence": answer["confidence"],
                            "probabilities": answer["probabilities"],
                            "request_latency_ms": row["duration_ms"],
                            "request_usage": row.get("usage"), "http_status": row.get("http_status"),
                            "decision_applied": row.get("decision_applied")})
        OUTPUT.write_text(json.dumps({"dataset_sha256": digest, "results": results},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"account": account, "cases": [c["id"] for c in group],
                          "status": "evaluated", "latency_ms": row["duration_ms"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("baseline", "experiment"))
    args = parser.parse_args()
    baseline() if args.phase == "baseline" else experiment()
