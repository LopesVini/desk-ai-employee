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

## Troca de idioma na mesma sessão

- `idioma-portugues-ingles`: quatro turnos, dois em português e dois em inglês;
  verifica a conversa em inglês, APPROVE, ausência de APROVO e de afirmação de
  envio, mantendo o outreach no idioma português do playbook.
- `idioma-ingles-portugues`: três turnos, um em inglês e dois em português;
  verifica a troca para português, APROVO e ausência de APPROVE e de afirmação
  de envio.

Os checks `conversa:<n>` retiram apenas o outreach salvo e seus cabeçalhos da
resposta daquele turno. Assim o email em português não mascara nem faz falhar
os checks do wrapper em inglês. As regexes são sinais de idioma, não uma
classificação completa: na execução com modelo, confira também a resposta
inteira. Os cenários existentes continuam inalterados.
