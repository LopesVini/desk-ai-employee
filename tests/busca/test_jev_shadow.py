"""The optional evaluator is observable but cannot steer Milo's turn."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "skills/qualificar-conta/scripts/jev-shadow.py"
spec = importlib.util.spec_from_file_location("jev_shadow", SCRIPT)
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)


def sample():
    return {
        "account": "empresa-exemplo",
        "verdict": "incerto",
        "claims": [{
            "claim": "A empresa opera três unidades no Rio.",
            "source_excerpt": "Operamos três unidades na cidade do Rio de Janeiro.",
            "source_url": "https://example.com/sobre?campaign=private",
            "source_type": "official_company_page",
            "attribution": "company",
        }],
    }


class JevShadowTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.input = Path(self.folder.name) / "input.json"
        self.log = Path(self.folder.name) / "shadow.jsonl"
        self.input.write_text(json.dumps(sample()), encoding="utf-8")

    def test_disabled_does_not_call_or_log(self):
        result = jev.evaluate(self.input, self.log, {"JEV_ENABLED": "0"},
                              lambda *_: self.fail("called while disabled"))
        self.assertEqual(result, {"status": "skipped", "reason": "disabled"})
        self.assertFalse(self.log.exists())

    def test_shadow_logs_typed_result_without_returning_decision_or_raw_input(self):
        def fake(body, key, timeout):
            self.assertEqual(key, "test-key")
            self.assertEqual(timeout, 2.5)
            self.assertEqual(body["model"], "jev-1.13.0")
            self.assertEqual(body["state"]["item_0"]["source_host"], "example.com")
            self.assertEqual(body["state"]["item_0"]["source_type"], "official_company_page")
            self.assertNotIn("campaign=private", json.dumps(body))
            return {"model": "jev-1.13.0", "_http_status": 200,
                    "usage": {"input_tokens": 120},
                    "answers": {
                "claim_0": {"type": "choice", "choice": "supported", "confidence": 0.9,
                            "probabilities": {"supported": 0.9, "contradicted": 0.02,
                                              "insufficient": 0.06, "wrong_entity": 0.02}}}}

        result = jev.evaluate(self.input, self.log,
                              {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"}, fake)
        self.assertEqual(result, {"status": "shadow_recorded"})
        row = json.loads(self.log.read_text(encoding="utf-8"))
        self.assertEqual(row["status"], "evaluated")
        self.assertEqual(row["milo_verdict"], "incerto")
        self.assertEqual(row["answers"][0]["choice"], "supported")
        self.assertEqual(row["http_status"], 200)
        self.assertEqual(row["usage"], {"input_tokens": 120})
        self.assertNotIn("cost", row)
        self.assertNotIn("Operamos", self.log.read_text(encoding="utf-8"))
        self.assertNotIn("test-key", self.log.read_text(encoding="utf-8"))
        self.assertEqual(self.log.stat().st_mode & 0o777, 0o600)

    def test_unavailable_api_is_recorded_and_does_not_raise(self):
        result = jev.evaluate(self.input, self.log,
                              {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"},
                              lambda *_: (_ for _ in ()).throw(TimeoutError()))
        self.assertEqual(result, {"status": "shadow_recorded"})
        self.assertEqual(json.loads(self.log.read_text())["status"], "unavailable")

    def test_http_error_logs_only_status_without_response_body(self):
        error = urllib.error.HTTPError("https://api.typesafe.ai/v1/systemone", 401, "private detail", {}, None)
        result = jev.evaluate(self.input, self.log,
                              {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"},
                              lambda *_: (_ for _ in ()).throw(error))
        self.assertEqual(result, {"status": "shadow_recorded"})
        row = json.loads(self.log.read_text())
        self.assertEqual((row["status"], row["reason"], row["http_status"]),
                         ("unavailable", "http_error", 401))
        self.assertNotIn("private detail", self.log.read_text())

    def test_personal_contact_is_rejected_before_call(self):
        data = sample()
        data["claims"][0]["source_excerpt"] = "Escreva para maria@example.com sobre as três unidades."
        self.input.write_text(json.dumps(data), encoding="utf-8")
        result = jev.evaluate(self.input, self.log,
                              {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"},
                              lambda *_: self.fail("private content sent"))
        self.assertEqual(result["reason"], "personal_contact_in_input")

    def test_invalid_answer_cannot_be_treated_as_success(self):
        result = jev.evaluate(self.input, self.log,
                              {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"},
                              lambda *_: {"answers": {"claim_0": {"choice": "send"}}})
        self.assertEqual(result, {"status": "shadow_recorded"})
        self.assertEqual(json.loads(self.log.read_text())["status"], "unavailable")

    def test_unrecognized_source_metadata_is_rejected_before_call(self):
        data = sample()
        data["claims"][0]["source_type"] = "private_crm"
        self.input.write_text(json.dumps(data), encoding="utf-8")
        result = jev.evaluate(self.input, self.log,
                              {"JEV_ENABLED": "1", "TYPESAFE_API_KEY": "test-key"},
                              lambda *_: self.fail("invalid metadata sent"))
        self.assertEqual(result["reason"], "invalid_source_metadata")


    def test_direct_transport_uses_typesafe_endpoint_and_bearer_key(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_):
                return b'{"model":"jev-1.13.0","answers":{}}'

        def fake_urlopen(request, timeout):
            self.assertEqual(request.full_url, "https://api.typesafe.ai/v1/systemone")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            self.assertEqual(json.loads(request.data)["model"], "jev-1.13.0")
            self.assertEqual(timeout, 2.5)
            return Response()

        with patch.object(jev.urllib.request, "urlopen", fake_urlopen):
            result = jev.call_jev({"model": jev.MODEL}, "test-key", 2.5)
        self.assertEqual(result["_http_status"], 200)


if __name__ == "__main__":
    unittest.main()
