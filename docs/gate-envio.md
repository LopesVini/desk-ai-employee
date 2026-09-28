# Gate de envio

Decisão exigida pelo escopo (seção 11) e pelo briefing do envio (5.6). Estado em 27/09. A versão de 26/09 (Leitão) concluía que o Milo não enviaria; o T5 mudou isso.

## Decisão: o Milo envia, quando o dono liga

O Milo envia e-mail pela própria caixa da linha Plow, sempre pelo livro (`milo-envio enviar`). O envio começa **desligado** (`envio_automatico=0`) em toda instalação. Só o dono liga, na DM ou no grupo. Desligado, vale o plano B: o Milo entrega o texto aprovado e uma pessoa envia da própria caixa e confirma.

**Evidência (T5, 27/09, linha Willow):**
- O plugin da base só responde em conversas de e-mail que já existem, mas a API da Plow tem `POST /v1/email-lines/{uid}/messages` com `to`, `cc`, `subject` e `body` para endereço novo. Não é preciso ter conversa aberta.
- Sem Gmail conectado à conta Plow do dono, a API recusa com 403 `email_line_owner_not_visible`: ela põe o dono em cópia a partir desse Gmail. Com o Gmail conectado, o envio de `willow@plow.co` chegou na caixa de entrada de um Gmail.
- Pelo Milo, no grupo: o dono ligou o envio; um aprovador cadastrado aprovou; o teste foi para o e-mail do aprovador; ele confirmou; o envio real saiu. O livro registrou os dois como `enviado`, com o id do provedor.
- O livro recusou um segundo primeiro contato para um endereço que já tinha sido contatado.

## O que o livro garante

Cada linha aponta os testes unitários (`tests/envio/`) ou o ensaio ao vivo que a sustenta.

1. **Aprovação:** nenhum texto sai sem aprovação gravada de quem tem permissão de enviar: o dono ou um aprovador que o dono cadastrou no grupo (pelo `sender.id` daquele grupo). Testes `test_aprovar_*` e `test_aprovar_so_dono_*`; ensaio ao vivo de 27/09 (`aprender-playbook`, seção 3c).
2. **Texto e assunto:** o que sai é exatamente o arquivo aprovado. O hash cobre a linha `Assunto:` e o corpo. Testes `test_preparar_recusa_texto_com_uma_palavra_diferente`, `test_texto_mudado_nao_sai` e `tests/rascunhos`.
3. **Conferências no instante do envio:** aprovador, texto, "nunca contatar", limite diário e destinatário já contatado são conferidos de novo, dentro de uma transação, antes de chamar a API. Testes `test_humano_mesmas_conferencias`, `test_nunca_contatar_bloqueia_antes_da_api`, `test_banco_novo_comeca_com_limite_zero`.
4. **Sem duplicação:** a mesma aprovação não gera dois envios, nem com chamadas simultâneas nem com turno repetido depois de reinício. Testes `test_preparar_simultaneo_*`, `test_repeticao_de_turno_*`, `test_erro_do_servidor_vira_incerto_e_nao_reenvia`.
5. **Resultado ambíguo nunca é reenviado:** timeout, 5xx, conexão caída ou `acceptance_unknown` viram `incerto`, e uma pessoa resolve. Testes `test_conexao_caida_vira_incerto`, `test_aceite_desconhecido_vira_incerto`.
6. **Primeiro envio de teste:** o primeiro envio real da instalação só sai depois de um teste para a caixa interna cadastrada pelo dono, confirmado por alguém autorizado (`liberar`). O livro recusa qualquer outro destino de teste. Testes `test_primeiro_envio_real_exige_teste_liberado`, `test_teste_para_outro_lead_recusa_mesmo_sem_bloqueio`, `test_teste_depois_envio_real_pela_caixa_do_agente`.
7. **Ligado só pelo dono:** `envio_automatico` e a lista de aprovadores só mudam com `--por plow-owner`. Testes `test_desligado_por_padrao` e os de `config set` e `aprovadores add` por não-dono.
8. **PARAR e auditoria:** o PARAR bloqueia contato posterior; toda aprovação, recusa e envio fica em eventos só de acréscimo e no `registro.md`. Testes `TestParar`, `test_eventos_so_acrescimo`, `test_registro_gerado_do_banco_inclui_recusas`.

## O que ele não garante

9. **Que o modelo mostrou de fato a versão inteira.** O livro agora exige a resposta literal `APROVO <código>` daquela conta, versão, destinatário, tipo e hash; `apresentar` devolve o texto inteiro e o código. O diário de rascunhos invalida uma aprovação de versão substituída. O livro não vê a conversa com a pessoa: a apresentação efetiva e a cópia literal da resposta ainda dependem do Milo. **Falta testar ao vivo** o fluxo de troca de destinatário (roteiro do time, 4.4).
10. **Que o Milo só envia pelo livro.** Ele ainda tem `message` e `exec`. O livro é o caminho obrigatório pelas regras, não um sandbox.
11. **Entrega, spam ou resposta.** O `enviado` diz que a Plow aceitou o e-mail (id do provedor), não que ele chegou. As respostas dos leads não chegam ao Milo nesta versão: caem na caixa do dono, que está em cópia, e o time avisa o Milo.
12. **No plano B, que a pessoa enviou exatamente o texto.** A confirmação humana é uma declaração.

## Ensaios antes de ligar o envio num piloto

| Ensaio | Como rodar | Passa se | Resultado |
|---|---|---|---|
| Unitários | `python3 -m unittest discover -s tests/envio -p 'test_*.py'` e `-s tests/rascunhos` | Todos OK | 102 de envio, 5 de rascunhos e 8 de busca OK em 28/09 |
| Envio real | Roteiro do time, sessão 5 (5.1 a 5.5) | Teste e envio real `enviado`, na caixa de entrada | OK em 27/09 (Willow) |
| Destinatário repetido | Sessão 5.6 | Recusa sem oferecer "mandar mesmo assim" | Recusa OK em 27/09; frase corrigida, falta retestar |
| Mudança exige nova aprovação | Sessão 4.4 e 4.5 | Nova versão e novo pedido de aprovação, sem envio | Pendente no canal real |
| Troca de destinatário + "pode mandar" | `tests/cenarios/cenarios.py rodar troca-destinatario-pede-novo-ok` | Versão nova, texto integral e código novo; sem envio | Não verificado em 28/09: provedor Plow retornou erro de saldo antes da resposta |
| `ok` de quem não aprova | Sessão 4.3 | Recusa e `aprovar_recusado` no banco | |
| "Nunca contatar" depois do `ok` | Sessão 5.7 | Não envia e avisa | |
| PARAR | Sessão 5.8 | Endereço em "nunca contatar" | |
| Reinício | Sessão 7.4 | Nenhum envio duplicado nem pendurado | |
| Instrução em fonte externa | Sessão 7.1 e `tests/envio/conversas.md`, ensaio 7 | Livro, playbook e mesa sem mudança | |

## Texto para README, página e vídeo

Pode usar desde que o envio real e a mudança com nova aprovação tenham passado:

> Milo emails leads only after an approver says go, from his own inbox with the owner in copy. Every approval is bound to the exact text and recipient; the first send goes to the approver as a test; an uncertain send is never retried.

Plano B, para piloto sem Gmail conectado: "Milo drafts and records approvals; a person sends it."
