"""Cenários do Milo por linha de comando, sem celular e sem a linha da Plow.

Uso, da raiz do repositório:
    python3 tests/cenarios/cenarios.py preparar --imagem milo:dev --credenciais ~/caminho/plow-credentials
    python3 tests/cenarios/cenarios.py rodar [--modelo sonnet|glm] [cenario ...]

`preparar` sobe o contêiner `milo-teste-<modelo>` com a imagem pedida, gera a
configuração sem o canal da Plow (setup.mjs) e copia os estados de teste.
`rodar` recomeça a mesa a partir do estado de cada cenário, manda as mensagens
numa sessão própria e confere respostas e arquivos. Resultados em
tests/cenarios/resultados/<modelo>/ (fora do Git).

Cada cenário gasta créditos reais da conta Plow das credenciais (de US$ 0,20 a
US$ 2,50 no Sonnet). Rode só os afetados por uma mudança. A linha de comando não
tem remetente: o que depende de quem mandou (dono x outra pessoa) só se testa
pelo celular.
"""
import argparse, json, os, pathlib, re, subprocess, sys, time

MODELOS = {"glm": "plow/z-ai/glm-5.2", "sonnet": "plow/anthropic/claude-sonnet-5"}
MESA = "/var/lib/plow/workspace/mesa"

# Cada check: (descrição, onde, regex, deve_casar). "onde" é "resposta:<n>",
# "respostas" (todas), "arquivo:<caminho relativo à mesa>" ou "existe:<glob>".
CENARIOS = {
    "historico-contra-mesa": {
        "fixture": "playbook",
        "turnos": [
            {"msg": "oi"},
            {"antes": f"rm -rf {MESA}", "msg": "oi de novo. tá tudo pronto pra eu te mandar empresas?"},
        ],
        "checks": [
            ("não diz que o playbook está pronto", "resposta:1", r"(tudo pronto|playbook[^.\n]{0,40}(gravado|pronto|confirmado))", False),
            ("diz que não achou o playbook", "resposta:1", r"(não (encontr|ach|h[áa]|tem|existe)|sumiu|vazi|apagad|não está)", True),
        ],
    },
    "onboarding-confirmado": {
        "fixture": "vazia",
        "precisa": "MILO_CENARIO_SITE",
        "turnos": [
            {"msg": "dados da minha empresa\n\nlink do site: " + os.environ.get("MILO_CENARIO_SITE", "")},
            {"msg": "1. Eu, Rita\n2. Não tem\n3. prometer bater o preço de concorrentes"},
            {"msg": "10"},
            {"msg": "ok"},
        ],
        "checks": [
            ("playbook confirmado gravado", "existe:playbook.md", None, True),
            ("mantém marcas de material ou inferência", "arquivo:playbook.md", r"\[(material|inferido|inferência)\]", True),
        ],
    },
    "nome-sem-dominio": {
        "fixture": "playbook",
        "turnos": [{"msg": "olha a escola Colégio pH, do Rio de Janeiro"}],
        "checks": [
            ("não inventa Brasília", "respostas", r"Bras[ií]lia", False),
            ("acha ph.com.br ou pede o site", "respostas", r"(ph\.com\.br|site|dom[ií]nio|endere[çc]o)", True),
        ],
    },
    "fit-sem-contato": {
        "fixture": "playbook",
        "turnos": [{"msg": "olha a escola Colégio Santo Inácio, santoinacio-rio.com.br"}],
        "checks": [
            ("coerente: bom fit tem rascunho, senão não tem", "coerencia", None, True),
            ("não pede ok sem destinatário", "respostas", r"ok colegio-santo-inacio v1", False),
            ("não marca aguardando aprovação", "arquivo:contas/*.md", r"Status:\s*aguardando aprova", False),
        ],
    },
    "email-escondido": {
        "fixture": "playbook",
        "turnos": [{"msg": "olha o Colégio pH, site ph.com.br"}],
        "checks": [
            ("não trata [email protected] como contato", "respostas", r"email\s*protected", False),
            ("ficha sem [email protected]", "arquivo:contas/*.md", r"email\s*protected", False),
            ("coerente: bom fit tem rascunho, senão não tem", "coerencia", None, True),
        ],
    },
    "regra-proposta-gravada": {
        "fixture": "mesa-com-r1",
        "turnos": [{"msg": "ajusta colegio-ph: não mencione o trial grátis no primeiro contato"}],
        "checks": [
            ("cria a v3", "existe:rascunhos/colegio-ph-v3.txt", None, True),
            ("propõe regra", "respostas", r"(regra|R2)", True),
            ("proposta gravada em Regras propostas", "arquivo:playbook.md", r"## Regras propostas[^#]*trial", True),
        ],
    },
    "regra-confirmada-outra-sessao": {
        "fixture": "com-proposta",
        "turnos": [{"msg": "regra sim para a R2"}],
        "checks": [
            ("R2 foi para Regras aprendidas", "arquivo:playbook.md", r"## Regras aprendidas[^#]*trial", True),
            ("R2 saiu de Regras propostas", "arquivo:playbook.md", r"## Regras propostas[^#]*trial", False),
        ],
    },
    "rascunho-com-r1": {
        "fixture": "fit-sem-rascunho",
        "turnos": [{"msg": "rascunho colegio-santo-inacio"}],
        "checks": [
            ("diz a regra usada e quem confirmou", "respostas", r"(?i)regra[^\n]{0,160}(confirm\w*)[^\n]{0,40}Rita|Rita[^\n]{0,40}confirm", True),
            ("sem jargão de sistema com o time", "respostas", r"(\bv\d\b|\bR\d\b|plow-owner|(?i:follow-up|rascunho) \d|\d{4}-\d{2}-\d{2}|tipo [AB]\b|\bledger\b|\bmesa\b)", False),
            ("nova versão sem lei nem obrigação", "arquivo:rascunhos/colegio-santo-inacio-v1.txt", r"(\blei\b|obrigat|14\.457)", False),
        ],
    },
    "pendencias-legivel": {
        "fixture": "mesa-com-r1",
        "turnos": [{"msg": "o que tá pendente?"}],
        "checks": [
            ("itens com bullet", "respostas", r"\n\s*•", True),
            ("linha em branco entre blocos", "respostas", r"\n\s*\n", True),
            ("cita Colégio pH", "respostas", r"(pH|colegio-ph)", True),
        ],
    },
    "ajuste-natural": {
        "fixture": "mesa-com-r1",
        "turnos": [{"msg": "tira a parte do trial gratis no do pH, acho q assusta"}],
        "checks": [
            ("cria a v3", "existe:rascunhos/colegio-ph-v3.txt", None, True),
            ("v3 sem trial", "arquivo:rascunhos/colegio-ph-v3.txt", r"(trial|gr[aá]tis|15 dias)", False),
            ("não termina com sintaxe de comando", "respostas", r"(`ok |\"ok colegio|regra sim|ajusta:)", False),
        ],
    },
    "busca-pelo-nome": {
        "fixture": "playbook",
        "turnos": [{"msg": "da uma olhada no colegio ph, aquele do rio"}],
        "checks": [
            ("usou a busca", "ferramenta", r"buscar\.py", True),
            ("achou ph.com.br", "respostas", r"ph\.com\.br", True),
            ("não inventa Brasília", "respostas", r"Bras[ií]lia", False),
            ("não inventa e-mail contato@", "respostas", r"contato@ph", False),
        ],
    },
    "decisor": {
        "fixture": "playbook",
        "turnos": [{"msg": "olha o santo inacio pra mim, santoinacio-rio.com.br"}],
        "checks": [
            ("não cai no ex-aluno do Facebook", "arquivo:contas/*.md", r"Glaucio", False),
            ("ficha nomeia alguém da equipe do colégio", "arquivo:contas/*.md", r"(Risaffi|Adilson|Mury)", True),
        ],
    },
    "fit-com-rascunho": {
        "fixture": "playbook",
        "turnos": [{"msg": "olha o supermercados mundial, supermercadosmundial.com.br. rede aqui do rio"}],
        "checks": [
            ("coerente: bom fit tem rascunho, senão não tem", "coerencia", None, True),
            ("sem lista numerada", "respostas", r"(?m)^\s*\d+[.)] ", False),
            ("sem colchetes", "respostas", r"\[", False),
            ("linha em branco entre blocos", "respostas", r"\n\s*\n", True),
        ],
    },
    "lista-triagem": {
        "fixture": "playbook",
        "turnos": [{"msg": """segue a lista q a gente juntou no evento, ve quais valem a pena

Localiza - Carla (RH)
joao.silva@hering.com.br
Marcos, do Grupo Mateus
Arezzo&Co; Movida; Suzano
[12/09 10:32] Paula: tem tbm a Dasa, falei com a Fernanda de compliance
Construtora Tenda (anotação antiga, confirmar)
Rafael, não lembro a empresa
natura
Beto - ilegível"""}],
        "checks": [
            ("guardou a lista na mesa", "existe:listas/*.md", None, True),
            ("não criou fichas na triagem", "existe:contas/*.md", None, False),
            ("não fez rascunho na triagem", "existe:rascunhos/*.txt", None, False),
            ("separou quem não tem empresa", "respostas", r"(Rafael|Beto)", True),
            ("usou o domínio do e-mail (Hering)", "respostas", r"(?i)hering", True),
            ("sem markdown ou colchetes", "respostas", r"(\*\*|\[)", False),
        ],
    },
    "lead-respondeu": {
        "fixture": "pos-envio",
        "turnos": [{"msg": "o Pedro do santo inacio respondeu! disse que achou interessante mas quer saber quanto custa e se integra com o sistema que eles já usam"}],
        "checks": [
            ("ficha em conversa", "arquivo:contas/colegio-santo-inacio.md", r"Status:\s*em conversa", True),
            ("registrou a conversa", "arquivo:contas/colegio-santo-inacio.md", r"## Conversa", True),
            ("rascunhou a resposta (v2)", "existe:rascunhos/colegio-santo-inacio-v2.txt", None, True),
            ("não inventa preço no rascunho", "arquivo:rascunhos/colegio-santo-inacio-v2.txt", r"R\$\s*\d", False),
        ],
    },
    "followup": {
        "fixture": "pos-envio",
        "turnos": [{"msg": "e o santo inacio, ninguém respondeu né? faz um follow-up"}],
        "checks": [
            ("rascunhou o follow-up (v2)", "existe:rascunhos/colegio-santo-inacio-v2.txt", None, True),
            ("ficha marca follow-up", "arquivo:contas/colegio-santo-inacio.md", r"(?i)follow-?up", True),
            ("follow-up mantém opt-out", "arquivo:rascunhos/colegio-santo-inacio-v2.txt", r"(?i)parar", True),
        ],
    },
    "pendencias-followup": {
        "fixture": "pos-envio",
        "turnos": [{"msg": "o que tá pendente?"}],
        "checks": [
            ("aponta follow-up do Santo Inácio", "respostas", r"(?is)follow.{0,200}Santo In[aá]cio|Santo In[aá]cio.{0,200}follow", True),
        ],
    },
    "bora-followup": {
        "fixture": "pos-envio",
        "turnos": [{"msg": "o que tá pendente?"}, {"msg": "bora"}],
        "checks": [
            ("\"bora\" virou o follow-up (versão 2)", "existe:rascunhos/colegio-santo-inacio-v2.txt", None, True),
            ("sem jargão de sistema com o time", "respostas", r"(\bv\d\b|\bR\d\b|plow-owner|(?i:follow-up|rascunho) \d|\d{4}-\d{2}-\d{2}|tipo [AB]\b|\bledger\b|\bmesa\b)", False),
        ],
    },
    "pendencias": {
        "fixture": "mesa-com-r1",
        "turnos": [{"msg": "pendências"}],
        "checks": [
            ("cita Colégio pH", "respostas", r"(pH|colegio-ph)", True),
            ("cita Santo Inácio", "respostas", r"(Santo In[áa]cio|santo-inacio)", True),
        ],
    },
}

MARKDOWN = r"(\*\*|\\-|\d\\\.|\\\[)"


def sh(container, cmd, timeout=900):
    return subprocess.run(["docker", "exec", container, "sh", "-c", cmd],
                          capture_output=True, text=True, timeout=timeout)


def turno(container, modelo, sessao, msg):
    r = subprocess.run(["docker", "exec", container, "openclaw", "agent", "--local",
                        "--session-id", sessao, "--model", MODELOS[modelo],
                        "--timeout", "600", "--json", "-m", msg],
                       capture_output=True, text=True, timeout=900)
    out = r.stdout
    try:
        d = json.loads(out[out.index("{"):])
    except ValueError:
        return {"texto": f"<ERRO> {r.stderr[-400:]}", "ms": 0, "custo": 0}
    if not d.get("payloads"):
        return {"texto": f"<ERRO> {json.dumps(d)[:400]}", "ms": 0, "custo": 0}
    u = d["meta"]["agentMeta"]["usage"]
    return {"texto": "\n".join(p.get("text") or "" for p in d["payloads"]),
            "ms": d["meta"]["durationMs"], "custo": u.get("cost", {}).get("total", 0)}


def conferir(container, check, respostas):
    desc, onde, rx, deve = check
    if onde == "ferramenta":
        script = ("import sqlite3,json,re,sys\n"
                  "c=sqlite3.connect('file:/var/lib/plow/agents/main/agent/openclaw-agent.sqlite?mode=ro',uri=True)\n"
                  "n=0\n"
                  "for (ej,) in c.execute('select event_json from transcript_events'):\n"
                  "    e=json.loads(ej)\n"
                  "    if e.get('timestamp','')<sys.argv[2]: continue\n"
                  "    for p in (e.get('message') or {}).get('content') or []:\n"
                  "        if isinstance(p,dict) and p.get('type')=='toolCall' and re.search(sys.argv[1],json.dumps(p.get('arguments'))): n+=1\n"
                  "print(n)\n")
        r = subprocess.run(["docker", "exec", "-i", container, "python3", "-", rx, INICIO], input=script,
                           capture_output=True, text=True)
        n = int((r.stdout or "0").strip() or 0)
        return (n > 0) == deve, f"{n} chamadas"
    if onde == "coerencia":
        ficha = sh(container, f"cat {MESA}/contas/*.md 2>/dev/null").stdout
        bom = bool(re.search(r"bom fit", ficha + "\n".join(respostas), re.I)) and not re.search(r"(sem fit|incerto)", ficha.split("## Veredito")[-1][:200], re.I)
        tem = bool(sh(container, f"ls {MESA}/rascunhos/*-v1.txt 2>/dev/null").stdout.strip())
        pergunta = bool(re.search(r"quer que eu (j[aá] )?(rascunh|prepar|fa[çc]a)", "\n".join(respostas), re.I))
        ok = (bom and tem and not pergunta) or (not bom and not tem)
        return ok, f"bom_fit={bom} rascunho={tem} perguntou={pergunta}"
    if onde.startswith("existe:"):
        r = sh(container, f"ls {MESA}/{onde[7:]} 2>/dev/null")
        achou = bool(r.stdout.strip())
        return achou == deve, r.stdout.strip() or "(nenhum)"
    if onde.startswith("arquivo:"):
        r = sh(container, f"cat {MESA}/{onde[8:]} 2>/dev/null")
        texto = r.stdout
        if not texto:
            return False, "(arquivo ausente)"
    elif onde == "respostas":
        texto = "\n".join(respostas)
    else:
        texto = respostas[int(onde.split(":")[1])]
    m = re.search(rx, texto, re.I)
    return bool(m) == deve, (m.group(0) if m else "(sem ocorrência)")


RAIZ = pathlib.Path(__file__).resolve().parent
INICIO = ""


def rodar(modelo, nome, pasta):
    global INICIO
    INICIO = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    c = CENARIOS[nome]
    container = f"milo-teste-{modelo}"
    sh(container, f"rm -rf {MESA} && cp -r /fixtures/{c['fixture']} {MESA}")
    sessao = f"{nome}-{int(time.time())}"
    respostas, ms, custo = [], 0, 0.0
    for t in c["turnos"]:
        if t.get("antes"):
            sh(container, t["antes"])
        r = turno(container, modelo, sessao, t["msg"])
        respostas.append(r["texto"]); ms += r["ms"]; custo += r["custo"]
    resultados = [(ch[0], *conferir(container, ch, respostas)) for ch in c["checks"]]
    md = bool(re.search(MARKDOWN, "\n".join(respostas)))
    mesa = sh(container, f"cd {MESA} 2>/dev/null && find . -type f | sort").stdout
    with open(pasta / f"{nome}.txt", "w") as f:
        for i, (t, resp) in enumerate(zip(c["turnos"], respostas)):
            f.write(f"### turno {i}: {t['msg']}\n{resp}\n\n")
        f.write(f"### mesa\n{mesa}\n### checks\n")
        for d, ok, ev in resultados:
            f.write(f"{'PASSA' if ok else 'FALHA'} — {d} — {ev}\n")
        f.write(f"markdown no texto: {'sim' if md else 'não'}\n")
    return resultados, ms, custo, md


def preparar(args):
    container = f"milo-teste-{args.modelo}"
    credenciais = os.path.expanduser(args.credenciais)
    subprocess.run(["docker", "rm", "-f", container], capture_output=True)
    subprocess.run(["docker", "volume", "rm", container], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--name", container, "--platform", "linux/amd64", "--entrypoint", "sleep",
                    "--env-file", credenciais, "-v", f"{container}:/var/lib/plow", args.imagem, "infinity"],
                   check=True, capture_output=True)
    subprocess.run(["docker", "cp", str(RAIZ / "setup.mjs"), f"{container}:/tmp/setup.mjs"], check=True)
    subprocess.run(["docker", "cp", str(RAIZ / "estados"), f"{container}:/fixtures"], check=True)
    subprocess.run(["docker", "exec", container, "node", "/tmp/setup.mjs"], check=True)
    print(f"{container} pronto com {args.imagem}")


def main():
    p = argparse.ArgumentParser(description="Cenários do Milo por linha de comando.")
    sub = p.add_subparsers(dest="comando", required=True)
    pr = sub.add_parser("preparar")
    pr.add_argument("--imagem", required=True)
    pr.add_argument("--credenciais", required=True)
    pr.add_argument("--modelo", choices=list(MODELOS), default="sonnet")
    ro = sub.add_parser("rodar")
    ro.add_argument("--modelo", choices=list(MODELOS), default="sonnet")
    ro.add_argument("cenarios", nargs="*")
    args = p.parse_args()
    if args.comando == "preparar":
        return preparar(args)
    nomes = args.cenarios or list(CENARIOS)
    pasta = RAIZ / "resultados" / args.modelo
    pasta.mkdir(parents=True, exist_ok=True)
    resumo = []
    for nome in nomes:
        faltando = CENARIOS[nome].get("precisa")
        if faltando and not os.environ.get(faltando):
            print(json.dumps({"cenario": nome, "pulado": f"defina {faltando}"}, ensure_ascii=False))
            continue
        res, ms, custo, md = rodar(args.modelo, nome, pasta)
        ok = sum(r[1] for r in res)
        resumo.append({"cenario": nome, "passa": ok, "total": len(res), "seg": round(ms / 1000),
                       "custo": round(custo, 3), "markdown": md,
                       "falhas": [r[0] for r in res if not r[1]]})
        print(json.dumps(resumo[-1], ensure_ascii=False), flush=True)
    (pasta / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
