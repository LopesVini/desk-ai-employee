# Replay histórico Milo × Jev — 29/09/2026

Branch local `codex/jev-shadow-pr15`. Dataset pré-rotulado: `tests/jev/real_replay_cases.json`. SHA-256 durante a avaliação: `767916de8b3f406fd38201ae8760673f08a2b250a2d88b06f96aadd82a0349bb`; SHA-256 atual após trocar somente o caminho absoluto da sessão por uma referência de nome: `aa08166341706b46f76d2945357c4eadcbb5befecd77ccb0c17fe5a62735a5ee`. Runner: `tests/jev/run_real_replay.py`. Para reproduzir a validação histórica, defina `JEV_HISTORICAL_SESSION` para a cópia local do transcript referido no dataset. Resultados e log estruturado ficam apenas em `tests/jev/results/` (ignorado pelo Git). Nenhum veredito ou ação do Milo foi alterado; as duas chamadas registraram `decision_applied=milo_unchanged`.

## Método e limites

As respostas e fichas históricas foram recuperadas literalmente do transcript local `rollout-2026-09-26T21-47-22-01a0e054-b201-7d22-b002-40b3e0995602.jsonl`. O runner verifica a presença textual de cada citação no ordinal indicado antes da chamada. F011/F012/F013/F015 foram lidas dos registros da mesa capturados no mesmo transcript, depois da resposta inicial, mas com indicação de criação anterior a ela. Os trechos enviados ao Jev são **recortes das notas de fonte contemporâneas**, não capturas brutas das páginas. A transcrição das notas pode carregar erros do Milo; portanto esta amostra não mede verificação independente da web. Nenhum dado interno de Bitrix/eSocial, contato pessoal, telefone ou email foi enviado.

Há duas qualificações históricas, ambas com veredito **incerto**, que era adequado diante dos dados faltantes. O comparativo principal abaixo é **por afirmação pública**, não accuracy de veredito. São quatro afirmações em duas contas (limite de duas por conta). A amostra foi escolhida por risco conhecido, não aleatoriamente. O rótulo esperado foi fixado antes das chamadas a partir das notas e correções históricas; não houve rotulagem humana cega e independente. O caso Consult/CNPJ tem saída ambígua e foi retirado da métrica principal.

## Casos e resultado

`P` é a probabilidade da classe escolhida por Jev. Usage e latência são **por chamada**, compartilhados pelas duas linhas da mesma conta; não somar duas vezes.

| Caso e evidência disponível na época | Milo real → rótulo auditado | Jev; P / confidence | HTTP; latência | Usage e custo estimado da chamada | Julgamento |
|---|---|---|---|---|---|
| `consult_founding`: F011, site institucional; output ordinal 1457: “Fundada em 2016” | supported → supported | supported; 0,98 / 0,98 | 200; 770 ms | 810 in / 108 out; US$ 0,000034020 | Duplicação correta |
| `consult_snippet_cnpj`: F012, snippets não abertos; ficha ordinal 1468 pôs o CNPJ sob “Fatos”, mas também avisou “não confirmado por leitura própria” | supported* → insufficient | insufficient; 1,00 / 1,00 | 200; 770 ms | Mesma chamada Consult | Sinal útil; **fora do placar principal** pela ressalva explícita de Milo |
| `santana_aggregator_provenance`: F013, página do agregador MonitorCNPJ; output ordinal 1659 atribuiu o registro à “própria Receita Federal” | supported → insufficient | insufficient; 0,90 / 0,86 | 200; 519 ms | 863 in / 111 out; US$ 0,000036246 | Erro de proveniência sinalizado |
| `santana_preserves_namesake`: F015, snippet LinkedIn não aberto; ficha ordinal 1670 disse “claramente diferente”, com ressalva contraditória adiante | supported → insufficient | insufficient; 0,61 / 0,48 | 200; 519 ms | Mesma chamada Santana | Certeza excessiva sinalizada; confiança baixa |

F011 dizia também “22 logos”, depois corrigidos para 20 únicos. Esse erro de extração visual não é pontuado: a própria nota F011 continha o número errado, e o Jev textual recebe apenas o trecho que Milo entrega. A suposta contradição EPP × capital social dependia da regra legal de porte, fora do contrato atual de suporte por trecho. CTA inventada e próxima ação incorreta são decisões de playbook, também fora do contrato. Não se fabricou uma resposta antiga do Milo para esses casos.

Foram procurados relatórios, cenários/regressões e transcripts disponíveis. Não apareceram seis pares íntegros de **fonte contemporânea + saída real da qualificação**. Os demais cenários da branch são testes com estado fictício ou resumos sem o trecho original da fonte. Por isso o replay ficou em quatro afirmações de duas contas, sem acrescentar exemplos artificiais. A ficha Santana também qualifica o snippet como “pista, não fato confirmado” depois de dizer “claramente diferente”; a classificação de erro refere-se à frase categórica na seção de fatos e deve ser tratada como interpretação auditada, não como erro cego incontestável.

## Métricas

Em três afirmações comparáveis: Milo **1/3 (33,3%)**, Jev **3/3 (100%)**; `rescued_errors=2`, `harmful_disagreements=0`, confirmação/duplicação `=1`. No quarto item ambíguo, Jev acertou o rótulo do trecho, mas não se atribui um erro binário ao Milo. Os dois vereditos de qualificação `incerto` estavam corretos; Jev não decidiu fit. São números descritivos desta seleção, não estimativas de accuracy futura. As duas chamadas foram HTTP 200, sem falhas: Consult 770 ms, 810 tokens de entrada/108 de saída; Santana 519 ms, 863/111. Latência média **644,5 ms por chamada**. Usage total **1.673 tokens de entrada e 219 de saída**. A [tabela oficial do Jev 1.13](https://docs.typesafe.ai/models) informa US$ 0,042 por milhão de tokens de entrada e saída gratuita: custo **estimado US$ 0,000070266**; nenhuma cobrança efetiva foi retornada pela API. O [contrato da API](https://docs.typesafe.ai/api) fornece as probabilidades e `confidence` das respostas.

## Advisory simulado e decisão

Nos três casos principais, as duas discordâncias Jev × Milo tiveram `confidence` 0,86 e 0,48. Um corte acima de 0,86 não mostraria nenhuma; um corte maior que 0,48 e até 0,86 mostraria uma; um corte até 0,48 mostraria duas. Não há discordância prejudicial observada, mas apenas um acerto do Milo e nenhuma amostra aleatória ou rotulagem cega. Escolher agora um limiar seria ajuste à própria amostra. Mesmo uma indicação exibida ao Milo não garante que ele corrigiria o texto; `rescued_errors` significa erros **sinalizados no replay**, não erros operacionalmente evitados.

**Recomendação: KEEP SHADOW.** O sinal sobre proveniência e homônimo foi útil, porém não há base para advisory. O próximo experimento precisa de mais qualificações concluídas, cópias brutas das fontes que Milo abriu, saídas literais, uma mistura pré-fixada de acertos e falhas e revisão humana cega antes de mostrar Jev. O contrato atual deve continuar restrito a afirmações públicas; veredito, rascunho, aprovação, envio e ledger permanecem intocados.

## End-to-end smoke

The later isolated Profarma qualification saved its account card and triggered the
OpenClaw post-step. The final linux/amd64 image recorded a direct TypeSafe HTTP
200 response in `mesa/jev-shadow.jsonl`: two claims, 387 ms, 803 input tokens,
105 output tokens and `decision_applied=milo_unchanged`. The test volume remained
separate from the production desk. Prospecting latency remains outside this PR.
