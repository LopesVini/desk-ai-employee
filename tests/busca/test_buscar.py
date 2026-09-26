import importlib.util
import pathlib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("buscar", RAIZ / "skills/qualificar-conta/scripts/buscar.py")
buscar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(buscar)

PAGINA_REAL = (pathlib.Path(__file__).parent / "ddg-colegio-ph.html").read_text(encoding="utf-8", errors="replace")


class TestLeitura(unittest.TestCase):
    def test_pagina_real_traz_site_oficial_primeiro(self):
        resultados = buscar.ler_resultados(PAGINA_REAL, 5)
        self.assertGreaterEqual(len(resultados), 3)
        self.assertTrue(resultados[0]["url"].startswith("https://ph.com.br/"))
        self.assertIn("pH", resultados[0]["titulo"])
        self.assertTrue(resultados[0]["trecho"])

    def test_respeita_maximo_e_nao_repete_url(self):
        resultados = buscar.ler_resultados(PAGINA_REAL, 2)
        self.assertEqual(len(resultados), 2)
        self.assertNotEqual(resultados[0]["url"], resultados[1]["url"])

    def test_redirecionamento_vira_url_de_destino(self):
        href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemplo.com.br%2Fequipe&rut=abc"
        self.assertEqual(buscar.url_real(href), "https://exemplo.com.br/equipe")

    def test_anuncio_e_descartado(self):
        pagina = ('<a class="result__a" href="https://duckduckgo.com/y.js?ad_domain=x">Anúncio</a>'
                  '<a class="result__a" href="https://empresa.com.br/">Empresa</a>'
                  '<a class="result__snippet" href="#">Sobre a <b>empresa</b></a>')
        resultados = buscar.ler_resultados(pagina, 5)
        self.assertEqual([r["url"] for r in resultados], ["https://empresa.com.br/"])
        self.assertEqual(resultados[0]["trecho"], "Sobre a empresa")

    def test_pagina_de_verificacao_e_bloqueio(self):
        self.assertTrue(buscar.bloqueado('<div class="anomaly-modal__title">...</div>'))
        self.assertFalse(buscar.bloqueado(PAGINA_REAL))

    def test_consulta_vazia_e_uso_invalido(self):
        self.assertEqual(buscar.main(["   "]), 2)


if __name__ == "__main__":
    unittest.main()
