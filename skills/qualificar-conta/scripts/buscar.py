#!/usr/bin/env python3
"""Busca na web para o Milo, pela versão HTML do DuckDuckGo, com o Brave de reserva.

Uso: buscar.py "<consulta>" [--max N]
Saída: uma linha JSON. Código 0 com resultados; 1 sem resultados ou bloqueado;
2 erro de uso ou de rede. Resultado de busca é pista, não fonte: o que for
afirmado precisa vir de uma página aberta depois.
"""
import argparse
import fcntl
import html
import html.parser
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://html.duckduckgo.com/html/"
BRAVE = "https://search.brave.com/search"
AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
INTERVALO_S = 6  # entre buscas; com 2,5 s o DuckDuckGo bloqueou na terceira
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


_BRAVE_BLOCO = re.compile(r'<div class="snippet [^"]*" data-pos="\d+" data-type="web"')


def _texto(fragmento):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def ler_resultados_brave(pagina, maximo=5):
    """A página do Brave vem pronta do servidor: um bloco data-type="web" por resultado."""
    inicios = [m.start() for m in _BRAVE_BLOCO.finditer(pagina)]
    vistos, saida = set(), []
    for i, inicio in enumerate(inicios):
        bloco = pagina[inicio:inicios[i + 1] if i + 1 < len(inicios) else inicio + 8000]
        link = re.search(r'<a href="(https?://[^"]+)"', bloco)
        if not link or link.group(1) in vistos:
            continue
        titulo = re.search(r'class="title search-snippet-title[^"]*"[^>]*>(.*?)</div>', bloco, re.S)
        trecho = re.search(r'class="content desktop-default-regular[^"]*"[^>]*>(.*?)</div>', bloco, re.S)
        vistos.add(link.group(1))
        saida.append({"titulo": _texto(titulo.group(1)) if titulo else "",
                      "url": html.unescape(link.group(1)),
                      "trecho": _texto(trecho.group(1)) if trecho else ""})
        if len(saida) == maximo:
            break
    return saida


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


def _baixar(pedido):
    with urllib.request.urlopen(pedido, timeout=20) as resposta:
        return resposta.read().decode("utf-8", "replace")


def buscar(consulta, maximo):
    esperar_vez()
    corpo = urllib.parse.urlencode({"q": consulta, "kl": "br-pt"}).encode()
    motivo = "sem_resultados"
    try:
        pagina = _baixar(urllib.request.Request(ENDPOINT, data=corpo, headers={"User-Agent": AGENTE}))
        if bloqueado(pagina):
            motivo = "bloqueado"
        else:
            resultados = ler_resultados(pagina, maximo)
            if resultados:
                return 0, {"ok": True, "consulta": consulta, "motor": "duckduckgo", "resultados": resultados}
    except urllib.error.HTTPError:
        motivo = "bloqueado"
    # Reserva: o Brave também entrega a página pronta, sem JavaScript.
    url = BRAVE + "?" + urllib.parse.urlencode({"q": consulta})
    try:
        pagina = _baixar(urllib.request.Request(url, headers={"User-Agent": AGENTE}))
    except urllib.error.HTTPError:  # 429 e afins: limite de uso, não falha de rede
        pagina, motivo = "", "bloqueado"
    resultados = ler_resultados_brave(pagina, maximo)
    if resultados:
        return 0, {"ok": True, "consulta": consulta, "motor": "brave", "resultados": resultados}
    if motivo == "bloqueado" or len(pagina) < 20000:
        return 1, {"ok": False, "consulta": consulta, "motivo": "bloqueado",
                   "detalhe": "Os buscadores pediram verificação. Tente os domínios prováveis ou peça o site a quem pediu."}
    return 1, {"ok": False, "consulta": consulta, "motivo": "sem_resultados"}


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
