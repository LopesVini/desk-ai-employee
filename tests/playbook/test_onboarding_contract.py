"""Contratos estáticos de instruções; não executam nem simulam um modelo."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILL = (ROOT / "skills/aprender-playbook/SKILL.md").read_text()
PROSPECT = (ROOT / "skills/prospectar/SKILL.md").read_text()


class OnboardingContract(unittest.TestCase):
    def test_no_literal_portuguese_response_templates(self):
        for wording in ("Oi! Sou o Milo", "Entendi assim", "Acertei o tipo de cliente",
                        "Fecho o perfil assim", "Fechei o perfil", "Beleza. Me pede",
                        "Carla, me responde", "Pronto: a Carla", "Isso vira regra",
                        "Usei a regra", "Antes de qualquer e-mail sair", "Quem mais aí",
                        "Se quiser, eu mesmo mando", "Quer que eu te mande"):
            with self.subTest(wording=wording):
                self.assertNotIn(wording, SKILL)
        self.assertIn("Milo prompt's CURRENT-message language rule", SKILL)
        self.assertIn("Quoted incoming messages", SKILL)

    def test_pre_message_greeting_uses_english_without_locale_guessing(self):
        greeting = " ".join(SKILL.split("For an automatic first greeting", 1)[1].split("## 1.", 1)[0].split())
        self.assertIn("before any user message", greeting)
        self.assertIn("no reliable owner/install locale", greeting)
        self.assertIn("use English", greeting)
        self.assertIn("Do not infer language from a phone country code, timezone or host locale", greeting)
        self.assertIn("do not offer a language picker or a bilingual greeting", greeting)
        self.assertIn("CURRENT message controls the reply", greeting)

    def test_workflow_confirmation_and_ledger_guards_remain_explicit(self):
        for invariant in ("the company's site, or a sentence about what they sell and to whom",
                          "Ask nothing else now", "never `mesa/playbook.md`",
                          "In the same turn, run `prospectar`", "never name a company you did not find",
                          "Choosing a company to", "confirm the profile AND research the named company",
                          "including the ledger sync in step 6", "do not start deep research yet",
                          "Remove\n   `playbook-proposta.md` only after that read succeeds",
                          "config set --chave limite_diario --valor <limit in the playbook> --por plow-owner",
                          "zero and stays closed if this fails"):
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, SKILL)

    def test_prospecting_reply_example_is_semantic_and_preserves_quotes(self):
        reply = PROSPECT.split("## 6. Reply", 1)[1].split("## Limits", 1)[0]
        self.assertIn("illustrate layout", reply)
        self.assertIn("sender's CURRENT message language", reply)
        self.assertIn("keep source quotations verbatim", reply)


if __name__ == "__main__":
    unittest.main()
