"""A persisted account triggers an isolated, idempotent shadow evaluation."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "skills/qualificar-conta/scripts/jev-poststep.py"
spec = importlib.util.spec_from_file_location("jev_poststep", SCRIPT)
post = importlib.util.module_from_spec(spec)
spec.loader.exec_module(post)

CARD = '''# Empresa Exemplo

- Status: pesquisada

## Veredito

Bom fit — pesquisada.

1. A empresa opera três unidades no Rio (site oficial)

## Fatos (com fonte)

- "A empresa opera três unidades na cidade do Rio de Janeiro." — https://empresa-exemplo.com.br/sobre

## Contato

- não encontrado
'''
ENV = {"JEV_ENABLED": "1", "JEV_MODE": "shadow", "TYPESAFE_API_KEY": "test-key"}


class PoststepTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.mesa = Path(self.folder.name) / "mesa"
        (self.mesa / "contas").mkdir(parents=True)
        self.card = self.mesa / "contas/empresa-exemplo.md"
        self.card.write_text(CARD, encoding="utf-8")
        self.original = self.card.read_bytes()
        self.calls = 0

    def caller(self, body, key, timeout):
        self.calls += 1
        self.assertEqual(key, "test-key")
        self.assertEqual(len(body["state"]), 1)
        return {"model": post.jev.MODEL, "_http_status": 200,
                "usage": {"input_tokens": 42}, "answers": {"claim_0": {
                    "type": "choice", "choice": "contradicted", "confidence": .8,
                    "probabilities": {"supported": .1, "contradicted": .8,
                                      "insufficient": .05, "wrong_entity": .05}}}}

    def test_disabled_does_not_call_or_create_artifact(self):
        self.assertEqual(post.run(self.mesa, self.card, {**ENV, "JEV_ENABLED": "0"}, self.caller), "disabled")
        self.assertEqual(post.run(self.mesa, self.card, {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"}, self.caller), "disabled")
        self.assertEqual(self.calls, 0)
        self.assertFalse((self.mesa / "jev-shadow.jsonl").exists())
        self.assertFalse((self.mesa / ".jev-shadow.lock").exists())

    def test_shadow_records_without_mutating_qualification(self):
        self.assertEqual(post.run(self.mesa, self.card, ENV, self.caller), "shadow_recorded")
        row = json.loads((self.mesa / "jev-shadow.jsonl").read_text())
        self.assertEqual((row["status"], row["answers"][0]["choice"]), ("evaluated", "contradicted"))
        self.assertEqual(row["decision_applied"], "milo_unchanged")
        self.assertEqual(row["milo_verdict"], "bom fit")
        self.assertEqual(self.card.read_bytes(), self.original)

    def test_timeout_keeps_qualification_unchanged(self):
        def timeout(*_):
            raise TimeoutError()
        self.assertEqual(post.run(self.mesa, self.card, ENV, timeout), "shadow_recorded")
        row = json.loads((self.mesa / "jev-shadow.jsonl").read_text())
        self.assertEqual(row["status"], "unavailable")
        self.assertEqual(self.card.read_bytes(), self.original)

    def test_same_claim_is_not_called_twice(self):
        self.assertEqual(post.run(self.mesa, self.card, ENV, self.caller), "shadow_recorded")
        self.assertEqual(post.run(self.mesa, self.card, ENV, self.caller), "duplicate")
        self.assertEqual(self.calls, 1)
        self.assertEqual(len((self.mesa / "jev-shadow.jsonl").read_text().splitlines()), 1)

    def test_no_sourced_claim_skips(self):
        self.card.write_text(CARD.replace('"A empresa opera três unidades na cidade do Rio de Janeiro."',
                                          'A empresa opera três unidades na cidade do Rio de Janeiro.'), encoding="utf-8")
        self.assertEqual(post.run(self.mesa, self.card, ENV, self.caller), "no_eligible_claims")
        self.assertEqual(self.calls, 0)

    def test_requalification_verdict_with_leading_prose(self):
        self.card.write_text(CARD.replace("Bom fit — pesquisada.",
                                          "Requalificado hoje: mantém-se bom fit pelo porte."), encoding="utf-8")
        self.assertEqual(post.run(self.mesa, self.card, ENV, self.caller), "shadow_recorded")

    def test_conjoined_reason_is_reduced_to_one_supported_fact(self):
        card = CARD.replace("A empresa opera três unidades no Rio (site oficial)",
                            "A empresa opera três unidades no Rio e atua em 17 estados (site oficial)")
        self.card.write_text(card, encoding="utf-8")
        data = post.extract(self.card)
        self.assertEqual(data["claims"][0]["claim"], "A empresa opera três unidades no Rio")


if __name__ == "__main__":
    unittest.main()
