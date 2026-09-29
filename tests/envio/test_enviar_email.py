"""Testes do `milo-envio enviar`: livro + API de e-mail da Plow, contra um servidor falso local.

Rodar da raiz do repositório:
    python -m unittest discover -s tests/envio -v
"""
import http.server
import json
import subprocess
import sys
import threading
import unittest

from test_milo_envio import DONO, PARA, RAIZ, Base

TEXTO = "Para: {para}\nAssunto: Canal de ética na Acme\n\nOlá, Maria.\n\nSou o Milo, assistente de IA da Prossigo.\nResponda PARAR para não receber mais.\n"
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
            if getattr(self.server, "on_agents_me", None):
                self.server.on_agents_me()
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
        if getattr(self.server, "on_post", None):
            self.server.on_post()
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
        arquivo = self.texto(texto.replace("{para}", para))
        return self.aprovar(conta=conta, chat=None, para=para, texto=arquivo), arquivo

    def enviar(self, ap, arquivo, *extra):
        return self.cli("enviar", "--aprovacao", ap, "--texto-arquivo", arquivo, *extra, env=self.env)

    def liberar_por_email(self):
        ap, arquivo = self.aprovar_email(conta="teste-instalacao", para="lead@teste-instalacao.com")
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

    def test_teste_so_vai_para_email_interno_configurado(self):
        ap, arquivo = self.aprovar_email()
        for destino, motivo in ((PARA, "teste_para_destinatario"),
                                ("outro@outra-empresa.com", "teste_para_nao_autorizado")):
            with self.subTest(destino=destino):
                codigo, r = self.enviar(ap, arquivo, "--teste", "--para", destino)
                self.assertEqual((codigo, r.get("motivo")), (1, motivo), r)
        self.assertEqual((self.servidor.envios, self.sql("SELECT count(*) FROM envios")[0][0]), ([], 0))

    def test_teste_recusa_email_interno_bloqueado(self):
        self.ok("nunca-contatar", "add", "--tipo", "email", "--chave", CARLA,
                "--motivo", "bloqueado", "--por", DONO)
        ap, arquivo = self.aprovar_email()
        codigo, r = self.enviar(ap, arquivo, "--teste", "--para", CARLA)
        self.assertEqual((codigo, r.get("motivo")), (1, "nunca_contatar"), r)
        self.assertEqual(self.servidor.envios, [])

    def test_teste_recusa_sem_email_interno_configurado(self):
        self.sql("UPDATE config SET valor = '' WHERE chave = 'email_teste'")
        ap, arquivo = self.aprovar_email()
        codigo, r = self.enviar(ap, arquivo, "--teste", "--para", CARLA)
        self.assertEqual((codigo, r.get("motivo")), (1, "email_teste_nao_configurado"), r)
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
        self.assertNotIn("Para:", corpo["body"])
        self.assertEqual(self.sql("SELECT estado, id_provedor FROM envios WHERE teste = 0"), [("enviado", "gm_1")])

    def test_sem_assunto_recusa_antes_de_aprovar(self):
        # O enviar recusaria esse cabeçalho: a recusa vem antes do código, não depois do ok.
        arquivo = self.texto(f"Para: {PARA}\nOlá, Maria.\n\nResponda PARAR para não receber mais.\n")
        self.recusa("assunto_ausente", "apresentar", "--conta", "acme", "--versao", 1,
                    "--texto-arquivo", arquivo, "--para", PARA)
        self.recusa("assunto_ausente", *self.args_aprovar(chat=None, texto=arquivo))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_linha_em_branco_entre_para_e_assunto_sai_igual(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email(texto=TEXTO.replace("Para: {para}\n", "Para: {para}\n\n"))
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["estado"]), (0, "enviado"), r)
        _, corpo, _ = self.servidor.envios[-1]
        self.assertEqual(corpo["subject"], "Canal de ética na Acme")
        self.assertTrue(corpo["body"].startswith("Olá, Maria."))

    def test_sem_para_no_rascunho_recusa_antes_de_reservar(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email(texto=TEXTO.replace("Para: {para}\n", ""))
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["motivo"]), (1, "para_ausente"))
        self.assertEqual(self.contar_envios(), 0)

    def test_aprovar_para_outro_destinatario_que_o_do_rascunho_recusa(self):
        arquivo = self.texto(TEXTO.replace("{para}", PARA))
        r = self.recusa("destinatario_diferente_do_rascunho",
                        *self.args_aprovar(chat=None, para="outra@acme.com.br", texto=arquivo))
        self.assertEqual(r["para_rascunho"], PARA)
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_aprovacao_antiga_nao_vale_para_nova_versao(self):
        v1 = self.texto(TEXTO.replace("{para}", PARA))
        mostrado_v1 = self.ok("apresentar", "--conta", "acme", "--versao", 1,
                             "--texto-arquivo", v1, "--para", PARA)
        novo_para = "pedro@acme.com.br"
        v2 = self.texto(TEXTO.replace("{para}", novo_para))
        mostrado_v2 = self.ok("apresentar", "--conta", "acme", "--versao", 2,
                             "--texto-arquivo", v2, "--para", novo_para)
        self.assertEqual(mostrado_v2["texto"], TEXTO.replace("{para}", novo_para).strip())
        self.assertNotEqual(mostrado_v1["codigo"], mostrado_v2["codigo"])
        for resposta in ("pode mandar", "APROVO " + mostrado_v1["codigo"]):
            self.recusa("confirmacao_da_versao_ausente",
                        *self.args_aprovar(versao=2, chat=None, para=novo_para,
                                           texto=v2, resposta=resposta))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)
        self.ok(*self.args_aprovar(versao=2, chat=None, para=novo_para,
                                   texto=v2, resposta="APROVO " + mostrado_v2["codigo"]))

    def test_assunto_e_corpo_mudados_exigem_codigo_novo(self):
        v1 = self.texto(TEXTO.replace("{para}", PARA))
        antigo = self.ok("apresentar", "--conta", "acme", "--versao", 1,
                         "--texto-arquivo", v1, "--para", PARA)["codigo"]
        for versao, texto in ((2, TEXTO.replace("Canal de ética", "Conversa")),
                              (3, TEXTO.replace("Olá, Maria.", "Olá, Pedro."))):
            novo = self.texto(texto.replace("{para}", PARA))
            self.recusa("confirmacao_da_versao_ausente",
                        *self.args_aprovar(versao=versao, chat=None, texto=novo,
                                           resposta="APROVO " + antigo))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_rascunho_antigo_sem_para_nao_e_apresentado(self):
        antigo = self.texto(TEXTO.replace("Para: {para}\n", ""))
        self.recusa("para_ausente", "apresentar", "--conta", "acme", "--versao", 1,
                    "--texto-arquivo", antigo, "--para", PARA)

    def test_endereco_com_sinais_ou_ponto_final_e_recusado(self):
        # "<maria@acme.com.br>" teria o domínio "acme.com.br>": furaria "nunca contatar" e a
        # regra de um só primeiro contato por endereço.
        self.ok("nunca-contatar", "add", "--tipo", "dominio", "--chave", "acme.com.br",
                "--motivo", "pediu para parar", "--por", DONO)
        for para in ("<maria@acme.com.br>", "maria@acme.com.br.", "maria@acme.com.br>", "maria@@acme.com.br"):
            with self.subTest(para=para):
                arquivo = self.texto(TEXTO.replace("{para}", para))
                self.recusa("email_invalido", "apresentar", "--conta", "acme", "--versao", 1,
                            "--texto-arquivo", arquivo, "--para", para)
                self.recusa("email_invalido", *self.args_aprovar(chat=None, para=para, texto=arquivo))
        self.recusa("email_invalido", "nunca-contatar", "add", "--tipo", "email", "--chave", "<maria@acme.com.br>",
                    "--motivo", "PARAR", "--por", DONO)
        self.recusa("email_invalido", "config", "set", "--chave", "email_teste", "--valor", "<carla@prossigo.com.br>",
                    "--por", DONO)
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_aprovo_aceita_mencao_e_pontuacao(self):
        arquivo = self.texto(TEXTO.replace("{para}", PARA))
        codigo = self.ok("apresentar", "--conta", "acme", "--versao", 1, "--texto-arquivo", arquivo,
                         "--para", PARA)["codigo"]
        for resposta in (f"APROVO {codigo}.", f"@Milo APROVO {codigo}", f"aprovo  {codigo.lower()}",
                         f"APROVO: {codigo} 👍", f"APROVO {codigo} @Milo", f"  *APROVO {codigo}*  "):
            with self.subTest(resposta=resposta):
                self.ok(*self.args_aprovar(chat=None, texto=arquivo, resposta=resposta))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 1)

    def test_approve_em_ingles_vale_como_aprovo(self):
        # Quem conversa em inglês pode receber o pedido como "reply APPROVE <code>".
        arquivo = self.texto(TEXTO.replace("{para}", PARA))
        codigo = self.ok("apresentar", "--conta", "acme", "--versao", 1, "--texto-arquivo", arquivo,
                         "--para", PARA)["codigo"]
        for resposta in (f"APPROVE {codigo}", f"@Milo approve {codigo.lower()}.", f"APPROVE: {codigo} 👍",
                         f"APPROVE {codigo} @Milo"):
            with self.subTest(resposta=resposta):
                self.ok(*self.args_aprovar(chat=None, texto=arquivo, resposta=resposta))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 1)

    def test_aprovo_recusa_o_que_nao_e_so_o_codigo(self):
        arquivo = self.texto(TEXTO.replace("{para}", PARA))
        codigo = self.ok("apresentar", "--conta", "acme", "--versao", 1, "--texto-arquivo", arquivo,
                         "--para", PARA)["codigo"]
        outra = self.texto(TEXTO.replace("{para}", "pedro@acme.com.br"))
        outro_codigo = self.ok("apresentar", "--conta", "acme", "--versao", 1, "--texto-arquivo", outra,
                               "--para", "pedro@acme.com.br")["codigo"]
        self.assertNotEqual(codigo, outro_codigo)
        for resposta in ("pode mandar", "ok", "👍", f"não APROVO {codigo}", f"APROVO {codigo} mas troca o assunto",
                         f"APROVO {codigo}\nnão, espera", f"APROVO {codigo[:-1]}", f"APROVO {codigo}0",
                         f"Se estiver tudo certo, responda APROVO {codigo}.",
                         "approve", f"APPROVED {codigo}", f"not APPROVE {codigo}", f"APPROVE {outro_codigo}",
                         f"APROVO {outro_codigo}", f"APROVO {codigo} APROVO {codigo}",
                         f"APROVO {codigo} APPROVE {codigo}", f"APPROVE {codigo} APPROVE {codigo}", f"APPROVE {codigo} but change the subject",
                         f"If everything looks right, reply APPROVE {codigo}."):
            with self.subTest(resposta=resposta):
                self.recusa("confirmacao_da_versao_ausente",
                            *self.args_aprovar(chat=None, texto=arquivo, resposta=resposta))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_quem_nao_aprova_e_recusado_por_permissao_antes_do_codigo(self):
        arquivo = self.texto(TEXTO.replace("{para}", PARA))
        self.recusa("aprovador_sem_permissao", *self.args_aprovar(chat=None, texto=arquivo, aprovador="mem_diego",
                                                                  canal="grupo", resposta="pode mandar"))
        eventos = self.sql("SELECT ator, motivo FROM eventos WHERE tipo = 'aprovar_recusado'")
        self.assertEqual(eventos, [("mem_diego", "aprovador_sem_permissao")])

    def test_criar_v2_invalida_aprovacao_da_v1(self):
        criador = RAIZ / "skills/redigir-abordagem/scripts/criar-rascunho.py"
        def criar(corpo):
            origem = self.texto(corpo)
            p = subprocess.run([sys.executable, str(criador), "--mesa", str(self.dir),
                                "--conta", "acme", "--texto-arquivo", origem],
                               capture_output=True, text=True, check=True)
            return json.loads(p.stdout)["arquivo"]
        v1 = criar(TEXTO.replace("{para}", PARA))
        ap = self.aprovar(conta="acme", versao=1, chat=None, texto=v1)
        v2 = criar(TEXTO.replace("{para}", "pedro@acme.com.br"))
        self.recusa("versao_substituida", *self.args_preparar(ap, v1, ("--executor", "humano")))
        self.recusa("versao_substituida", "apresentar", "--conta", "acme", "--versao", 1,
                    "--texto-arquivo", v1, "--para", PARA)
        self.assertEqual(self.ok("apresentar", "--conta", "acme", "--versao", 2,
                                 "--texto-arquivo", v2, "--para", "pedro@acme.com.br")["versao"], 2)

    def test_rascunho_legacy_sem_para_na_mesa_nao_e_aprovado(self):
        criador = RAIZ / "skills/redigir-abordagem/scripts/criar-rascunho.py"
        origem = self.texto(TEXTO.replace("Para: {para}\n", ""))
        p = subprocess.run([sys.executable, str(criador), "--mesa", str(self.dir),
                            "--conta", "acme", "--texto-arquivo", origem],
                           capture_output=True, text=True, check=True)
        arquivo = json.loads(p.stdout)["arquivo"]
        self.recusa("para_ausente", *self.args_aprovar(chat=None, texto=arquivo))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_envio_usa_texto_conferido_na_reserva(self):
        self.liberar_por_email()
        aprovado = TEXTO.replace("{para}", PARA)
        ap, arquivo = self.aprovar_email(texto=aprovado)
        from pathlib import Path
        caminho = Path(arquivo)
        caminho.write_text(aprovado.replace("Olá, Maria.", "TEXTO NÃO APROVADO."), encoding="utf-8")
        self.servidor.on_agents_me = lambda: caminho.write_text(aprovado, encoding="utf-8")
        codigo, r = self.enviar(ap, arquivo)
        self.assertEqual((codigo, r["estado"]), (0, "enviado"), r)
        self.assertIn("Olá, Maria.", self.servidor.envios[-1][1]["body"])
        self.assertNotIn("TEXTO NÃO APROVADO", self.servidor.envios[-1][1]["body"])

    def test_nova_versao_espera_envio_em_andamento(self):
        self.liberar_por_email()
        criador = RAIZ / "skills/redigir-abordagem/scripts/criar-rascunho.py"
        def comando_criar(corpo):
            origem = self.texto(corpo)
            return [sys.executable, str(criador), "--mesa", str(self.dir),
                    "--conta", "acme", "--texto-arquivo", origem]
        v1 = json.loads(subprocess.check_output(comando_criar(TEXTO.replace("{para}", PARA))))["arquivo"]
        ap = self.aprovar(conta="acme", versao=1, chat=None, texto=v1)
        entrou = threading.Event()
        soltar = threading.Event()
        self.servidor.on_post = lambda: (entrou.set(), soltar.wait(5))
        resultado = []
        worker = threading.Thread(target=lambda: resultado.append(self.enviar(ap, v1)))
        worker.start()
        criacao = None
        try:
            self.assertTrue(entrou.wait(5), "envio não chegou à API falsa")
            criacao = subprocess.Popen(comando_criar(TEXTO.replace("{para}", "pedro@acme.com.br")),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            threading.Event().wait(0.2)
            self.assertIsNone(criacao.poll(), "v2 foi criada enquanto o envio segurava o lock")
        finally:
            soltar.set()
            worker.join(10)
            if criacao is not None:
                out, err = criacao.communicate(timeout=10)
                self.assertEqual(criacao.returncode, 0, (out, err))
        self.assertEqual(resultado[0][0], 0, resultado)

    def test_nunca_contatar_espera_envio_em_andamento(self):
        self.liberar_por_email()
        ap, arquivo = self.aprovar_email()
        entrou = threading.Event()
        soltar = threading.Event()
        self.servidor.on_post = lambda: (entrou.set(), soltar.wait(5))
        resultado = []
        worker = threading.Thread(target=lambda: resultado.append(self.enviar(ap, arquivo)))
        worker.start()
        exclusao = None
        try:
            self.assertTrue(entrou.wait(5), "envio não chegou à API falsa")
            exclusao = subprocess.Popen(self.comando(["nunca-contatar", "add", "--tipo", "email",
                                                       "--chave", PARA, "--motivo", "PARAR", "--por", DONO]),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            threading.Event().wait(0.2)
            self.assertIsNone(exclusao.poll(), "exclusão foi gravada durante o envio em voo")
        finally:
            soltar.set()
            worker.join(10)
            if exclusao is not None:
                out, err = exclusao.communicate(timeout=10)
                self.assertEqual(exclusao.returncode, 0, (out, err))
        self.assertEqual(resultado[0][0], 0, resultado)
        self.assertEqual(self.sql("SELECT chave FROM nunca_contatar WHERE chave = ?", (PARA,)), [(PARA,)])

    def test_texto_mudado_nao_sai(self):
        self.liberar_por_email()
        ap, _ = self.aprovar_email()
        codigo, r = self.enviar(ap, self.texto(TEXTO.replace("{para}", PARA).replace("Maria", "Mariana")))
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
