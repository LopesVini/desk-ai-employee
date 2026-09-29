import importlib.util
import pathlib
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ler", RAIZ / "skills/qualificar-conta/scripts/ler.py")
ler = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ler)

CORPO = "Somos uma rede de supermercados com 12 lojas no interior de São Paulo. " * 5
PAGINA = f"""<html><head><title> Rede Exemplo | Supermercados </title>
<meta name="description" content="Rede regional com 12 lojas.">
<style>.x{{color:red}}</style><script>var segredo = "não aparece";</script></head>
<body><header><a href="/quem-somos">Quem somos</a> <a href="/lojas/">Nossas lojas</a>
<a href="https://outro.com.br/sobre">Sobre o parceiro</a> <a href="/produtos">Produtos</a></header>
<p>{CORPO}</p>
<footer><a href="/canal-de-etica">Canal de Ética</a> <a href="mailto:rh@exemplo.com.br?subject=oi">RH</a>
Fale com contato@exemplo.com.br</footer></body></html>"""


class TestLerHtml(unittest.TestCase):
    def setUp(self):
        self.r = ler.ler_html(PAGINA, "https://www.exemplo.com.br/", procura=r"canal de (é|e)tica|den[úu]ncia",
                              coletar_emails=True)

    def test_texto_sem_script_nem_estilo(self):
        self.assertTrue(self.r["ok"])
        self.assertIn("12 lojas", self.r["texto"])
        self.assertNotIn("segredo", self.r["texto"])
        self.assertNotIn("color:red", self.r["texto"])
        self.assertEqual(self.r["titulo"], "Rede Exemplo | Supermercados")
        self.assertEqual(self.r["descricao"], "Rede regional com 12 lojas.")

    def test_so_links_internos_uteis(self):
        urls = [l["url"] for l in self.r["links_uteis"]]
        self.assertIn("https://www.exemplo.com.br/quem-somos", urls)
        self.assertIn("https://www.exemplo.com.br/lojas/", urls)
        self.assertNotIn("https://outro.com.br/sobre", urls)
        self.assertNotIn("https://www.exemplo.com.br/produtos", urls)

    def test_emails_de_mailto_e_do_texto(self):
        self.assertEqual(self.r["emails"], ["contato@exemplo.com.br", "rh@exemplo.com.br"])

    def test_nao_coleta_emails_por_padrao_na_prospeccao(self):
        r = ler.ler_html(PAGINA, "https://www.exemplo.com.br/")
        self.assertNotIn("emails", r)

    def test_procura_acha_link_do_rodape(self):
        p = self.r["procura"]
        self.assertTrue(p["encontrado"])
        self.assertEqual(p["links"][0]["url"], "https://www.exemplo.com.br/canal-de-etica")

    def test_procura_sem_ocorrencia(self):
        r = ler.ler_html(PAGINA, "https://www.exemplo.com.br/", procura="ouvidoria")
        self.assertFalse(r["procura"]["encontrado"])

    def test_texto_limitado(self):
        r = ler.ler_html(PAGINA, "https://www.exemplo.com.br/", maximo=50)
        self.assertLessEqual(len(r["texto"]), 50)
        self.assertGreater(r["tamanho_texto"], 50)

    def test_pagina_de_javascript_nao_serve_de_evidencia(self):
        r = ler.ler_html('<html><head><title>App</title></head><body><div id="root"></div>'
                         '<script>render()</script></body></html>', "https://app.exemplo.com/")
        self.assertFalse(r["ok"])
        self.assertEqual(r["motivo"], "pouco_texto")

    def test_email_oculto_do_cloudflare(self):
        r = ler.ler_html(PAGINA.replace("</footer>", '<a href="/cdn-cgi/l/email-protection#abc">[email&#160;protected]</a></footer>'),
                         "https://www.exemplo.com.br/")
        self.assertTrue(r["email_oculto"])
        self.assertNotIn("emails", r)

    def test_nao_decodifica_email_do_cloudflare(self):
        chave = 0x42
        codigo = f"{chave:02x}" + "".join(f"{ord(c) ^ chave:02x}" for c in "vendas@exemplo.com.br")
        r = ler.ler_html(PAGINA.replace("</footer>", f'<a href="/cdn-cgi/l/email-protection" data-cfemail="{codigo}">[email&#160;protected]</a></footer>'),
                         "https://www.exemplo.com.br/", coletar_emails=True)
        self.assertTrue(r["email_oculto"])
        self.assertNotIn("vendas@exemplo.com.br", r["emails"])

    def test_email_na_descricao(self):
        r = ler.ler_html(PAGINA.replace("Rede regional com 12 lojas.", "Fale com sac@exemplo.com.br"),
                         "https://www.exemplo.com.br/", coletar_emails=True)
        self.assertIn("sac@exemplo.com.br", r["emails"])

    def test_texto_grudado_nao_vira_outro_email(self):
        r = ler.ler_html(PAGINA.replace("Rede regional com 12 lojas.", "Nosso E-mailsac@exemplo.com.br")
                         .replace("</footer>", '<a href="mailto:sac@exemplo.com.br">SAC</a></footer>'),
                         "https://www.exemplo.com.br/", coletar_emails=True)
        self.assertIn("sac@exemplo.com.br", r["emails"])
        self.assertNotIn("e-mailsac@exemplo.com.br", r["emails"])


class TestUso(unittest.TestCase):
    def test_procura_invalida(self):
        self.assertEqual(ler.main(["exemplo.com.br", "--procura", "("]), 2)


class TestFetchSeguro(unittest.TestCase):
    def test_recusa_loopback_e_endereco_de_metadata(self):
        for url in ("http://127.0.0.1/", "http://169.254.169.254/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                ler._validar_url_publica(url)

    def test_recusa_dns_que_resolve_para_endereco_privado(self):
        resposta = [(2, 1, 6, "", ("10.0.0.7", 80))]
        with mock.patch.object(ler.socket, "getaddrinfo", return_value=resposta):
            with self.assertRaises(ValueError):
                ler._validar_url_publica("http://interno.exemplo/")

    def test_redirecionamento_e_validado_antes_da_segunda_conexao(self):
        cabecalhos = {"Location": "http://127.0.0.1:18790/mcp"}
        with mock.patch.object(ler, "_requisitar", return_value=(302, cabecalhos, b"", "utf-8")) as pedido:
            with mock.patch.object(ler, "_resolver_publico", return_value="93.184.216.34"):
                with self.assertRaises(ValueError):
                    ler.baixar("https://exemplo.com/")
        pedido.assert_called_once()

    def test_recusa_porta_nao_web(self):
        with self.assertRaises(ValueError):
            ler._validar_url_publica("http://exemplo.com:18790/")


if __name__ == "__main__":
    unittest.main()
