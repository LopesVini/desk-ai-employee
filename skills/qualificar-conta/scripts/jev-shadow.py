#!/usr/bin/env python3
"""Evaluate public claim/source pairs without changing Milo's decisions."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
MAX_CLAIMS = 2
MAX_INPUT_BYTES = 4096
ACCOUNT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
OPTIONS = ("supported", "contradicted", "insufficient", "wrong_entity")
SOURCE_TYPES = ("official_company_page", "third_party_page", "search_snippet")
ATTRIBUTIONS = ("company", "individual", "other_entity", "unclear")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def public_host(url):
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or host == "localhost" or host.endswith(".local") or "." not in host
            or host.replace(".", "").isdigit()):
        raise ValueError("source_url_not_public_https")
    return host.lower()


def validate(raw):
    if not isinstance(raw, dict) or set(raw) != {"account", "verdict", "claims"}:
        raise ValueError("invalid_input_shape")
    account, verdict, claims = raw["account"], raw["verdict"], raw["claims"]
    if not isinstance(account, str) or not ACCOUNT.fullmatch(account):
        raise ValueError("invalid_account")
    if verdict not in ("bom fit", "incerto", "sem fit"):
        raise ValueError("invalid_verdict")
    if not isinstance(claims, list) or not 1 <= len(claims) <= MAX_CLAIMS:
        raise ValueError("invalid_claim_count")
    clean = []
    for item in claims:
        if (not isinstance(item, dict) or not {"claim", "source_excerpt", "source_url"} <= set(item)
                or set(item) - {"claim", "source_excerpt", "source_url", "source_type", "attribution"}):
            raise ValueError("invalid_claim_shape")
        claim, excerpt, url = item["claim"], item["source_excerpt"], item["source_url"]
        source_type = item.get("source_type", "third_party_page")
        attribution = item.get("attribution", "unclear")
        if source_type not in SOURCE_TYPES or attribution not in ATTRIBUTIONS:
            raise ValueError("invalid_source_metadata")
        if not isinstance(claim, str) or not 5 <= len(claim.strip()) <= 250:
            raise ValueError("invalid_claim")
        if not isinstance(excerpt, str) or not 10 <= len(excerpt.strip()) <= 600:
            raise ValueError("invalid_excerpt")
        if not isinstance(url, str):
            raise ValueError("invalid_source_url")
        host = public_host(url)
        if EMAIL.search(claim + " " + excerpt) or PHONE.search(claim + " " + excerpt):
            raise ValueError("personal_contact_in_input")
        clean.append({"claim": claim.strip(), "source_excerpt": excerpt.strip(), "source_host": host,
                      "source_type": source_type, "attribution": attribution,
                      "source_hash": digest(url)})
    return account, verdict, clean


def request_body(claims):
    state = {f"item_{i}": {"claim": c["claim"], "source_excerpt": c["source_excerpt"],
                           "source_host": c["source_host"], "source_type": c["source_type"],
                           "attribution": c["attribution"]} for i, c in enumerate(claims)}
    questions = {
        f"claim_{i}": {
            "type": "choice",
            "instructions": (f"Judge whether item_{i}.source_excerpt supports item_{i}.claim. "
                             "Use only that excerpt, not outside knowledge. A search snippet or a statement "
                             "about a different company or person does not support the claim. "
                             "A personal testimonial does not establish a company-wide fact."),
            "criteria": {
                "supported": "The excerpt directly supports the claim about the same entity.",
                "contradicted": "The excerpt directly conflicts with the claim.",
                "insufficient": "The excerpt is missing, ambiguous, partial, or too weak to establish the claim.",
                "wrong_entity": "The excerpt concerns another company or person with a similar name.",
            },
        } for i in range(len(claims))
    }
    return {"model": MODEL, "state": state, "questions": questions}


def parse_answers(response, count):
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict):
        raise ValueError("invalid_answers")
    parsed = []
    for i in range(count):
        answer = answers.get(f"claim_{i}")
        if not isinstance(answer, dict) or answer.get("type") != "choice" or answer.get("choice") not in OPTIONS:
            raise ValueError("invalid_choice")
        confidence, probabilities = answer.get("confidence"), answer.get("probabilities")
        if (not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
                or not 0 <= confidence <= 1 or not isinstance(probabilities, dict)
                or set(probabilities) != set(OPTIONS)
                or any(not isinstance(p, (int, float)) or isinstance(p, bool) or not 0 <= p <= 1
                       for p in probabilities.values())):
            raise ValueError("invalid_probabilities")
        parsed.append({"choice": answer["choice"], "confidence": confidence,
                       "probabilities": probabilities})
    return parsed


def call_jev(body, key, timeout):
    request = urllib.request.Request(
        API_URL, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(128 * 1024 + 1)
        if len(payload) > 128 * 1024:
            raise ValueError("response_too_large")
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise ValueError("invalid_response_shape")
        result["_http_status"] = response.status
        return result


def usage_summary(response):
    raw = response.get("usage")
    if not isinstance(raw, dict):
        return None
    return {key: raw[key] for key in ("input_tokens", "output_tokens")
            if isinstance(raw.get(key), int) and not isinstance(raw[key], bool) and raw[key] >= 0}


def append_log(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def evaluate(input_path, log_path, environ=None, caller=call_jev):
    env = os.environ if environ is None else environ
    if env.get("JEV_ENABLED") != "1":
        return {"status": "skipped", "reason": "disabled"}
    if env.get("JEV_MODE", "shadow") != "shadow":
        return {"status": "skipped", "reason": "shadow_only"}
    key = env.get("TYPESAFE_API_KEY", "")
    if not key:
        return {"status": "skipped", "reason": "missing_api_key"}
    try:
        data = input_path.read_bytes()
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError("input_too_large")
        account, verdict, claims = validate(json.loads(data))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "skipped", "reason": str(exc) if isinstance(exc, ValueError) else "invalid_input"}

    row = {"at": dt.datetime.now(dt.timezone.utc).isoformat(), "mode": "shadow",
           "evaluator": "claim_support_v1", "model_requested": MODEL,
           "account": account, "milo_verdict": verdict, "decision_applied": "milo_unchanged",
           "inputs": [{"claim_hash": digest(c["claim"]), "excerpt_hash": digest(c["source_excerpt"]),
                       "source_hash": c["source_hash"], "source_host": c["source_host"],
                       "source_type": c["source_type"], "attribution": c["attribution"]} for c in claims]}
    started = time.monotonic()
    try:
        timeout = min(5.0, max(0.2, float(env.get("JEV_TIMEOUT_SECONDS", "2.5"))))
        response = caller(request_body(claims), key, timeout)
        row["http_status"] = response.get("_http_status")
        row["answers"] = parse_answers(response, len(claims))
        if response.get("model") != MODEL:
            raise ValueError("unexpected_model")
        row["model_returned"] = MODEL
        row["usage"] = usage_summary(response)
        row["status"] = "evaluated"
    except urllib.error.HTTPError as exc:
        row["status"] = "unavailable"
        row["reason"] = "http_error"
        row["http_status"] = exc.code
    except (ValueError, TypeError, TimeoutError, urllib.error.URLError, OSError) as exc:
        row["status"] = "unavailable"
        row["reason"] = type(exc).__name__
    row["duration_ms"] = round((time.monotonic() - started) * 1000)
    try:
        append_log(log_path, row)
    except OSError:
        return {"status": "skipped", "reason": "log_unavailable"}
    # Do not expose Jev's decision to Milo during the shadow experiment.
    return {"status": "shadow_recorded"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--log", type=Path, default=Path("/var/lib/plow/workspace/mesa/jev-shadow.jsonl"))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.input, args.log)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
