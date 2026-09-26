"""Testes do milo-envio, contra a interface de docs/milo-envio.md.

Rodar da raiz do repositório:
    python -m unittest discover -s tests/envio -v

Cada chamada roda o script num processo novo, como a skill faz. O tempo não é
controlado por variável de ambiente: testes da janela de 24 h gravam
`tentado_em` antigo direto no banco.
"""
import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "executar-envio" / "scripts" / "milo-envio.py"
DONO = "plow-owner"
CHAT = "cht_acme1"
PARA = "maria@acme.com.br"
TEXTO = "Olá, Maria.\n\nSou o Milo, assistente de IA da Prossigo.\nResponda PARAR para não receber mais.\n"


def iso(momento):
    return momento.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def agora():
    return datetime.datetime.now(datetime.timezone.utc)


class Base(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), f"script ausente: {SCRIPT}")
        self.dir = Path(tempfile.mkdtemp(prefix="milo-envio-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.db = str(self.dir / "envios.sqlite")
        self.arquivos = 0
        self.ok("config", "get")
        self.ok("config", "set", "--chave", "limite_diario", "--valor", 10, "--por", DONO)

    # --- chamadas ao script ---

    def comando(self, args, db=True):
        banco = self.db if db is True else db
        return [sys.executable, str(SCRIPT)] + (["--db", banco] if banco else []) + [str(a) for a in args]

    def ambiente(self, env=None):
        base = {k: v for k, v in os.environ.items() if k not in ("MILO_MESA", "MILO_ENVIO_PAUSA_TESTE")}
        base.update(env or {})
        return base

    def ler(self, codigo, stdout, stderr):
        linhas = stdout.decode("utf-8").splitlines()
        self.assertEqual(len(linhas), 1, f"a saída deve ser uma linha JSON; stdout={stdout!r} stderr={stderr!r}")
        return codigo, json.loads(linhas[0])

    def cli(self, *args, db=True, env=None):
        p = subprocess.run(self.comando(args, db), capture_output=True, env=self.ambiente(env), timeout=60)
        return self.ler(p.returncode, p.stdout, p.stderr)

    def cli_paralelo(self, lista, env=None):
        procs = [subprocess.Popen(self.comando(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=self.ambiente(env)) for args in lista]
        resultados = []
        for p in procs:
            out, err = p.communicate(timeout=60)
            resultados.append(self.ler(p.returncode, out, err))
        return resultados

    def ok(self, *args, **kw):
        codigo, r = self.cli(*args, **kw)
        self.assertEqual((codigo, r.get("ok")), (0, True), r)
        return r

    def recusa(self, motivo, *args, codigo=1, **kw):
        c, r = self.cli(*args, **kw)
        self.assertEqual((c, r.get("ok"), r.get("motivo")), (codigo, False, motivo), r)
        return r

    # --- apoio ---

    def texto(self, conteudo=TEXTO):
        self.arquivos += 1
        caminho = self.dir / f"rascunho-{self.arquivos}.txt"
        caminho.write_bytes(conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8"))
        return str(caminho)

    def args_aprovar(self, conta="acme", versao=1, texto=None, chat=CHAT, para=PARA, aprovador=DONO, canal="dm"):
        args = ["aprovar", "--conta", conta, "--versao", versao, "--texto-arquivo", texto or self.texto(),
                "--para", para, "--aprovador", aprovador, "--canal", canal]
        return args + (["--chat", chat] if chat is not None else [])

    def aprovar(self, **kw):
        return self.ok(*self.args_aprovar(**kw))["aprovacao_id"]

    def args_preparar(self, aprovacao, texto=None, extra=()):
        return ["preparar", "--aprovacao", aprovacao, "--texto-arquivo", texto or self.texto(), *extra]

    def sql(self, consulta, params=()):
        con = sqlite3.connect(self.db, timeout=5, isolation_level=None)
        try:
            return con.execute(consulta, params).fetchall()
        finally:
            con.close()

    def contar_envios(self):
        """Envios reais; o envio de teste da instalação não conta."""
        return self.sql("SELECT count(*) FROM envios WHERE teste = 0")[0][0]

    def enviar_teste(self):
        ap = self.aprovar(conta="teste-instalacao", chat="cht_carla", para="carla@prossigo.com.br")
        envio = self.ok(*self.args_preparar(ap, extra=("--teste", "--chat", "cht_carla", "--para", "carla@prossigo.com.br")))
        return envio["envio_id"]

    def liberar_teste(self):
        """Fluxo real do primeiro envio: teste para a aprovadora, concluir, ok real."""
        envio = self.enviar_teste()
        self.concluir(envio, "enviado", "--id-provedor", "msg_teste")
        self.ok("liberar", "--envio", envio, "--aprovador", DONO)

    def concluir(self, envio, resultado, *extra):
        return self.ok("concluir", "--envio", envio, "--resultado", resultado, *extra)

    def preparar(self, ap, *extra):
        return self.ok(*self.args_preparar(ap, extra=extra))["envio_id"]

    def config(self, chave, valor):
        self.ok("config", "set", "--chave", chave, "--valor", valor, "--por", DONO)

    def cadastrar_carla(self):
        self.ok("aprovadores", "add", "--uid", "mem_carla", "--nome", "Carla", "--enviar", "--por", DONO)


class TestInterface(Base):
    def test_banco_novo_comeca_com_limite_zero(self):
        novo = str(self.dir / "novo.sqlite")
        codigo, resposta = self.cli("config", "get", "--chave", "limite_diario", db=novo)
        self.assertEqual((codigo, resposta["valor"]), (0, "0"))

    def test_saida_uma_linha_json_e_codigos_0_1_2_3(self):
        self.ok("config", "get")
        self.recusa("aprovador_sem_permissao", *self.args_aprovar(aprovador="mem_diego"))
        self.recusa("uso_invalido", "aprovar", codigo=2)
        self.recusa("erro_banco", "config", "get", db=str(self.dir), codigo=3)

    def test_pausa_de_teste_tem_teto_e_ignora_invalido(self):
        self.liberar_teste()
        for i, (valor, maximo) in enumerate((("abc", 1.5), ("nan", 1.5), ("-3", 1.5), ("100", 4.0))):
            with self.subTest(valor=valor):
                ap = self.aprovar(conta=f"p{i}", chat=f"cht_p{i}", para=f"x@p{i}.com")
                inicio = datetime.datetime.now()
                self.ok(*self.args_preparar(ap), env={"MILO_ENVIO_PAUSA_TESTE": valor})
                self.assertLess((datetime.datetime.now() - inicio).total_seconds(), maximo)

    def test_sem_banco_recusa(self):
        self.recusa("sem_banco", "config", "get", db=None, codigo=2)

    def test_estado_sobrevive_a_novo_processo(self):
        ap = self.ok(*self.args_aprovar(), db=None, env={"MILO_MESA": str(self.dir)})["aprovacao_id"]
        self.liberar_teste()
        r = self.ok(*self.args_preparar(ap))
        self.assertEqual(r["estado"], "reservado")


class TestAprovacao(Base):
    def test_aprovar_dono_na_dm_grava_aprovacao(self):
        r = self.ok(*self.args_aprovar())
        self.assertIsInstance(r["aprovacao_id"], int)
        linha = self.sql("SELECT conta, versao, chat_uid, para, aprovador_id, canal FROM aprovacoes")
        self.assertEqual(linha, [("acme", 1, CHAT, PARA, DONO, "dm")])

    def test_aprovar_recusa_aprovador_desconhecido(self):
        self.recusa("aprovador_sem_permissao", *self.args_aprovar(aprovador="mem_diego", canal="grupo"))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)
        eventos = self.sql("SELECT ator, motivo FROM eventos WHERE motivo = 'aprovador_sem_permissao'")
        self.assertEqual(eventos, [("mem_diego", "aprovador_sem_permissao")])

    def test_aprovar_so_dono_recusa_aprovador_cadastrado(self):
        self.cadastrar_carla()
        self.recusa("somente_dono", *self.args_aprovar(aprovador="mem_carla", canal="grupo"))

    def test_aprovar_so_dono_recusa_dono_fora_da_dm(self):
        self.recusa("somente_dono", *self.args_aprovar(canal="grupo"))

    def test_aprovar_aceita_cadastrado_com_so_dono_0(self):
        self.cadastrar_carla()
        self.config("aprovacao_so_dono", 0)
        self.aprovar(aprovador="mem_carla", canal="grupo")

    def test_aprovar_idempotente_devolve_mesmo_id(self):
        primeiro = self.ok(*self.args_aprovar())
        segundo = self.ok(*self.args_aprovar())
        self.assertEqual(segundo["aprovacao_id"], primeiro["aprovacao_id"])
        self.assertTrue(segundo.get("existente"))
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 1)

    def test_aprovar_mesma_versao_texto_diferente_e_conflito(self):
        self.aprovar()
        self.recusa("versao_conflitante", *self.args_aprovar(texto=self.texto(TEXTO + "PS: outra coisa.\n")))
        self.recusa("versao_conflitante", *self.args_aprovar(chat="cht_outro"))

    def test_aprovar_valida_entrada(self):
        casos = [
            ("chat_invalido", 1, dict(chat="acme")),
            ("email_invalido", 1, dict(para="maria")),
            ("texto_vazio", 1, dict(texto=self.texto("  \n\n\t\n"))),
            ("texto_invalido", 1, dict(texto=self.texto(b"\xff\xfe\x00ol\xe1"))),
            ("texto_inexistente", 1, dict(texto=str(self.dir / "nao-existe.txt"))),
            ("uso_invalido", 2, dict(conta="Acme Log")),
            ("uso_invalido", 2, dict(versao="x")),
        ]
        for motivo, codigo, kw in casos:
            with self.subTest(motivo=motivo, kw=kw):
                self.recusa(motivo, *self.args_aprovar(**kw), codigo=codigo)
        self.assertEqual(self.sql("SELECT count(*) FROM aprovacoes")[0][0], 0)

    def test_preparar_recusa_aprovacao_inexistente(self):
        self.recusa("aprovacao_inexistente", *self.args_preparar(999))

    def test_preparar_recusa_aprovador_que_perdeu_permissao(self):
        self.cadastrar_carla()
        self.config("aprovacao_so_dono", 0)
        self.liberar_teste()
        removida = self.aprovar(aprovador="mem_carla", canal="grupo")
        so_dono = self.aprovar(conta="beta", chat="cht_beta1", para="joao@beta.com", aprovador="mem_carla", canal="grupo")
        self.ok("aprovadores", "remove", "--uid", "mem_carla", "--por", DONO)
        self.recusa("aprovador_sem_permissao", *self.args_preparar(removida))
        self.cadastrar_carla()
        self.config("aprovacao_so_dono", 1)
        self.recusa("somente_dono", *self.args_preparar(so_dono))
        self.assertEqual(self.contar_envios(), 0)

    def test_aprovadores_add_e_config_set_exigem_plow_owner(self):
        self.recusa("somente_dono", "aprovadores", "add", "--uid", "mem_diego", "--nome", "Diego", "--enviar", "--por", "mem_carla")
        self.recusa("somente_dono", "config", "set", "--chave", "limite_diario", "--valor", 99, "--por", "mem_carla")
        self.assertEqual(self.ok("config", "get", "--chave", "limite_diario")["valor"], "10")
        self.assertEqual(self.sql("SELECT count(*) FROM aprovadores WHERE identificador = 'mem_diego'")[0][0], 0)

    def test_plow_owner_nao_pode_ser_alterado_nem_removido(self):
        self.recusa("dono_imutavel", "aprovadores", "add", "--uid", DONO, "--nome", "Outro", "--por", DONO)
        self.recusa("dono_imutavel", "aprovadores", "remove", "--uid", DONO, "--por", DONO)
        self.assertEqual(self.sql("SELECT pode_enviar, pode_regras FROM aprovadores WHERE identificador = ?", (DONO,)), [(1, 1)])


class TestTexto(Base):
    def setUp(self):
        super().setUp()
        self.liberar_teste()

    def preparar_com(self, aprovado, enviado):
        ap = self.aprovar(texto=self.texto(aprovado))
        return self.cli(*self.args_preparar(ap, self.texto(enviado)))

    def test_preparar_recusa_texto_com_uma_palavra_diferente(self):
        ap = self.aprovar()
        self.recusa("texto_diferente", *self.args_preparar(ap, self.texto(TEXTO.replace("Maria", "Mario"))))
        self.assertEqual(self.contar_envios(), 0)

    def test_normalizacao_crlf_igual_a_lf(self):
        codigo, r = self.preparar_com("linha um\nlinha dois\n", "linha um\r\nlinha dois\r\n")
        self.assertEqual((codigo, r["ok"]), (0, True), r)

    def test_normalizacao_espaco_no_fim_da_linha_ignorado(self):
        codigo, r = self.preparar_com("linha um\nlinha dois\n", "linha um  \nlinha dois\t\n")
        self.assertEqual((codigo, r["ok"]), (0, True), r)

    def test_normalizacao_espaco_duplo_no_meio_conta_como_diferenca(self):
        codigo, r = self.preparar_com("linha um\n", "linha  um\n")
        self.assertEqual((codigo, r.get("motivo")), (1, "texto_diferente"), r)

    def test_normalizacao_ignora_bom_e_linhas_em_branco_nas_bordas(self):
        codigo, r = self.preparar_com("linha um\nlinha dois", "﻿\n\n   \nlinha um\nlinha dois\n\n\n")
        self.assertEqual((codigo, r["ok"]), (0, True), r)

    def test_normalizacao_nfc_composto_igual_a_decomposto(self):
        codigo, r = self.preparar_com("Olá, você\n", "Olá, você\n")
        self.assertEqual((codigo, r["ok"]), (0, True), r)

    def test_preparar_devolve_chat_e_corpo_normalizado(self):
        codigo, r = self.preparar_com("﻿Oi, Maria.  \r\n\r\nAté logo.\r\n\r\n", "Oi, Maria.\n\nAté logo.\n")
        self.assertEqual(codigo, 0, r)
        self.assertEqual((r["chat"], r["para"], r["corpo"]), (CHAT, PARA, "Oi, Maria.\n\nAté logo."))
        self.assertEqual((r["estado"], r["teste"], r["executor"]), ("reservado", False, "milo"))


class TestConferencias(Base):
    def nunca(self, tipo, chave, por=DONO, motivo="cliente"):
        return self.ok("nunca-contatar", "add", "--tipo", tipo, "--chave", chave, "--motivo", motivo, "--por", por)

    def test_nunca_contatar_entre_aprovar_e_preparar_bloqueia(self):
        self.liberar_teste()
        ap = self.aprovar()
        self.nunca("email", "MARIA@acme.com.br ")
        self.recusa("nunca_contatar", *self.args_preparar(ap))
        self.assertEqual(self.contar_envios(), 0)

    def test_aprovar_recusa_quem_ja_esta_em_nunca_contatar(self):
        self.nunca("dominio", "acme.com.br")
        self.recusa("nunca_contatar", *self.args_aprovar())

    def test_dominio_bloqueia_subdominio_mas_nao_sufixo_solto(self):
        self.nunca("dominio", "acme.com")
        self.recusa("nunca_contatar", *self.args_aprovar(para="ana@vendas.acme.com"))
        self.recusa("nunca_contatar", *self.args_aprovar(para="ana@acme.com"))
        self.aprovar(conta="notacme", chat="cht_nota1", para="ana@notacme.com")

    def test_empresa_casa_por_slug(self):
        self.nunca("empresa", "Acme Logística")
        self.recusa("nunca_contatar", *self.args_aprovar(conta="acme-logistica"))
        self.aprovar(conta="acme")

    def test_nunca_contatar_chat_bloqueia_chat_uid(self):
        self.nunca("chat", CHAT)
        self.recusa("nunca_contatar", *self.args_aprovar())
        self.aprovar(chat="cht_outro")

    def test_preparar_real_recusa_teste_pendente(self):
        ap = self.aprovar()
        self.recusa("teste_pendente", *self.args_preparar(ap))
        self.assertEqual(self.contar_envios(), 0)

    def test_preparar_teste_pula_nunca_contatar_e_limite(self):
        ap = self.aprovar()
        self.config("limite_diario", 0)
        self.nunca("dominio", "acme.com.br")
        r = self.ok(*self.args_preparar(ap, extra=("--teste", "--chat", "cht_carla", "--para", "carla@prossigo.com.br")))
        self.assertEqual((r["teste"], r["chat"], r["para"]), (True, "cht_carla", "carla@prossigo.com.br"))
        self.liberar_teste()
        self.recusa("nunca_contatar", *self.args_preparar(ap))

    def test_limite_recusa_o_11o_envio_real_em_24h(self):
        self.liberar_teste()
        for i in range(1, 11):
            ap = self.aprovar(conta=f"c{i}", chat=f"cht_c{i}", para=f"x@c{i}.com")
            self.ok(*self.args_preparar(ap))
        ap = self.aprovar(conta="c11", chat="cht_c11", para="x@c11.com")
        r = self.recusa("limite_diario", *self.args_preparar(ap))
        self.assertEqual(r.get("limite"), 10)
        self.assertEqual(self.contar_envios(), 10)

    def test_limite_ignora_teste_falhou_bloqueado_e_mais_de_24h(self):
        self.config("limite_diario", 1)
        self.liberar_teste()
        ap = self.aprovar(conta="t0", chat="cht_t0", para="x@t0.com")
        self.preparar(ap, "--teste", "--chat", "cht_carla", "--para", "carla@prossigo.com.br")
        falhou = self.preparar(self.aprovar(conta="c1", chat="cht_c1", para="x@c1.com"))
        self.concluir(falhou, "falhou", "--erro", "Plow HTTP 403")
        bloqueado = self.preparar(self.aprovar(conta="c2", chat="cht_c2", para="x@c2.com"))
        self.concluir(bloqueado, "incerto")
        self.ok("resolver", "--envio", bloqueado, "--resultado", "bloqueado", "--aprovador", DONO)
        antigo = self.preparar(self.aprovar(conta="c3", chat="cht_c3", para="x@c3.com"))
        self.concluir(antigo, "enviado", "--id-provedor", "msg_c3")
        # Sem comando para voltar no tempo: a idade entra direto no banco.
        self.sql("UPDATE envios SET tentado_em = ? WHERE id = ?", (iso(agora() - datetime.timedelta(hours=25)), antigo))
        ap = self.aprovar(conta="c4", chat="cht_c4", para="x@c4.com")
        self.ok(*self.args_preparar(ap))
        ap = self.aprovar(conta="c5", chat="cht_c5", para="x@c5.com")
        self.recusa("limite_diario", *self.args_preparar(ap))

    def test_destinatario_ja_contatado_com_outro_texto(self):
        self.liberar_teste()
        self.ok(*self.args_preparar(self.aprovar(versao=1)))
        v2 = self.aprovar(versao=2, texto=self.texto("Outro texto para a Maria.\n"))
        self.recusa("destinatario_ja_contatado", *self.args_preparar(v2, self.texto("Outro texto para a Maria.\n")))
        v3 = self.aprovar(versao=3, texto=self.texto("Terceiro texto.\n"), chat="cht_outro")
        self.recusa("destinatario_ja_contatado", *self.args_preparar(v3, self.texto("Terceiro texto.\n")))


class TestDuplicacao(Base):
    def setUp(self):
        super().setUp()
        self.liberar_teste()

    def test_repeticao_de_turno_preparar_devolve_envio_existente(self):
        enviado = self.aprovar(versao=1)
        incerto = self.aprovar(conta="beta", chat="cht_beta1", para="joao@beta.com")
        envios = {enviado: self.preparar(enviado), incerto: self.preparar(incerto)}
        passos = (("reservado", enviado, None), ("enviado", enviado, ("enviado", "--id-provedor", "msg_1")),
                  ("incerto", incerto, ("incerto",)))
        for estado, ap, conclusao in passos:
            with self.subTest(estado=estado):
                if conclusao:
                    self.concluir(envios[ap], *conclusao)
                r = self.recusa("envio_existente", *self.args_preparar(ap))
                self.assertEqual((r["envio_id"], r["estado"]), (envios[ap], estado))
                self.assertEqual(self.contar_envios(), 2)

    def test_mesmo_texto_em_outra_versao_e_duplicado(self):
        v1 = self.ok(*self.args_preparar(self.aprovar(versao=1)))
        r = self.recusa("duplicado", *self.args_preparar(self.aprovar(versao=2)))
        self.assertEqual(r["envio_id"], v1["envio_id"])
        self.assertEqual(self.contar_envios(), 1)

    def test_preparar_simultaneo_mesma_aprovacao_so_um_reserva(self):
        ap = self.aprovar()
        texto = self.texto()
        resultados = self.cli_paralelo([self.args_preparar(ap, texto)] * 2, env={"MILO_ENVIO_PAUSA_TESTE": "0.5"})
        motivos = sorted(r.get("motivo", "ok") for _, r in resultados)
        self.assertEqual(motivos, ["envio_existente", "ok"], resultados)
        self.assertEqual(self.contar_envios(), 1)

    def test_preparar_simultaneo_respeita_limite(self):
        self.config("limite_diario", 1)
        a = self.aprovar(conta="a", chat="cht_a", para="x@a.com")
        b = self.aprovar(conta="b", chat="cht_b", para="x@b.com")
        resultados = self.cli_paralelo([self.args_preparar(a), self.args_preparar(b)], env={"MILO_ENVIO_PAUSA_TESTE": "0.5"})
        motivos = sorted(r.get("motivo", "ok") for _, r in resultados)
        self.assertEqual(motivos, ["limite_diario", "ok"], resultados)
        self.assertEqual(self.contar_envios(), 1)

    def test_banco_travado_devolve_codigo_3_sem_gravar(self):
        ap = self.aprovar()
        texto = self.texto()
        trava = sqlite3.connect(self.db, isolation_level=None)
        trava.execute("BEGIN IMMEDIATE")
        try:
            self.recusa("banco_ocupado", *self.args_preparar(ap, texto), codigo=3)
        finally:
            trava.execute("ROLLBACK")
            trava.close()
        self.assertEqual(self.contar_envios(), 0)


class TestRegistro(Base):
    def test_eventos_so_acrescimo(self):
        self.aprovar()
        self.recusa("aprovador_sem_permissao", *self.args_aprovar(aprovador="mem_diego"))
        antes = self.sql("SELECT count(*) FROM eventos")[0][0]
        self.assertGreater(antes, 0)
        with self.assertRaises(sqlite3.DatabaseError):
            self.sql("UPDATE eventos SET motivo = 'apagado'")
        with self.assertRaises(sqlite3.DatabaseError):
            self.sql("DELETE FROM eventos")
        self.recusa("aprovador_sem_permissao", *self.args_aprovar(aprovador="mem_diego"))
        self.assertEqual(self.sql("SELECT count(*) FROM eventos")[0][0], antes + 1)


class TestParar(Base):
    def parar(self, chat):
        return self.ok("nunca-contatar", "add", "--tipo", "chat", "--chave", chat,
                       "--motivo", "pediu para parar", "--por", "mem_lead")

    def test_parar_por_chat_bloqueia_preparar_seguinte(self):
        self.liberar_teste()
        ap = self.aprovar()
        self.parar(CHAT)
        self.recusa("nunca_contatar", *self.args_preparar(ap))

    def test_nunca_contatar_chat_devolve_rotulos_de_envios_anteriores(self):
        self.liberar_teste()
        self.ok(*self.args_preparar(self.aprovar()))
        self.assertEqual(self.parar(CHAT)["rotulos"], [PARA])
        self.assertEqual(self.parar("cht_sem_envio")["rotulos"], [])

    def test_nunca_contatar_add_aceita_qualquer_por_e_nao_tem_remove(self):
        self.parar(CHAT)
        self.recusa("uso_invalido", "nunca-contatar", "remove", "--chave", CHAT, codigo=2)
        self.assertEqual(self.sql("SELECT tipo, criado_por FROM nunca_contatar"), [("chat", "mem_lead")])


class TestExecutorHumano(Base):
    def humano(self, ap, texto=None):
        return self.args_preparar(ap, texto, extra=("--executor", "humano"))

    def test_humano_mesmas_conferencias(self):
        ap = self.aprovar(chat=None)
        r = self.ok(*self.humano(ap))
        self.assertEqual((r["executor"], r["chat"], r["para"], r["corpo"]), ("humano", None, PARA, TEXTO.strip()))
        self.recusa("chat_ausente", *self.args_preparar(self.aprovar(conta="b", chat=None, para="x@b.com")))
        c = self.aprovar(conta="c", chat=None, para="x@c.com")
        self.recusa("texto_diferente", *self.humano(c, self.texto("Outro.\n")))
        d = self.aprovar(conta="d", chat=None, para="x@d.com")
        self.ok("nunca-contatar", "add", "--tipo", "email", "--chave", "x@d.com", "--motivo", "cliente", "--por", DONO)
        self.recusa("nunca_contatar", *self.humano(d))
        self.config("limite_diario", 1)
        e = self.aprovar(conta="e", chat=None, para="x@e.com")
        self.recusa("limite_diario", *self.humano(e))

    def test_humano_e_milo_nao_duplicam(self):
        self.liberar_teste()
        ap = self.aprovar(versao=1)
        self.ok(*self.humano(ap))
        r = self.recusa("envio_existente", *self.args_preparar(ap))
        self.assertEqual(r["executor"], "humano")
        self.recusa("duplicado", *self.args_preparar(self.aprovar(versao=2)))
        self.assertEqual(self.contar_envios(), 1)

    def test_concluir_humano_exige_confirmado_por(self):
        envio = self.ok(*self.humano(self.aprovar(chat=None)))["envio_id"]
        self.recusa("confirmado_por_ausente", "concluir", "--envio", envio, "--resultado", "enviado")
        self.concluir(envio, "enviado", "--confirmado-por", "mem_diego", "--nota", "Gmail, 10h12")
        self.assertEqual(self.sql("SELECT estado, confirmado_por, id_provedor, nota FROM envios WHERE id = ?", (envio,)),
                         [("enviado", "mem_diego", None, "Gmail, 10h12")])

    def test_concluir_humano_falhou_exige_quem_pode_enviar(self):
        self.cadastrar_carla()
        ap = self.aprovar(chat=None)
        envio = self.ok(*self.humano(ap))["envio_id"]
        self.recusa("aprovador_sem_permissao", "concluir", "--envio", envio, "--resultado", "falhou", "--confirmado-por", "mem_diego")
        self.recusa("somente_dono", "concluir", "--envio", envio, "--resultado", "falhou", "--confirmado-por", "mem_carla")
        self.concluir(envio, "falhou", "--confirmado-por", DONO, "--nota", "não vou enviar")
        self.ok(*self.humano(ap))

    def test_concluir_humano_incerto_aceita_qualquer_um_e_bloqueia(self):
        ap = self.aprovar(chat=None)
        envio = self.ok(*self.humano(ap))["envio_id"]
        self.concluir(envio, "incerto", "--confirmado-por", "mem_diego")
        self.assertEqual(self.recusa("envio_existente", *self.humano(ap))["estado"], "incerto")


class TestConclusao(Base):
    def setUp(self):
        super().setUp()
        self.liberar_teste()
        self.contas = 0

    def novo(self):
        self.contas += 1
        return self.preparar(self.aprovar(conta=f"c{self.contas}", chat=f"cht_c{self.contas}", para=f"x@c{self.contas}.com"))

    def test_falhou_libera_nova_tentativa_ate_2_falhas(self):
        ap = self.aprovar()
        primeira = self.preparar(ap)
        self.concluir(primeira, "falhou", "--erro", "Plow HTTP 403")
        segunda = self.preparar(ap)
        self.assertNotEqual(segunda, primeira)
        self.concluir(segunda, "falhou", "--erro", "Error: Plow account does not serve this conversation")
        self.recusa("falhas_esgotadas", *self.args_preparar(ap))

    def test_incerto_bloqueia_ate_resolver(self):
        ap = self.aprovar()
        envio = self.preparar(ap)
        self.concluir(envio, "incerto")
        self.assertEqual(self.recusa("envio_existente", *self.args_preparar(ap))["estado"], "incerto")
        self.ok("resolver", "--envio", envio, "--resultado", "falhou", "--aprovador", DONO, "--nota", "não chegou")
        self.assertNotEqual(self.preparar(ap), envio)

    def test_concluir_so_aceita_reservado(self):
        envio = self.novo()
        self.concluir(envio, "enviado", "--id-provedor", "msg_1")
        for resultado in ("enviado", "incerto", "falhou"):
            with self.subTest(resultado=resultado):
                r = self.recusa("estado_invalido", "concluir", "--envio", envio, "--resultado", resultado,
                                "--id-provedor", "msg_2", "--erro", "Plow HTTP 403")
                self.assertEqual(r["estado"], "enviado")
        self.recusa("envio_inexistente", "concluir", "--envio", 999, "--resultado", "incerto")

    def test_concluir_enviado_exige_id_provedor(self):
        envio = self.novo()
        self.recusa("id_provedor_ausente", "concluir", "--envio", envio, "--resultado", "enviado")
        self.assertEqual(self.sql("SELECT estado FROM envios WHERE id = ?", (envio,)), [("reservado",)])

    def test_concluir_falhou_exige_erro_classificado(self):
        recusados = ("Plow delivery is unknown; stopped to avoid resending", "Plow HTTP 408", "Plow HTTP 424",
                     "Plow HTTP 500", "timeout", "")
        for erro in recusados:
            with self.subTest(erro=erro):
                self.recusa("falhou_nao_comprovado", "concluir", "--envio", self.novo(), "--resultado", "falhou", "--erro", erro)
        for erro in ("Plow HTTP 403", "Plow HTTP 404", "Plow account does not serve this conversation"):
            with self.subTest(erro=erro):
                self.concluir(self.novo(), "falhou", "--erro", erro)

    def test_resolver_so_de_incerto_e_so_dono_em_modo_so_dono(self):
        self.cadastrar_carla()
        envio = self.novo()
        self.recusa("estado_invalido", "resolver", "--envio", envio, "--resultado", "falhou", "--aprovador", DONO)
        self.concluir(envio, "incerto")
        self.recusa("aprovador_sem_permissao", "resolver", "--envio", envio, "--resultado", "falhou", "--aprovador", "mem_diego")
        self.recusa("somente_dono", "resolver", "--envio", envio, "--resultado", "falhou", "--aprovador", "mem_carla")
        self.config("aprovacao_so_dono", 0)
        self.ok("resolver", "--envio", envio, "--resultado", "enviado", "--aprovador", "mem_carla")
        self.assertEqual(self.sql("SELECT estado, resolvido_por FROM envios WHERE id = ?", (envio,)), [("enviado", "mem_carla")])

    def test_liberar_exige_teste_enviado_e_so_dono_em_modo_so_dono(self):
        # Banco novo: começa fechado e sem liberação de teste.
        self.db = str(self.dir / "outro.sqlite")
        self.config("limite_diario", 10)
        self.cadastrar_carla()
        teste = self.enviar_teste()
        self.recusa("teste_nao_enviado", "liberar", "--envio", teste, "--aprovador", DONO)
        self.concluir(teste, "enviado", "--id-provedor", "msg_teste")
        self.recusa("aprovador_sem_permissao", "liberar", "--envio", teste, "--aprovador", "mem_diego")
        self.recusa("somente_dono", "liberar", "--envio", teste, "--aprovador", "mem_carla")
        ap = self.aprovar()
        self.recusa("teste_pendente", *self.args_preparar(ap))
        self.ok("liberar", "--envio", teste, "--aprovador", DONO)
        self.assertTrue(self.ok("liberar", "--envio", teste, "--aprovador", DONO).get("existente"))
        real = self.preparar(ap)
        self.concluir(real, "enviado", "--id-provedor", "msg_real")
        self.recusa("teste_nao_enviado", "liberar", "--envio", real, "--aprovador", DONO)

    def test_bloqueado_e_final(self):
        ap = self.aprovar()
        envio = self.preparar(ap)
        self.concluir(envio, "incerto")
        self.ok("resolver", "--envio", envio, "--resultado", "bloqueado", "--aprovador", DONO)
        self.recusa("estado_invalido", "concluir", "--envio", envio, "--resultado", "incerto")
        self.recusa("estado_invalido", "resolver", "--envio", envio, "--resultado", "falhou", "--aprovador", DONO)
        self.assertEqual(self.recusa("envio_existente", *self.args_preparar(ap))["estado"], "bloqueado")
        self.assertEqual(self.recusa("duplicado", *self.args_preparar(self.aprovar(versao=2)))["estado"], "bloqueado")


class TestPendentesERegistro(Base):
    def test_pendentes_lista_reservado_e_incerto_com_idade(self):
        self.assertFalse(self.ok("pendentes")["teste_liberado"])
        self.liberar_teste()
        reservado = self.preparar(self.aprovar(conta="a", chat="cht_a", para="x@a.com"))
        incerto = self.preparar(self.aprovar(conta="b", chat="cht_b", para="x@b.com"))
        self.concluir(incerto, "incerto")
        enviado = self.preparar(self.aprovar(conta="c", chat="cht_c", para="x@c.com"))
        self.concluir(enviado, "enviado", "--id-provedor", "msg_c")
        humano = self.ok(*self.args_preparar(self.aprovar(conta="d", chat=None, para="x@d.com"),
                                             extra=("--executor", "humano")))["envio_id"]
        r = self.ok("pendentes")
        self.assertTrue(r["teste_liberado"])
        vistos = {e["envio_id"]: (e["estado"], e["executor"], e["conta"]) for e in r["envios"]}
        self.assertEqual(vistos, {reservado: ("reservado", "milo", "a"), incerto: ("incerto", "milo", "b"),
                                  humano: ("reservado", "humano", "d")})
        for e in r["envios"]:
            self.assertIsInstance(e["idade_s"], int)
            self.assertGreaterEqual(e["idade_s"], 0)

    def test_registro_gerado_do_banco_inclui_recusas(self):
        self.liberar_teste()
        envio = self.preparar(self.aprovar())
        self.concluir(envio, "enviado", "--id-provedor", "msg_acme")
        self.recusa("aprovador_sem_permissao", *self.args_aprovar(conta="beta", aprovador="mem_diego"))
        r = self.ok("registro")
        arquivo = Path(r["arquivo"])
        self.assertEqual(arquivo, self.dir / "registro.md")
        conteudo = arquivo.read_text(encoding="utf-8")
        self.assertEqual(conteudo.splitlines()[0], "Gerado por milo-envio. Não editar.")
        for trecho in ("msg_acme", PARA, "aprovar_recusado", "aprovador_sem_permissao", "mem_diego", "liberado em"):
            self.assertIn(trecho, conteudo)
        outro = self.dir / "copia" / "registro.md"
        outro.parent.mkdir()
        self.assertEqual(Path(self.ok("registro", "--saida", outro)["arquivo"]), outro)


if __name__ == "__main__":
    unittest.main()
