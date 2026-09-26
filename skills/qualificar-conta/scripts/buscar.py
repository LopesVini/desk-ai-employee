#!/usr/bin/env python3
"""Busca na web para o Milo, pela versão HTML do DuckDuckGo (sem JavaScript).

Uso: buscar.py "<consulta>" [--max N]
Saída: uma linha JSON. Código 0 com resultados; 1 sem resultados ou bloqueado;
2 erro de uso ou de rede. Resultado de busca é pista, não fonte: o que for
afirmado precisa vir de uma página aberta depois.
"""
import argparse
import fcntl
import html.parser
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://html.duckduckgo.com/html/"
AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
INTERVALO_S = 2.5  # entre buscas, para o DuckDuckGo não bloquear
MARCA_TEMPO = "/tmp/milo-busca.ultima"
SINAIS_BLOQUEIO = ("anomaly-modal", "challenge-form", "detected unusual traffic")


def url_real(href):
    """Resolve o redirecionamento //duckduckgo.com/l/?uddg=<url>; anúncios viram None."""
    if href.startswith("//"):
        href = "https:" + href
    partes = urllib.parse.urlparse(href)
    if partes.netloc.endswith("duckduckgo.com"):
        if partes.path == "/l/":
            destino = urllib.parse.parse_qs(partes.query).get("uddg", [None])[0]
            return destino
        return None  # y.js e outros links internos são anúncios
    return href


class _Leitor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.resultados, self._campo, self._atual = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if "result__a" in classes:
            self._atual = {"titulo": "", "url": url_real(a.get("href") or ""), "trecho": ""}
            self.resultados.append(self._atual)
            self._campo = "titulo"
        elif "result__snippet" in classes and self._atual is not None:
            self._campo = "trecho"

    def handle_endtag(self, tag):
        if tag == "a":
            self._campo = None

    def handle_data(self, dados):
        if self._campo and self._atual is not None:
            self._atual[self._campo] += dados


def ler_resultados(pagina, maximo=5):
    leitor = _Leitor()
    leitor.feed(pagina)
    vistos, saida = set(), []
    for r in leitor.resultados:
        if not r["url"] or r["url"] in vistos:
            continue
        vistos.add(r["url"])
        saida.append({k: " ".join(v.split()) for k, v in r.items()})
        if len(saida) == maximo:
            break
    return saida


def bloqueado(pagina):
    baixa = pagina.lower()
    return any(s in baixa for s in SINAIS_BLOQUEIO)


def esperar_vez():
    with open(MARCA_TEMPO, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            ultima = float(f.read().strip() or 0)
        except ValueError:
            ultima = 0
        falta = INTERVALO_S - (time.time() - ultima)
        if falta > 0:
            time.sleep(falta)
        f.seek(0)
        f.truncate()
        f.write(str(time.time()))


def buscar(consulta, maximo):
    esperar_vez()
    corpo = urllib.parse.urlencode({"q": consulta, "kl": "br-pt"}).encode()
    pedido = urllib.request.Request(ENDPOINT, data=corpo, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(pedido, timeout=20) as resposta:
        pagina = resposta.read().decode("utf-8", "replace")
    if bloqueado(pagina):
        return 1, {"ok": False, "consulta": consulta, "motivo": "bloqueado",
                   "detalhe": "O DuckDuckGo pediu verificação. Espere alguns minutos ou peça o site a quem pediu."}
    resultados = ler_resultados(pagina, maximo)
    if not resultados:
        return 1, {"ok": False, "consulta": consulta, "motivo": "sem_resultados"}
    return 0, {"ok": True, "consulta": consulta, "resultados": resultados}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("consulta")
    p.add_argument("--max", type=int, default=5)
    args = p.parse_args(argv)
    if not args.consulta.strip() or not 1 <= args.max <= 10:
        print(json.dumps({"ok": False, "motivo": "uso_invalido"}))
        return 2
    try:
        codigo, saida = buscar(args.consulta.strip(), args.max)
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        codigo, saida = 2, {"ok": False, "consulta": args.consulta, "motivo": "erro_rede", "detalhe": str(erro)[:200]}
    print(json.dumps(saida, ensure_ascii=False))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
