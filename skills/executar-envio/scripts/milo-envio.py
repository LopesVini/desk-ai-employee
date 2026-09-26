#!/usr/bin/env python3
"""milo-envio: livro de aprovações e envios do Milo.

Interface, estados e limites em docs/milo-envio.md. Só biblioteca padrão.
Saída: sempre uma linha JSON. Códigos: 0 ok, 1 recusa, 2 uso inválido, 3 banco.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata

OK, RECUSA, USO, BANCO = 0, 1, 2, 3
DONO = "plow-owner"
VIVOS = ("reservado", "enviado", "incerto", "bloqueado")
OCUPAM = ("reservado", "enviado", "incerto")
PADROES = {"limite_diario": "0", "aprovacao_so_dono": "1"}
CHAT_RE = re.compile(r"^cht_[A-Za-z0-9_-]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DOMINIO_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")
CONTA_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Só para testes de concorrência: pausa dentro da transação do preparar.
# Teto de 2 s; valor inválido é ignorado.
PAUSA_TESTE = "MILO_ENVIO_PAUSA_TESTE"
PAUSA_MAXIMA = 2.0
# Erros de message(send) que provam que nada saiu (plugin Plow: 4xx exceto 408 e 424).
FALHA_COMPROVADA = re.compile(r"Plow HTTP 4(?!08|24)\d\d\b|does not serve this conversation")

ESQUEMA = [
    """CREATE TABLE aprovadores(
        identificador TEXT PRIMARY KEY, nome TEXT NOT NULL,
        pode_enviar INTEGER NOT NULL DEFAULT 0 CHECK (pode_enviar IN (0, 1)),
        pode_regras INTEGER NOT NULL DEFAULT 0 CHECK (pode_regras IN (0, 1)),
        criado_em TEXT NOT NULL, criado_por TEXT NOT NULL)""",
    """CREATE TABLE nunca_contatar(
        chave TEXT PRIMARY KEY,
        tipo TEXT NOT NULL CHECK (tipo IN ('email', 'dominio', 'empresa', 'chat')),
        motivo TEXT NOT NULL, criado_em TEXT NOT NULL, criado_por TEXT NOT NULL)""",
    """CREATE TABLE aprovacoes(
        id INTEGER PRIMARY KEY, conta TEXT NOT NULL, versao INTEGER NOT NULL,
        hash_texto TEXT NOT NULL, chat_uid TEXT, para TEXT NOT NULL,
        aprovador_id TEXT NOT NULL REFERENCES aprovadores(identificador),
        canal TEXT NOT NULL CHECK (canal IN ('dm', 'grupo', 'email')),
        aprovado_em TEXT NOT NULL, UNIQUE (conta, versao))""",
    """CREATE TABLE envios(
        id INTEGER PRIMARY KEY, aprovacao_id INTEGER NOT NULL REFERENCES aprovacoes(id),
        teste INTEGER NOT NULL CHECK (teste IN (0, 1)), chat_uid TEXT, para TEXT NOT NULL,
        executor TEXT NOT NULL DEFAULT 'milo' CHECK (executor IN ('milo', 'humano')),
        chave_dedup TEXT NOT NULL,
        estado TEXT NOT NULL CHECK (estado IN ('reservado', 'enviado', 'incerto', 'falhou', 'bloqueado')),
        tentado_em TEXT NOT NULL, concluido_em TEXT, id_provedor TEXT, confirmado_por TEXT,
        nota TEXT, erro TEXT, resolvido_por TEXT)""",
    """CREATE UNIQUE INDEX envios_chave_viva ON envios(chave_dedup)
        WHERE estado IN ('reservado', 'enviado', 'incerto', 'bloqueado')""",
    "CREATE INDEX envios_aprovacao ON envios(aprovacao_id)",
    "CREATE INDEX envios_tentado ON envios(tentado_em)",
    """CREATE TABLE config(
        chave TEXT PRIMARY KEY, valor TEXT, alterado_em TEXT NOT NULL, alterado_por TEXT NOT NULL)""",
    """CREATE TABLE eventos(
        id INTEGER PRIMARY KEY, em TEXT NOT NULL, tipo TEXT NOT NULL, ator TEXT,
        aprovacao_id INTEGER, envio_id INTEGER, motivo TEXT, dados TEXT)""",
    """CREATE TRIGGER eventos_sem_update BEFORE UPDATE ON eventos
        BEGIN SELECT RAISE(ABORT, 'eventos: só acréscimo'); END""",
    """CREATE TRIGGER eventos_sem_delete BEFORE DELETE ON eventos
        BEGIN SELECT RAISE(ABORT, 'eventos: só acréscimo'); END""",
]


class Saida(Exception):
    def __init__(self, codigo, corpo):
        super().__init__(corpo.get("motivo"))
        self.codigo, self.corpo = codigo, corpo


def recusa(motivo, **extra):
    return Saida(RECUSA, {"ok": False, "motivo": motivo, **extra})


def uso(detalhe):
    return Saida(USO, {"ok": False, "motivo": "uso_invalido", "detalhe": detalhe})


def agora(delta=None):
    momento = datetime.datetime.now(datetime.timezone.utc)
    if delta:
        momento += delta
    return momento.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def slug(texto):
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def normalizar(texto):
    if texto.startswith("﻿"):
        texto = texto[1:]
    texto = unicodedata.normalize("NFC", texto.replace("\r\n", "\n").replace("\r", "\n"))
    linhas = [linha.rstrip(" \t") for linha in texto.split("\n")]
    while linhas and not linhas[0]:
        linhas.pop(0)
    while linhas and not linhas[-1]:
        linhas.pop()
    return "\n".join(linhas)


def ler_texto(caminho):
    try:
        with open(caminho, "rb") as arquivo:
            bruto = arquivo.read()
    except OSError:
        raise recusa("texto_inexistente")
    try:
        corpo = normalizar(bruto.decode("utf-8"))
    except UnicodeDecodeError:
        raise recusa("texto_invalido")
    if not corpo:
        raise recusa("texto_vazio")
    return corpo, sha256(corpo)


def email_valido(valor):
    email = valor.strip().lower()
    if not EMAIL_RE.match(email):
        raise recusa("email_invalido")
    return email


def chat_valido(valor):
    if not CHAT_RE.match(valor):
        raise recusa("chat_invalido")
    return valor


# --- banco ---

def abrir(caminho):
    if not caminho:
        mesa = os.environ.get("MILO_MESA")
        if not mesa:
            raise Saida(USO, {"ok": False, "motivo": "sem_banco"})
        os.makedirs(mesa, exist_ok=True)
        caminho = os.path.join(mesa, "envios.sqlite")
    conn = sqlite3.connect(caminho, timeout=5.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = FULL")
    if conn.execute("PRAGMA user_version").fetchone()[0] < 1:
        with transacao(conn):
            if conn.execute("PRAGMA user_version").fetchone()[0] < 1:
                for comando in ESQUEMA:
                    conn.execute(comando)
                momento = agora()
                conn.execute("INSERT INTO aprovadores VALUES (?, 'dono', 1, 1, ?, 'canal')", (DONO, momento))
                for chave, valor in PADROES.items():
                    conn.execute("INSERT INTO config VALUES (?, ?, ?, 'milo-envio')", (chave, valor, momento))
                conn.execute("PRAGMA user_version = 1")
    return conn, caminho


def pausa_teste():
    try:
        segundos = float(os.environ.get(PAUSA_TESTE, ""))
    except ValueError:
        return
    if segundos > 0:
        time.sleep(min(segundos, PAUSA_MAXIMA))


class transacao:
    """BEGIN IMMEDIATE: trava de escrita desde o início, antes de qualquer leitura."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, tipo, *_):
        if not self.conn.in_transaction:
            return False
        self.conn.execute("COMMIT" if tipo is None else "ROLLBACK")
        return False


def cfg(conn, chave):
    linha = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
    return linha[0] if linha else PADROES.get(chave)


def evento(conn, tipo, ator=None, aprovacao_id=None, envio_id=None, motivo=None, dados=None):
    conn.execute(
        "INSERT INTO eventos(em, tipo, ator, aprovacao_id, envio_id, motivo, dados) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (agora(), tipo, ator, aprovacao_id, envio_id, motivo,
         json.dumps(dados, ensure_ascii=False, sort_keys=True) if dados else None))


def checar_aprovador(conn, identificador, canal=None):
    """canal=None: comandos sem canal (concluir, resolver, liberar) exigem só plow-owner no modo só-dono."""
    linha = conn.execute("SELECT pode_enviar FROM aprovadores WHERE identificador = ?", (identificador,)).fetchone()
    if linha is None or not linha[0]:
        raise recusa("aprovador_sem_permissao", aprovador=identificador)
    if cfg(conn, "aprovacao_so_dono") == "1" and (identificador != DONO or canal not in (None, "dm")):
        raise recusa("somente_dono", aprovador=identificador)


def checar_dono(por):
    if por != DONO:
        raise recusa("somente_dono", por=por)


def bloqueio(conn, conta, chat, para):
    dominio = para.rsplit("@", 1)[1] if "@" in para else ""
    empresa = slug(conta)
    for linha in conn.execute("SELECT chave, tipo, motivo FROM nunca_contatar"):
        chave, tipo = linha["chave"], linha["tipo"]
        if ((tipo == "email" and chave == para)
                or (tipo == "chat" and chat is not None and chave == chat)
                or (tipo == "dominio" and (dominio == chave or dominio.endswith("." + chave)))
                or (tipo == "empresa" and chave == empresa)):
            return {"tipo": tipo, "chave": chave, "motivo_lista": linha["motivo"]}
    return None


# --- comandos ---

def cmd_aprovar(conn, a):
    chat = chat_valido(a.chat) if a.chat is not None else None
    para = email_valido(a.para)
    _, hash_texto = ler_texto(a.texto_arquivo)
    with transacao(conn):
        checar_aprovador(conn, a.aprovador, a.canal)
        bloqueado = bloqueio(conn, a.conta, chat, para)
        if bloqueado:
            raise recusa("nunca_contatar", **bloqueado)
        antiga = conn.execute("SELECT * FROM aprovacoes WHERE conta = ? AND versao = ?", (a.conta, a.versao)).fetchone()
        if antiga:
            if (antiga["hash_texto"], antiga["chat_uid"], antiga["para"]) == (hash_texto, chat, para):
                return {"ok": True, "aprovacao_id": antiga["id"], "hash": hash_texto, "existente": True}
            raise recusa("versao_conflitante", aprovacao_id=antiga["id"])
        cursor = conn.execute(
            "INSERT INTO aprovacoes(conta, versao, hash_texto, chat_uid, para, aprovador_id, canal, aprovado_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (a.conta, a.versao, hash_texto, chat, para, a.aprovador, a.canal, agora()))
        evento(conn, "aprovado", a.aprovador, cursor.lastrowid,
               dados={"conta": a.conta, "versao": a.versao, "chat": chat, "para": para, "canal": a.canal})
        return {"ok": True, "aprovacao_id": cursor.lastrowid, "hash": hash_texto}


def cmd_preparar(conn, a):
    teste = 1 if a.teste else 0
    if teste and a.executor == "humano":
        raise uso("--teste não se aplica a --executor humano")
    if teste and (a.chat is None or a.para is None):
        raise uso("--teste exige --chat e --para")
    if not teste and (a.chat is not None or a.para is not None):
        raise uso("--chat e --para só com --teste")
    if teste:
        chat_teste, para_teste = chat_valido(a.chat), email_valido(a.para)
    corpo, hash_texto = ler_texto(a.texto_arquivo)
    with transacao(conn):
        ap = conn.execute("SELECT * FROM aprovacoes WHERE id = ?", (a.aprovacao,)).fetchone()
        if ap is None:
            raise recusa("aprovacao_inexistente")
        chat, para = (chat_teste, para_teste) if teste else (ap["chat_uid"], ap["para"])
        existente = conn.execute(
            f"SELECT id, estado, executor FROM envios WHERE aprovacao_id = ? AND teste = ?"
            f" AND estado IN {VIVOS} ORDER BY id DESC LIMIT 1", (ap["id"], teste)).fetchone()
        if existente:
            raise recusa("envio_existente", envio_id=existente["id"], estado=existente["estado"],
                         executor=existente["executor"])
        if a.executor == "milo" and chat is None:
            raise recusa("chat_ausente")
        checar_aprovador(conn, ap["aprovador_id"], ap["canal"])
        if hash_texto != ap["hash_texto"]:
            raise recusa("texto_diferente")
        destino = chat if chat is not None else "email:" + para
        chave = sha256("|".join((ap["conta"], destino, hash_texto, "teste" if teste else "real")))
        if not teste:
            bloqueado = bloqueio(conn, ap["conta"], chat, para)
            if bloqueado:
                raise recusa("nunca_contatar", **bloqueado)
            if a.executor == "milo" and not cfg(conn, "teste_liberado_em"):
                raise recusa("teste_pendente")
        vivo = conn.execute(f"SELECT id, estado FROM envios WHERE chave_dedup = ? AND estado IN {VIVOS}",
                            (chave,)).fetchone()
        if vivo:
            raise recusa("duplicado", envio_id=vivo["id"], estado=vivo["estado"])
        if not teste:
            contato = conn.execute(
                f"SELECT id, estado, tentado_em FROM envios WHERE teste = 0 AND estado IN {OCUPAM}"
                " AND ((? IS NOT NULL AND chat_uid = ?) OR para = ?) ORDER BY id LIMIT 1",
                (chat, chat, para)).fetchone()
            if contato:
                raise recusa("destinatario_ja_contatado", envio_id=contato["id"], estado=contato["estado"],
                             tentado_em=contato["tentado_em"])
            limite = int(cfg(conn, "limite_diario"))
            usados = conn.execute(
                f"SELECT count(*) FROM envios WHERE teste = 0 AND estado IN {OCUPAM} AND tentado_em >= ?",
                (agora(datetime.timedelta(hours=-24)),)).fetchone()[0]
            if usados >= limite:
                raise recusa("limite_diario", limite=limite)
        falhas = conn.execute("SELECT count(*) FROM envios WHERE chave_dedup = ? AND estado = 'falhou'",
                              (chave,)).fetchone()[0]
        if falhas >= 2:
            raise recusa("falhas_esgotadas")
        pausa_teste()
        try:
            cursor = conn.execute(
                "INSERT INTO envios(aprovacao_id, teste, chat_uid, para, executor, chave_dedup, estado, tentado_em)"
                " VALUES (?, ?, ?, ?, ?, ?, 'reservado', ?)",
                (ap["id"], teste, chat, para, a.executor, chave, agora()))
        except sqlite3.IntegrityError:
            raise recusa("duplicado")
        evento(conn, "preparado", None, ap["id"], cursor.lastrowid,
               dados={"teste": bool(teste), "executor": a.executor, "chat": chat, "para": para})
        return {"ok": True, "envio_id": cursor.lastrowid, "estado": "reservado", "teste": bool(teste),
                "executor": a.executor, "chat": chat, "para": para, "corpo": corpo}


def cmd_aprovadores(conn, a):
    if a.acao == "list":
        linhas = conn.execute("SELECT identificador, nome, pode_enviar, pode_regras FROM aprovadores ORDER BY criado_em")
        return {"ok": True, "aprovadores": [dict(linha) for linha in linhas]}
    checar_dono(a.por)
    if a.uid == DONO:
        raise recusa("dono_imutavel")
    with transacao(conn):
        if a.acao == "add":
            conn.execute(
                "INSERT INTO aprovadores VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(identificador) DO UPDATE"
                " SET nome = excluded.nome, pode_enviar = excluded.pode_enviar, pode_regras = excluded.pode_regras",
                (a.uid, a.nome, int(a.enviar), int(a.regras), agora(), a.por))
            evento(conn, "aprovador_add", a.por, dados={"uid": a.uid, "nome": a.nome,
                                                        "enviar": a.enviar, "regras": a.regras})
        else:
            if conn.execute("SELECT 1 FROM aprovadores WHERE identificador = ?", (a.uid,)).fetchone() is None:
                raise recusa("aprovador_inexistente")
            conn.execute("UPDATE aprovadores SET pode_enviar = 0, pode_regras = 0 WHERE identificador = ?", (a.uid,))
            evento(conn, "aprovador_remove", a.por, dados={"uid": a.uid})
    return {"ok": True, "uid": a.uid}


def cmd_nunca_contatar(conn, a):
    if a.acao == "list":
        linhas = conn.execute("SELECT chave, tipo, motivo, criado_em, criado_por FROM nunca_contatar ORDER BY criado_em")
        return {"ok": True, "nunca_contatar": [dict(linha) for linha in linhas]}
    if a.tipo == "email":
        chave = email_valido(a.chave)
    elif a.tipo == "chat":
        chave = chat_valido(a.chave.strip())
    elif a.tipo == "dominio":
        chave = a.chave.strip().lower().lstrip("@.")
        if not DOMINIO_RE.match(chave):
            raise recusa("dominio_invalido")
    else:
        chave = slug(a.chave)
        if not chave:
            raise uso("empresa vazia")
    with transacao(conn):
        existente = conn.execute("SELECT 1 FROM nunca_contatar WHERE chave = ?", (chave,)).fetchone() is not None
        if not existente:
            conn.execute("INSERT INTO nunca_contatar VALUES (?, ?, ?, ?, ?)", (chave, a.tipo, a.motivo, agora(), a.por))
            evento(conn, "nunca_contatar_add", a.por, motivo=a.motivo, dados={"tipo": a.tipo, "chave": chave})
        resposta = {"ok": True, "tipo": a.tipo, "chave": chave, "existente": existente}
        if a.tipo == "chat":
            linhas = conn.execute("SELECT DISTINCT para FROM envios WHERE chat_uid = ? AND teste = 0 ORDER BY para", (chave,))
            resposta["rotulos"] = [linha[0] for linha in linhas]
        return resposta


def cmd_config(conn, a):
    if a.acao == "get":
        valores = dict(PADROES)
        valores.update({linha["chave"]: linha["valor"] for linha in conn.execute("SELECT chave, valor FROM config")})
        if a.chave:
            return {"ok": True, "chave": a.chave, "valor": valores.get(a.chave)}
        return {"ok": True, "config": valores}
    checar_dono(a.por)
    valor = a.valor.strip()
    if a.chave == "limite_diario" and not valor.isdigit():
        raise uso("limite_diario deve ser inteiro >= 0")
    if a.chave == "aprovacao_so_dono" and valor not in ("0", "1"):
        raise uso("aprovacao_so_dono deve ser 0 ou 1")
    with transacao(conn):
        conn.execute("INSERT INTO config VALUES (?, ?, ?, ?) ON CONFLICT(chave) DO UPDATE"
                     " SET valor = excluded.valor, alterado_em = excluded.alterado_em, alterado_por = excluded.alterado_por",
                     (a.chave, str(int(valor)), agora(), a.por))
        evento(conn, "config_set", a.por, dados={"chave": a.chave, "valor": str(int(valor))})
    return {"ok": True, "chave": a.chave, "valor": str(int(valor))}


def carregar_envio(conn, envio_id):
    envio = conn.execute("SELECT * FROM envios WHERE id = ?", (envio_id,)).fetchone()
    if envio is None:
        raise recusa("envio_inexistente", envio_id=envio_id)
    return envio


def cmd_concluir(conn, a):
    with transacao(conn):
        envio = carregar_envio(conn, a.envio)
        if envio["estado"] != "reservado":
            raise recusa("estado_invalido", envio_id=envio["id"], estado=envio["estado"])
        if envio["executor"] == "humano":
            # enviado/incerto só restringem (bloqueiam reenvio): qualquer sender.id confirma.
            # falhou libera nova tentativa: exige quem pode enviar.
            if not a.confirmado_por:
                raise recusa("confirmado_por_ausente", envio_id=envio["id"])
            if a.resultado == "falhou":
                checar_aprovador(conn, a.confirmado_por)
            id_provedor, erro = None, a.erro
        else:
            if a.confirmado_por:
                raise uso("--confirmado-por só vale para executor humano")
            if a.resultado == "enviado" and not a.id_provedor:
                raise recusa("id_provedor_ausente", envio_id=envio["id"])
            if a.resultado == "falhou" and not FALHA_COMPROVADA.search(a.erro or ""):
                raise recusa("falhou_nao_comprovado", envio_id=envio["id"])
            id_provedor, erro = a.id_provedor, a.erro
        conn.execute(
            "UPDATE envios SET estado = ?, concluido_em = ?, id_provedor = ?, erro = ?, confirmado_por = ?, nota = ?"
            " WHERE id = ?",
            (a.resultado, agora(), id_provedor, erro, a.confirmado_por, a.nota, envio["id"]))
        evento(conn, "concluido", a.confirmado_por, envio["aprovacao_id"], envio["id"], a.resultado,
               {"executor": envio["executor"], "id_provedor": id_provedor, "erro": erro, "nota": a.nota})
    return {"ok": True, "envio_id": envio["id"], "estado": a.resultado}


def cmd_resolver(conn, a):
    with transacao(conn):
        envio = carregar_envio(conn, a.envio)
        if envio["estado"] != "incerto":
            raise recusa("estado_invalido", envio_id=envio["id"], estado=envio["estado"])
        checar_aprovador(conn, a.aprovador)
        conn.execute("UPDATE envios SET estado = ?, resolvido_por = ?, nota = coalesce(?, nota),"
                     " concluido_em = ? WHERE id = ?",
                     (a.resultado, a.aprovador, a.nota, agora(), envio["id"]))
        evento(conn, "resolvido", a.aprovador, envio["aprovacao_id"], envio["id"], a.resultado, {"nota": a.nota})
    return {"ok": True, "envio_id": envio["id"], "estado": a.resultado}


def cmd_liberar(conn, a):
    with transacao(conn):
        envio = carregar_envio(conn, a.envio)
        if not envio["teste"] or envio["estado"] != "enviado":
            raise recusa("teste_nao_enviado", envio_id=envio["id"], estado=envio["estado"])
        checar_aprovador(conn, a.aprovador)
        liberado = cfg(conn, "teste_liberado_em")
        if liberado:
            return {"ok": True, "existente": True, "teste_liberado_em": liberado,
                    "teste_liberado_por": cfg(conn, "teste_liberado_por")}
        momento = agora()
        for chave, valor in (("teste_liberado_em", momento), ("teste_liberado_por", a.aprovador),
                             ("teste_envio_id", str(envio["id"]))):
            conn.execute("INSERT OR REPLACE INTO config VALUES (?, ?, ?, ?)", (chave, valor, momento, a.aprovador))
        evento(conn, "teste_liberado", a.aprovador, envio["aprovacao_id"], envio["id"])
    return {"ok": True, "teste_liberado_em": momento, "teste_liberado_por": a.aprovador}


def listar_envios(conn, onde="", params=()):
    return conn.execute(
        "SELECT e.*, a.conta, a.versao FROM envios e JOIN aprovacoes a ON a.id = e.aprovacao_id"
        f" {onde} ORDER BY e.tentado_em, e.id", params).fetchall()


def cmd_pendentes(conn, a):
    referencia = datetime.datetime.now(datetime.timezone.utc)
    envios = []
    for e in listar_envios(conn, "WHERE e.estado IN ('reservado', 'incerto')"):
        tentado = datetime.datetime.strptime(e["tentado_em"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
        envios.append({"envio_id": e["id"], "conta": e["conta"], "versao": e["versao"], "chat": e["chat_uid"],
                       "para": e["para"], "estado": e["estado"], "teste": bool(e["teste"]),
                       "executor": e["executor"], "tentado_em": e["tentado_em"],
                       "idade_s": max(0, int((referencia - tentado).total_seconds()))})
    return {"ok": True, "teste_liberado": bool(cfg(conn, "teste_liberado_em")), "envios": envios}


def celula(valor):
    if valor is None or valor == "":
        return "—"
    return str(valor).replace("|", "\\|").replace("\n", " ")


def tabela(cabecalho, linhas):
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(celula(v) for v in linha) + " |" for linha in linhas]
    return saida if linhas else saida + ["| " + " | ".join("—" for _ in cabecalho) + " |"]


def cmd_registro(conn, a):
    destino = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.db_caminho)), "registro.md")
    liberado = cfg(conn, "teste_liberado_em")
    envios = listar_envios(conn)
    aprovacoes = conn.execute("SELECT * FROM aprovacoes ORDER BY id").fetchall()
    eventos = conn.execute("SELECT * FROM eventos ORDER BY id").fetchall()
    linhas = [
        "Gerado por milo-envio. Não editar.", "",
        "# Registro de envios do Milo", "",
        f"Atualizado em {agora()} a partir de `envios.sqlite`.", "",
        "## Configuração", "",
        f"- Limite diário: {cfg(conn, 'limite_diario')} envios reais em 24 h",
        f"- Só o dono aprova: {'sim' if cfg(conn, 'aprovacao_so_dono') == '1' else 'não'}",
        f"- Teste da instalação: {'liberado em ' + liberado + ' por ' + str(cfg(conn, 'teste_liberado_por')) if liberado else 'pendente'}",
        "", "## Envios", "",
        *tabela(("#", "Conta", "Versão", "Para", "Chat", "Executor", "Tipo", "Estado", "Tentado em", "Concluído em",
                 "Confirmação"),
                [(e["id"], e["conta"], e["versao"], e["para"], e["chat_uid"], e["executor"],
                  "teste" if e["teste"] else "real", e["estado"], e["tentado_em"], e["concluido_em"],
                  " ".join(filter(None, (e["id_provedor"], e["confirmado_por"] and "por " + e["confirmado_por"],
                                         e["resolvido_por"] and "resolvido por " + e["resolvido_por"],
                                         e["erro"], e["nota"])))) for e in envios]),
        "", "## Aprovações", "",
        *tabela(("#", "Conta", "Versão", "Para", "Chat", "Aprovador", "Canal", "Aprovado em"),
                [(p["id"], p["conta"], p["versao"], p["para"], p["chat_uid"], p["aprovador_id"], p["canal"],
                  p["aprovado_em"]) for p in aprovacoes]),
        "", "## Eventos e recusas", "",
        *tabela(("Quando", "Tipo", "Ator", "Motivo", "Aprovação", "Envio"),
                [(v["em"], v["tipo"], v["ator"], v["motivo"], v["aprovacao_id"], v["envio_id"]) for v in eventos]),
        "", "## Nunca contatar", "",
        *tabela(("Chave", "Tipo", "Motivo", "Desde", "Por"),
                [tuple(n) for n in conn.execute(
                    "SELECT chave, tipo, motivo, criado_em, criado_por FROM nunca_contatar ORDER BY criado_em")]),
        "", "## Aprovadores", "",
        *tabela(("Identificador", "Nome", "Envia", "Regras"),
                [(r["identificador"], r["nome"], "sim" if r["pode_enviar"] else "não",
                  "sim" if r["pode_regras"] else "não")
                 for r in conn.execute("SELECT * FROM aprovadores ORDER BY criado_em")]),
        "",
    ]
    temporario = destino + ".tmp"
    with open(temporario, "w", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write("\n".join(linhas))
    os.replace(temporario, destino)
    return {"ok": True, "arquivo": destino, "aprovacoes": len(aprovacoes), "envios": len(envios),
            "eventos": len(eventos)}


# --- linha de comando ---

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise uso(message)


def tipo_conta(valor):
    if not CONTA_RE.match(valor):
        raise argparse.ArgumentTypeError("conta deve ser slug (minúsculas, números e hífen)")
    return valor


def tipo_versao(valor):
    if not valor.isdigit() or int(valor) < 1:
        raise argparse.ArgumentTypeError("versão deve ser inteiro >= 1")
    return int(valor)


def parser():
    banco = Parser(add_help=False)
    banco.add_argument("--db", default=argparse.SUPPRESS)
    p = Parser(prog="milo-envio", description="Livro de aprovações e envios do Milo (docs/milo-envio.md).")
    p.add_argument("--db", default=None)
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("aprovar", parents=[banco])
    s.add_argument("--conta", required=True, type=tipo_conta)
    s.add_argument("--versao", required=True, type=tipo_versao)
    s.add_argument("--texto-arquivo", required=True)
    s.add_argument("--chat")
    s.add_argument("--para", required=True)
    s.add_argument("--aprovador", required=True)
    s.add_argument("--canal", required=True, choices=("dm", "grupo", "email"))
    s.set_defaults(func=cmd_aprovar, nome="aprovar")

    s = sub.add_parser("preparar", parents=[banco])
    s.add_argument("--aprovacao", required=True, type=int)
    s.add_argument("--texto-arquivo", required=True)
    s.add_argument("--teste", action="store_true")
    s.add_argument("--chat")
    s.add_argument("--para")
    s.add_argument("--executor", choices=("milo", "humano"), default="milo")
    s.set_defaults(func=cmd_preparar, nome="preparar")

    s = sub.add_parser("aprovadores", parents=[banco])
    acoes = s.add_subparsers(dest="acao", required=True)
    add = acoes.add_parser("add", parents=[banco])
    add.add_argument("--uid", required=True)
    add.add_argument("--nome", required=True)
    add.add_argument("--enviar", action="store_true")
    add.add_argument("--regras", action="store_true")
    add.add_argument("--por", required=True)
    remove = acoes.add_parser("remove", parents=[banco])
    remove.add_argument("--uid", required=True)
    remove.add_argument("--por", required=True)
    acoes.add_parser("list", parents=[banco])
    s.set_defaults(func=cmd_aprovadores, nome="aprovadores")

    s = sub.add_parser("nunca-contatar", parents=[banco])
    acoes = s.add_subparsers(dest="acao", required=True)
    add = acoes.add_parser("add", parents=[banco])
    add.add_argument("--chave", required=True)
    add.add_argument("--tipo", required=True, choices=("email", "dominio", "empresa", "chat"))
    add.add_argument("--motivo", required=True)
    add.add_argument("--por", required=True)
    acoes.add_parser("list", parents=[banco])
    s.set_defaults(func=cmd_nunca_contatar, nome="nunca-contatar")

    s = sub.add_parser("config", parents=[banco])
    acoes = s.add_subparsers(dest="acao", required=True)
    get = acoes.add_parser("get", parents=[banco])
    get.add_argument("--chave")
    put = acoes.add_parser("set", parents=[banco])
    put.add_argument("--chave", required=True, choices=tuple(PADROES))
    put.add_argument("--valor", required=True)
    put.add_argument("--por", required=True)
    s.set_defaults(func=cmd_config, nome="config")

    s = sub.add_parser("concluir", parents=[banco])
    s.add_argument("--envio", required=True, type=int)
    s.add_argument("--resultado", required=True, choices=("enviado", "incerto", "falhou"))
    s.add_argument("--id-provedor")
    s.add_argument("--erro")
    s.add_argument("--confirmado-por")
    s.add_argument("--nota")
    s.set_defaults(func=cmd_concluir, nome="concluir")

    s = sub.add_parser("resolver", parents=[banco])
    s.add_argument("--envio", required=True, type=int)
    s.add_argument("--resultado", required=True, choices=("enviado", "falhou", "bloqueado"))
    s.add_argument("--aprovador", required=True)
    s.add_argument("--nota")
    s.set_defaults(func=cmd_resolver, nome="resolver")

    s = sub.add_parser("liberar", parents=[banco])
    s.add_argument("--envio", required=True, type=int)
    s.add_argument("--aprovador", required=True)
    s.set_defaults(func=cmd_liberar, nome="liberar")

    s = sub.add_parser("pendentes", parents=[banco])
    s.set_defaults(func=cmd_pendentes, nome="pendentes")

    s = sub.add_parser("registro", parents=[banco])
    s.add_argument("--saida")
    s.set_defaults(func=cmd_registro, nome="registro")
    return p


def registrar_recusa(conn, a, corpo):
    """Toda recusa vai para eventos, numa transação própria. Se falhar, a recusa vale do mesmo jeito."""
    campos = ("conta", "versao", "chat", "para", "canal", "executor", "teste", "tipo", "chave", "uid", "acao",
              "resultado", "erro")
    dados = {k: getattr(a, k) for k in campos if getattr(a, k, None) not in (None, False)}
    dados.update({k: v for k, v in corpo.items() if k not in ("ok", "motivo")})
    ator = getattr(a, "aprovador", None) or getattr(a, "por", None) or getattr(a, "confirmado_por", None)
    try:
        with transacao(conn):
            evento(conn, a.nome + "_recusado", ator, getattr(a, "aprovacao", None) or corpo.get("aprovacao_id"),
                   getattr(a, "envio", None) or corpo.get("envio_id"), corpo["motivo"], dados)
    except sqlite3.Error:
        corpo["evento_gravado"] = False


def executar(argv):
    conn = None
    try:
        a = parser().parse_args(argv)
        conn, a.db_caminho = abrir(getattr(a, "db", None))
        try:
            return a.func(conn, a)
        except Saida as saida:
            if saida.codigo == RECUSA:
                registrar_recusa(conn, a, saida.corpo)
            raise
    except Saida as saida:
        return saida
    except sqlite3.Error as erro:
        texto = str(erro).lower()
        motivo = "banco_ocupado" if ("locked" in texto or "busy" in texto) else "erro_banco"
        return Saida(BANCO, {"ok": False, "motivo": motivo, "detalhe": str(erro)})
    finally:
        if conn is not None:
            conn.close()


def main(argv=None):
    resultado = executar(sys.argv[1:] if argv is None else argv)
    codigo, corpo = (resultado.codigo, resultado.corpo) if isinstance(resultado, Saida) else (OK, resultado)
    sys.stdout.buffer.write((json.dumps(corpo, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.flush()
    return codigo


if __name__ == "__main__":
    sys.exit(main())
