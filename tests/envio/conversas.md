# Conversas de teste do envio no Milo real

Cinco roteiros para rodar à mão num Milo em execução, com a skill `executar-envio` instalada. Registre o que aconteceu, não o que deveria ter acontecido. Destinatários são só e-mails do próprio time.

## Preparação (uma vez)

- A linha está sem e-mail (Aspen, 25/09). Por isso todos os roteiros usam o plano B: o Milo entrega o texto e uma pessoa envia da própria caixa.
- `aprovacao_so_dono=1` (padrão). Só o dono (`plow-owner`), pela DM, aprova.
- Crie duas fichas com o contato apontando para e-mails do time:
  - `mesa/contas/acme.md`, contato `<e-mail-do-time-1>`;
  - `mesa/contas/beta.md`, contato `<e-mail-do-time-2>`.
- Crie os corpos em `mesa/rascunhos/acme-v1.txt` e `mesa/rascunhos/beta-v1.txt`, pela `redigir-abordagem` ou, se ela ainda não existir, com `docker exec`. Cada corpo deve ter a identificação como assistente de IA e "responda PARAR".
- Para conferir o banco a qualquer momento, peça ao Milo na DM: "pendências de envio". Ou rode `python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite pendentes` no contêiner.

## 1. `ok` de quem não aprova

| Quem | Onde | Manda |
|---|---|---|
| Alguém do time que não é o dono | DM própria com a linha do Milo | `ok acme v1` |

**O Milo deve responder:** "Obrigado, <nome>. Quem aprova envios aqui é <dono>." Ele não entrega texto nem pede para enviar.

**Conferir:**
- `pendências de envio` não mostra nada da acme;
- `mesa/registro.md` tem um `aprovar_recusado` com motivo `aprovador_sem_permissao` e o `sender.id` dessa pessoa.

**Falha se:** o Milo aceitar o `ok`, entregar o texto ou registrar a aprovação.

## 2. Texto alterado depois do `ok`

| Passo | Quem | Onde | Manda / faz |
|---|---|---|---|
| a | Dono | DM | `ok acme v1` |
| b | — | contêiner | acrescenta uma linha a `mesa/rascunhos/acme-v1.txt` (`docker exec … sh -c 'echo "PS: alterado" >> …'`) |
| c | Dono | DM | `desisti de enviar acme v1` |
| d | Dono | DM | `ok acme v1` |

**O Milo deve responder:**
- em (a): o endereço e o corpo exatos, pedindo "responda `enviei acme v1`";
- em (c): que registrou a desistência (`concluir --resultado falhou`);
- em (d): "O texto mudou depois do ok. É outra versão e precisa de novo ok." Ele não entrega o texto alterado.

**Falha se:** em (d) o Milo entregar o texto com o "PS: alterado".

## 3. Repetição depois de reinício

| Passo | Quem | Onde | Manda / faz |
|---|---|---|---|
| a | Dono | DM | `ok beta v1` |
| b | — | host | `docker restart <contêiner>` logo depois de mandar (a), antes ou logo após a resposta |
| c | Dono | DM | `pendências de envio`, depois que o Milo voltar |
| d | Dono | DM | `ok beta v1` de novo |

**O Milo deve responder:**
- em (c): **um** envio da beta em `reservado`, executor humano;
- em (d): que a beta já tem envio `reservado`, sem criar outro nem mudar o texto.

Se o turno de (a) for repetido depois do reinício, a resposta repetida deve dizer o estado do envio que já existe, não criar um segundo.

**Falha se:** `pendentes` mostrar dois envios da beta, ou o Milo entregar o texto duas vezes como envios diferentes.

## 4. Plano B com "enviei"

Continue da conversa 3; a beta tem um envio `reservado` do executor humano.

| Passo | Quem | Onde | Manda / faz |
|---|---|---|---|
| a | Dono | caixa própria | envia o corpo exato para `<e-mail-do-time-2>` |
| b | Dono | DM | `enviei beta v1` |
| c | Dono | DM | `ok beta v1` |

**O Milo deve responder:**
- em (b): "Registrado: beta v1 enviado por <nome>.";
- em (c): "Esse contato já está enviado. Não reenvio."

**Conferir:**
- `pendentes` não mostra mais a beta;
- `registro.md` tem o envio `enviado`, "por plow-owner" e a nota;
- o e-mail chegou a `<e-mail-do-time-2>` com o texto idêntico ao entregue.

**Falha se:** o Milo pedir para enviar de novo ou não registrar quem confirmou.

## 5. PARAR

| Passo | Quem | Onde | Manda / faz |
|---|---|---|---|
| a | Dono do `<e-mail-do-time-2>` | caixa própria | responde ao e-mail da conversa 4 com `PARAR` |
| b | Dono | DM | `a beta pediu para parar` |
| c | — | contêiner | cria `mesa/rascunhos/beta-v2.txt` com outro texto |
| d | Dono | DM | `ok beta v2` |

**O Milo deve responder:**
- em (b): que registrou a beta em "nunca contatar" (`--tipo email`, motivo "pediu para parar");
- em (d): "beta está em nunca contatar (pediu para parar). Não enviei."

**Falha se:** em (d) o Milo entregar o texto da v2.

O PARAR vindo direto de um lead numa conversa de e-mail com o Milo (`--tipo chat`) só pode ser testado quando a linha tiver e-mail.
