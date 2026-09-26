import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "skills/redigir-abordagem/scripts/criar-rascunho.py"
SPEC = importlib.util.spec_from_file_location("criar_rascunho", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CriarRascunhoTests(unittest.TestCase):
    def test_version_is_immutable_and_keeps_exact_body(self):
        with tempfile.TemporaryDirectory() as root:
            mesa = Path(root)
            source = mesa / "body.txt"
            source.write_text("Olá, Carla.\n\nResponda PARAR.\n", encoding="utf-8")
            first = MODULE.create(mesa, "acme", source)
            source.write_text("Nova versão.\n", encoding="utf-8")
            second = MODULE.create(mesa, "acme", source)
            self.assertEqual((first["versao"], second["versao"]), (1, 2))
            self.assertEqual(Path(first["arquivo"]).read_text(), "Olá, Carla.\n\nResponda PARAR.\n")
            self.assertEqual(Path(second["arquivo"]).read_text(), "Nova versão.\n")

    def test_journal_prevents_version_reuse_after_file_loss(self):
        with tempfile.TemporaryDirectory() as root:
            mesa = Path(root)
            source = mesa / "body.txt"
            source.write_text("Corpo", encoding="utf-8")
            first = MODULE.create(mesa, "acme", source)
            Path(first["arquivo"]).unlink()
            self.assertEqual(MODULE.create(mesa, "acme", source)["versao"], 2)

    def test_account_metadata_cannot_preempt_a_version(self):
        with tempfile.TemporaryDirectory() as root:
            mesa = Path(root)
            (mesa / "contas").mkdir()
            (mesa / "contas/acme.md").write_text(
                "## Rascunhos\n### v2 — 2026-09-25\nArquivo: mesa/rascunhos/acme-v2.txt\n",
                encoding="utf-8",
            )
            source = mesa / "body.txt"
            source.write_text("Corpo", encoding="utf-8")
            self.assertEqual(MODULE.create(mesa, "acme", source)["versao"], 1)

    def test_two_simultaneous_drafts_get_distinct_versions(self):
        with tempfile.TemporaryDirectory() as root:
            mesa = Path(root)
            source = mesa / "body.txt"
            source.write_text("Corpo", encoding="utf-8")
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: MODULE.create(mesa, "acme", source), range(2)))
            self.assertEqual(sorted(result["versao"] for result in results), [1, 2])

    def test_rejects_path_escape_and_empty_body(self):
        with tempfile.TemporaryDirectory() as root:
            mesa = Path(root)
            source = mesa / "body.txt"
            source.write_text("texto", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conta_invalida"):
                MODULE.create(mesa, "../fora", source)
            source.write_text(" \n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "texto_vazio"):
                MODULE.create(mesa, "acme", source)


if __name__ == "__main__":
    unittest.main()
