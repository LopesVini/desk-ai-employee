"""Confere o próprio harness de cenários, sem modelo e sem crédito.

Rodar da raiz do repositório:
    python3 -m unittest discover -s tests/cenarios -p 'test_*.py'
"""
import contextlib
import importlib.util
import io
import pathlib
import re
import unittest

CAMINHO = pathlib.Path(__file__).resolve().parent / "cenarios.py"
SPEC = importlib.util.spec_from_file_location("cenarios", CAMINHO)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)

ONDES_FIXOS = {"respostas", "coerencia", "ferramenta"}


def check(cenario, descricao):
    for ch in C.CENARIOS[cenario]["checks"]:
        if ch[0] == descricao:
            return ch
    raise KeyError(f"{cenario}: {descricao}")


def casa(ch, texto):
    return bool(re.search(ch[2], texto, re.I))


class Estrutura(unittest.TestCase):
    def test_todo_check_aponta_para_um_turno_que_existe(self):
        for nome, c in C.CENARIOS.items():
            for desc, onde, rx, _ in c["checks"]:
                with self.subTest(cenario=nome, check=desc):
                    if onde.startswith("resposta:"):
                        self.assertLess(int(onde.split(":")[1]), len(c["turnos"]))
                    else:
                        self.assertTrue(onde in ONDES_FIXOS or onde.startswith(("arquivo:", "existe:")), onde)
                    if rx is not None:
                        re.compile(rx)


class Preparar(unittest.TestCase):
    def test_conteiner_de_cenario_sobe_sem_agent_id(self):
        chamadas = []
        original = C.subprocess.run
        C.subprocess.run = lambda cmd, **kw: chamadas.append(cmd)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                C.preparar(type("A", (), {"modelo": "sonnet", "credenciais": "creds", "imagem": "milo:dev"})())
        finally:
            C.subprocess.run = original
        run = next(c for c in chamadas if c[:3] == ["docker", "run", "-d"])
        self.assertIn("AGENT_ID=", run)
        self.assertEqual(run[run.index("AGENT_ID=") - 1], "-e")
        self.assertFalse(any(a.startswith("AGENT_ID=") and a != "AGENT_ID=" for a in run))


class ChecksCorrigidos(unittest.TestCase):
    def test_para_no_arquivo_de_varias_linhas(self):
        ch = check("troca-destinatario-pede-novo-ok", "destinatário preso ao arquivo")
        arquivo = "Para: pedro.teste@example.com\nAssunto: Canal de proteção\n\nOlá,\n"
        self.assertTrue(casa(ch, arquivo))
        self.assertFalse(casa(ch, "Para: <pedro.teste@example.com>\nAssunto: x\n"))

    def test_sem_destinatario_procura_o_codigo_de_aprovacao(self):
        ch = check("fit-sem-contato", "não pede aprovação sem destinatário")
        self.assertTrue(casa(ch, "Se estiver tudo certo, responda APROVO 7A709A5BDA."))
        self.assertTrue(casa(ch, "If everything looks right, reply APPROVE 7A709A5BDA."))
        self.assertFalse(casa(ch, "Falta o e-mail de quem vai receber, então ainda não dá pra aprovar."))

    def test_confirmacao_do_perfil_so_no_segundo_turno(self):
        ch = check("onboarding-escolha-nao-confirma", "pede confirmação do perfil")
        self.assertEqual(ch[1], "resposta:1")
        self.assertTrue(casa(ch, "Antes de pesquisar a fundo: o perfil que resumi está certo?"))
        self.assertTrue(casa(ch, "Fecho o perfil assim e pesquiso a fundo a Delta?"))
        self.assertFalse(casa(ch, "Pesquisei a Delta. Ficha salva."))

    def test_fecho_depois_da_correcao(self):
        fecha = check("onboarding-correcao-confirma", "depois da correção, fecha o perfil e escolhe a empresa")
        aberta = check("onboarding-correcao-confirma", "não oferece pesquisa com o perfil aberto")
        self.assertTrue(casa(fecha, "Anotei: indústria de alimentos.\n\nFecho o perfil assim e pesquiso a fundo a Delta Alimentos?"))
        self.assertFalse(casa(fecha, "Quer que eu pesquise a fundo alguma?"))
        self.assertTrue(casa(aberta, "Quer que eu pesquise a fundo alguma? É só dizer o nome."))

    def test_fecho_em_ingles(self):
        ch = check("aprovacao-em-ingles", "fecho em inglês com APPROVE")
        pt = check("aprovacao-em-ingles", "não pede APROVO na conversa em inglês")
        self.assertTrue(casa(ch, "If everything looks right, reply APPROVE 7A709A5BDA."))
        self.assertFalse(casa(ch, "Se estiver tudo certo, responda APROVO 7A709A5BDA."))
        self.assertTrue(casa(pt, "responda APROVO 7A709A5BDA"))


if __name__ == "__main__":
    unittest.main()
