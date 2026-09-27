"""Testes do `milo-envio enviar`: livro + API de e-mail da Plow, contra um servidor falso local.

Rodar da raiz do repositório:
    python -m unittest discover -s tests/envio -v
"""
import http.server
import json
import threading
import unittest

from test_milo_envio import DONO, PARA, Base

TEXTO = "Assunto: Canal de ética na Acme\n\nOlá, Maria.\n\nSou o Milo, assistente de IA da Prossigo.\nResponda PARAR para não receber mais.\n"
CARLA = "carla@prossigo.com.br"


class PlowFalsa(http.server.BaseHTTPRequestHandler):
    """Responde como a API da Plow. `servidor.resposta` escolhe o resultado do envio."""

    def log_message(self, *args):
        pass

    def responder(self, codigo, corpo):
        dados = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path == "/v1/agents/me":
            return self.responder(200, {"line": {"uid": "ln_p1", "display_name": "Willow"}})
        if self.path == "/v1/lines":
            return self.responder(200, {"data": [
                {"uid": "ln_e_elm", "provider_type": "email", "provider_key": "elm@plow.co", "display_name": "Elm"},
                {"uid": "ln_e_willow", "provider_type": "email", "provider_key": "willow@plow.co", "display_name": "Willow"},
            ]})
        self.responder(404, {"detail": "Not Found"})

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.envios.append((self.path, corpo, self.headers["Authorization"]))
        codigo, resposta = self.server.resposta
        if codigo is None:
            self.close_connection = True
            return
        self.responder(codigo, resposta)


class TestEnviar(Base):
    def setUp(self):
        super().setUp()
        self.servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PlowFalsa)
        self.servidor.envios = []
        self.servidor.resposta = (201, {"status": "sent", "message_id": "gm_1", "thread_id": "gm_1"})
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)
        self.env = {"PLOW_API_BASE": f"http://127.0.0.1:{self.servidor.server_address[1]}",
                    "PLOW_AGENT_TOKEN": "plow_teste"}
        self.config("envio_automatico", 1)

    def aprovar_email(self, conta="acme", para=PARA, texto=TEXTO):
        arquivo = self.texto(texto)
        return self.aprovar(conta=conta, chat=None, para=para, texto=arquivo), arquivo

    def enviar(self, ap, arquivo, *extra):
        return self.cli("enviar", "--aprovacao", ap, "--texto-arquivo", arquivo, *extra, env=self.env)

    def liberar_por_email(self):
        ap, arquivo = self.aprovar_email(conta="teste-instalacao", para=CARLA)
        codigo, r = self.enviar(ap, arquivo, "--teste", "--para", CARLA)
        self.assertEqual((codigo, r["estado"], r["teste"]), (0, "enviado", True), r)
        self.ok("liberar", "--envio", r["envio_id"], "--aprovador", DONO)

    def test_desligado_por_padrao(self):
        self.config("envio_automatico", 0)
        ap, arquivo = self.aprovar_email()
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"]), (1, "envio_automatico_desligado"))
        self.assertEqual((self.servidor.envios, self.contar_envios()), ([], 0))

    def test_primeiro_envio_real_exige_teste_liberado(self):
        ap, arquivo = self.aprovar_email()
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"]), (1, "teste_pendente"))
        self.assertEqual(self.servidor.envios, [])

    def test_teste_depois_envio_real_pela_caixa_do_agente(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["estado"], r["de"], r["para"]), (0, "enviado", "willow@plow.co", PARA), r)
        caminho, corpo, auth = self.servidor.envios[-1]
        self.assertEqual(caminho, "/v1/email-lines/ln_e_willow/messages")
        self.assertEqual(auth, "Bearer plow_teste")
        self.assertEqual(corpo["to"], [PARA])
        self.assertEqual(corpo["subject"], "Canal de ética na Acme")
        self.assertTrue(corpo["body"].startswith("Olá, Maria."))
        self.assertNotIn("Assunto:", corpo["body"])
        self.assertEqual(self.sql("SELECT estado, id_provedor FROM envios WHERE teste = 0"), [("enviado", "gm_1")])

    def test_sem_assunto_recusa_antes_de_reservar(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email(texto="Olá, Maria.\n\nResponda PARAR para não receber mais.\n")
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"]), (1, "assunto_ausente"))
        self.assertEqual(self.contar_envios(), 0)

    def test_texto_mudado_nao_sai(self):
        self.liberar_por_email()
        ap, _ = self.aprovar_email()
        codigo, r = self.enviar(ap, self.texto(TEXTO.replace("Maria", "Mariana")))
        self.assertEqual((codigo, r["motivo"]), (1, "texto_diferente"))
        self.assertEqual(len(self.servidor.envios), 1)  # só o teste

    def test_nunca_contatar_bloqueia_antes_da_api(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        self.ok("nunca-contatar", "add", "--tipo", "dominio", "--chave", "acme.com.br", "--motivo", "cliente", "--por", DONO)
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"]), (1, "nunca_contatar"))
        self.assertEqual(len(self.servidor.envios), 1)

    def test_erro_do_servidor_vira_incerto_e_nao_reenvia(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        self.servidor.resposta = (502, {"detail": "bad gateway"})
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"], r["estado"]), (1, "entrega_incerta", "incerto"), r)
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"]), (1, "envio_existente"))
        self.assertEqual(len(self.servidor.envios), 2)  # teste + uma tentativa

    def test_conexao_caida_vira_incerto(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        self.servidor.resposta = (None, None)
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["estado"]), (1, "incerto"), r)

    def test_aceite_desconhecido_vira_incerto(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        self.servidor.resposta = (201, {"status": "acceptance_unknown", "message_id": None})
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["estado"]), (1, "incerto"), r)

    def test_recusa_da_plow_vira_falhou(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        self.servidor.resposta = (403, {"error": {"code": "email_line_owner_not_visible"}})
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"], r["estado"]), (1, "envio_falhou", "falhou"), r)
        self.assertIn("email_line_owner_not_visible", r["erro"])

    def test_sem_credencial_nao_reserva(self):
        ap, arquivo = self.aprovar_email()
        codigo, r = self.cli("enviar", "--aprovacao", ap, "--texto-arquivo", arquivo,
                             env={"PLOW_AGENT_TOKEN": "", "PLOW_API_BASE": self.env["PLOW_API_BASE"]})
        self.assertEqual((codigo, r["motivo"]), (1, "sem_credencial"))
        self.assertEqual(self.contar_envios(), 0)


if __name__ == "__main__":
    unittest.main()
