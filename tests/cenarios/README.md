# Cenários do Milo

Testes de comportamento por linha de comando: o Milo roda num contêiner com a
mesma imagem, o mesmo prompt e as mesmas skills, mas **sem o canal da Plow**.
Nenhuma mensagem vai para celular. Cada cenário recomeça a mesa a partir de um
estado em `estados/`, manda mensagens escritas como gente escreve e confere
respostas e arquivos.

```bash
docker build --platform linux/amd64 -t milo:dev .
python3 tests/cenarios/cenarios.py preparar --imagem milo:dev --credenciais ~/caminho/plow-credentials
python3 tests/cenarios/cenarios.py rodar fit-com-rascunho lista-triagem
```

- **Custa créditos reais** da conta Plow das credenciais: de US$ 0,20 (pendências)
  a US$ 2,50 (pesquisa completa) por cenário no Sonnet. Rode só os afetados pela
  mudança.
- **Sem remetente:** pela linha de comando ninguém é o dono. Aprovação, regra
  confirmada e grupo só se testam pelo celular.
- **Busca na web:** muitos cenários seguidos do mesmo IP podem ser bloqueados
  pelos buscadores; o Milo então cai no plano B (domínios prováveis).
- `onboarding-confirmado` só roda com `MILO_CENARIO_SITE=<url do site>`.
- Resultados em `tests/cenarios/resultados/<modelo>/` (fora do Git).

Os estados usam uma empresa fictícia (Integra) e pessoas fictícias. As contas
pesquisadas (Colégio pH, Colégio Santo Inácio, Supermercados Mundial) são
empresas reais, com informação pública dos próprios sites. Não coloque aqui
mesa, playbook ou lista de um piloto.
