#!/usr/bin/env python3
"""Read a completed account card and record eligible public claims in shadow."""

import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit


CLIENT = Path(__file__).with_name("jev-shadow.py")
spec = importlib.util.spec_from_file_location("jev_shadow", CLIENT)
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)

WORD = re.compile(r"[a-zà-ÿ0-9]+", re.IGNORECASE)
STOP = {"a", "as", "o", "os", "de", "da", "do", "das", "dos", "em", "e", "com",
        "para", "por", "que", "uma", "um", "mais", "site", "empresa", "grupo"}
URL = re.compile(r"https://[^\s)]+")
QUOTE = re.compile(r'["“]([^"”]{10,600})["”]')
REASON = re.compile(r"^\s*\d+\.\s+(.+)$", re.MULTILINE)
FACT = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)


def section(markdown, title):
    match = re.search(r"^## " + re.escape(title) + r"\s*$", markdown, re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""
    end = re.search(r"^## ", markdown[match.end():], re.MULTILINE)
    return markdown[match.end(): match.end() + end.start() if end else None]


def terms(value):
    return {w.lower() for w in WORD.findall(value) if len(w) > 2 and w.lower() not in STOP}


def extract(account_path):
    if account_path.is_symlink() or not account_path.is_file() or account_path.stat().st_size > 32_768:
        return None
    markdown = account_path.read_text(encoding="utf-8")
    verdict_text = section(markdown, "Veredito")
    fact_text = section(markdown, "Fatos (com fonte)") or section(markdown, "Fatos")
    if not verdict_text or not fact_text:
        return None
    first = next((line.strip() for line in verdict_text.splitlines() if line.strip()), "")
    labels = {label.lower() for label in re.findall(r"\b(bom fit|incerto|sem fit)\b", first, re.IGNORECASE)}
    if len(labels) != 1:
        return None
    verdict = labels.pop()
    facts = []
    for line in FACT.findall(fact_text):
        quote, url = QUOTE.search(line), URL.search(line)
        if quote and url:
            facts.append((quote.group(1).strip(), url.group(0).rstrip(".,;")))
    claims = []
    used = set()
    for reason in REASON.findall(verdict_text):
        claim = re.split(r"[,;—(]", reason, maxsplit=1)[0].strip()
        joined = re.split(r"\s+e\s+", claim, maxsplit=1, flags=re.IGNORECASE)
        if len(joined) == 2 and all(len(terms(part)) >= 2 for part in joined):
            claim = joined[0]
        if not 5 <= len(claim) <= 250:
            continue
        words = terms(claim)
        options = [(len(words & terms(excerpt)), i, excerpt, url)
                   for i, (excerpt, url) in enumerate(facts) if i not in used]
        if not options:
            continue
        score, i, excerpt, url = max(options)
        if score < 2:
            continue
        host = urlsplit(url).hostname or ""
        account_words = account_path.stem.split("-")
        official = any(len(w) > 3 and w in host.replace("-", "") for w in account_words)
        candidate = {"claim": claim, "source_excerpt": excerpt, "source_url": url,
                     "source_type": "official_company_page" if official else "third_party_page",
                     "attribution": "company"}
        try:
            jev.validate({"account": account_path.stem, "verdict": verdict, "claims": [candidate]})
        except ValueError:
            continue
        claims.append(candidate)
        used.add(i)
        if len(claims) == jev.MAX_CLAIMS:
            break
    if not claims:
        return None
    return {"account": account_path.stem, "verdict": verdict, "claims": claims}


def signature(account, verdict, clean):
    return (account, verdict,
            tuple((jev.digest(c["claim"]), jev.digest(c["source_excerpt"]), c["source_hash"])
                  for c in clean))


def recorded(log_path, expected):
    if not log_path.exists():
        return False
    with log_path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                row = json.loads(line)
                found = (row.get("account"), row.get("milo_verdict"),
                         tuple((i["claim_hash"], i["excerpt_hash"], i["source_hash"])
                               for i in row.get("inputs", [])))
                if found == expected:
                    return True
            except (ValueError, KeyError, TypeError):
                continue
    return False


def run(mesa, account_path, environ=None, caller=jev.call_jev):
    env = os.environ if environ is None else environ
    if env.get("JEV_ENABLED") != "1" or env.get("JEV_MODE") != "shadow" or not env.get("TYPESAFE_API_KEY"):
        return "disabled"
    mesa = Path(mesa).resolve()
    account_path = Path(account_path)
    if (account_path.parent.resolve() != mesa / "contas" or
            not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.md", account_path.name)):
        return "invalid_account_path"
    data = extract(account_path)
    if data is None:
        return "no_eligible_claims"
    account, verdict, clean = jev.validate(data)
    expected = signature(account, verdict, clean)
    lock_path = mesa / ".jev-shadow.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        log_path = mesa / "jev-shadow.jsonl"
        if recorded(log_path, expected):
            return "duplicate"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as temp:
            json.dump(data, temp, ensure_ascii=False)
            temp.flush()
            return jev.evaluate(Path(temp.name), log_path, env, caller)["status"]
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesa", type=Path, required=True)
    parser.add_argument("--account", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.mesa, args.account)
    except Exception:
        # A detached shadow post-step cannot block or change the Milo reply.
        pass


if __name__ == "__main__":
    main()
