# milo-envio: interface e esquema

v1, 25/09. Responsável: Leitão. Escrito para quem faz a skill `executar-envio` sem ler o código.

## 1. O que é

`milo-envio` é o livro de aprovações e envios do Milo, guardado num SQLite. Ele registra quem aprovou o quê, confere tudo imediatamente antes do envio e reserva o envio para que não saia duas vezes. **Não é uma porta técnica**: o Milo continua tendo `message` e `exec` e pode contorná-lo (seção 8). O script impede erro e confusão. A regra "só envie por aqui" é do prompt.

Quando o Milo passa pelo script, fica garantido que:

1. Nada sai sem aprovação gravada de um aprovador com permissão.
2. O corpo enviado é o aprovado (hash).
3. "Nunca contatar", teste e limite diário são conferidos no momento do envio.
4. A mesma conta, destino e texto nunca geram dois envios. `reservado` ou `incerto` bloqueia até um humano resolver.
5. Depois de um reinício, `pendentes` mostra o que ficou pela metade.
6. `registro.md` é gerado a partir do banco, nunca editado à mão.

Se o T5 confirmar que o Milo não abre e-mail para endereço novo, nada aqui muda. O script continua valendo para threads que já existem: um lead que escreveu ao Milo, ou uma pessoa do time que abriu a thread com o Milo em cópia.

## 2. Como chamar

```
python3 {baseDir}/scripts/milo-envio.py <comando> [argumentos]
```

- **Banco:** `--db <caminho>` ou `$MILO_MESA/envios.sqlite`, com `MILO_MESA=/var/lib/plow/workspace/mesa`. Sem nenhum dos dois, recusa com `sem_banco`. O esquema é criado na primeira chamada.
- **Saída:** sempre uma linha JSON em stdout, `{"ok":true,…}` ou `{"ok":false,"motivo":"…",…}`.
- **Código de saída:**
  - 0: ok.
  - 1: recusa por regra.
  - 2: uso inválido.
  - 3: erro de banco, inclusive `banco_ocupado`.

  Com 2 ou 3, nada foi gravado. Não envie.
- **Horas:** UTC, ISO 8601.
- **`--aprovador` e `--por`:** sempre o `sender.id` da mensagem que motivou a ação, exatamente como veio do canal (uid Plow ou `plow-owner`). Nunca nome exibido, nunca telefone.

## 3. Destino, texto e identidade

- **Destino:** o `chat_uid` (`cht_…`) da conversa de e-mail. O endereço (`--para`) é só rótulo: serve para "nunca contatar" e para o registro.
  - O remetente é fixo, a linha de e-mail do Milo.
  - Não há assunto, cc nem responder-para: a ferramenta de envio da Plow aceita só o corpo.
- **Texto:** um arquivo com exatamente o corpo que vai sair, sem linha de assunto.
  - **Normalização antes do hash:**
    - exige UTF-8 e remove o BOM;
    - converte CRLF e CR em LF;
    - aplica Unicode NFC;
    - tira espaços e tabs do fim de cada linha;
    - tira linhas em branco do começo e do fim.
  - Nada além disso. Espaço duplo, aspas curvas e espaço não separável contam como diferença.
  - O hash é o SHA-256 do corpo normalizado.
- **Envio:** a skill envia o `chat` e o `corpo` que o `preparar` devolve, com `message(action="send", channel="plow", accountId="email", target=<chat>, message=<corpo>)`. Nada é remontado de memória.
- **Aprovadores:** identificados pelo `sender.id`.
  - `plow-owner` é o dono, identificado pelo próprio canal. Vem gravado na criação do banco, com permissão de enviar e de confirmar regras, e não pode ser alterado.
  - Os outros entram por `aprovadores add`, só a pedido do dono.
  - O uid de uma pessoa só é conhecido depois que ela escreve ao Milo. O Milo grava o uid que viu naquela mensagem, nunca um que alguém digitou.
- **Só o dono aprova:** a configuração `aprovacao_so_dono=1` é o padrão até o T1 provar que o `sender.id` é visível e estável [depende de T1]. Nesse modo, `aprovar` exige `--aprovador plow-owner` e `--canal dm`; `preparar` recusa aprovações que não cumpram isso; `liberar` e `resolver` exigem `--aprovador plow-owner`. Qualquer outro aprovador recebe `somente_dono`.
- **Chave de deduplicação:** SHA-256 de `conta | destino | hash_texto | teste-ou-real`. O destino é o `chat_uid` ou, no plano B, `email:<para>`.

## 4. Comandos

### aprovar

```
aprovar --conta <slug> --versao <n> --texto-arquivo <path> --chat <cht_…> --para <email>
        --aprovador <sender.id> --canal dm|grupo|email
```

Grava a aprovação. Confere:
- se o aprovador tem permissão de enviar e se a regra "só o dono" está sendo respeitada;
- o formato `cht_…`;
- se o e-mail do rótulo é válido;
- "nunca contatar";
- se o texto não está vazio.

É idempotente: com a mesma conta, versão, hash, chat e rótulo, devolve o mesmo id com `"existente":true`. Mesma conta e versão com qualquer diferença dá `versao_conflitante`.

→ `{"ok":true,"aprovacao_id":17,"hash":"…"}`

**Recusas:** `aprovador_sem_permissao`, `somente_dono`, `nunca_contatar`, `versao_conflitante`, `texto_vazio`, `texto_invalido`, `chat_invalido`, `email_invalido`. Toda recusa é gravada em `eventos`. Chame `aprovar` também quando o `ok` vier de quem não aprova: é assim que a recusa fica registrada.

### preparar

```
preparar --aprovacao <id> --texto-arquivo <path>
preparar --aprovacao <id> --texto-arquivo <path> --teste --chat <cht_… do aprovador> --para <email do aprovador>
```

Roda numa única transação (`BEGIN IMMEDIATE`). Confere nesta ordem:

1. A aprovação existe. Senão: `aprovacao_inexistente`.
2. Já existe envio desta aprovação, do mesmo tipo (teste ou real), em `reservado`, `incerto`, `enviado` ou `bloqueado`? Então devolve `envio_existente`, com `envio_id` e `estado`, e **não cria outro**. É aqui que cai a repetição de turno depois de um reinício.
3. O aprovador ainda tem permissão (e a regra "só o dono" continua respeitada). Senão: `aprovador_sem_permissao`.
4. O hash do arquivo é igual ao aprovado. Senão: `texto_diferente`.
5. *(real)* Nem o `chat_uid` nem o rótulo estão em "nunca contatar". Senão: `nunca_contatar`.
6. *(real)* O teste da instalação já foi liberado. Senão: `teste_pendente`.
7. *(real)* Não há outro envio real, com qualquer texto, para o mesmo chat ou rótulo em `reservado`, `incerto` ou `enviado`. Senão: `destinatario_ja_contatado`. Follow-up e resposta a lead são nível 2; se entrarem, esta regra muda.
8. *(real)* O limite diário não foi atingido. Senão: `limite_diario`.
9. A chave tem menos de 2 falhas. Senão: `falhas_esgotadas`.
10. Nenhuma outra aprovação tem a mesma chave em andamento. Senão: `duplicado`, com `envio_id` e `estado`.
11. Cria o envio como `reservado`.

→ `{"ok":true,"envio_id":31,"estado":"reservado","teste":false,"chat":"cht_…","corpo":"…"}`

**Só `ok:true` autoriza o envio.** Qualquer `ok:false`, inclusive `envio_existente`, significa não enviar. O teste pula os passos 5 a 8 e vai para a thread de e-mail do aprovador.

### concluir

```
concluir --envio <id> --resultado enviado|incerto|falhou [--id-provedor <messageId>] [--erro "<texto do erro>"]
```

Só aceita envios em `reservado`; qualquer outro estado dá `estado_invalido`. Classifique pelo que o `message(send)` devolveu:

| Retorno do `message(send)` | `--resultado` |
|---|---|
| `messageId` | `enviado --id-provedor <messageId>` |
| erro com "delivery is unknown" | `incerto` |
| erro com "Plow HTTP 4xx" ou "does not serve this conversation" | `falhou --erro "<texto>"` |
| qualquer outra coisa, ou nenhum retorno | `incerto` |

O script confere a classificação:
- `enviado` exige `--id-provedor`;
- `falhou` exige um `--erro` que case com um dos dois padrões acima (4xx, exceto 408 e 424); senão responde `falhou_nao_comprovado`, e o certo é usar `incerto`.

### resolver (decisão humana)

```
resolver --envio <id> --resultado enviado|falhou|bloqueado --aprovador <sender.id> [--nota "…"]
```

- Só aceita envios em `incerto` e exige aprovador com permissão de enviar. Com `aprovacao_so_dono=1`, exige `--aprovador plow-owner`; senão, `somente_dono`.
- `falhou` significa que uma pessoa confirmou que o e-mail não saiu. Isso libera nova tentativa e conta como falha.
- `bloqueado` significa nunca mais enviar com esta chave.

### liberar (`ok real`)

```
liberar --envio <id do teste> --aprovador <sender.id>
```

Exige um envio de teste em `enviado` e aprovador com permissão de enviar. Com `aprovacao_so_dono=1`, exige `--aprovador plow-owner`. Grava a liberação da instalação, uma única vez. Depois disso, o `preparar` real deixa de responder `teste_pendente`. Recusas: `teste_nao_enviado`, `aprovador_sem_permissao` e `somente_dono`. Se repetido, responde `ok` com `"existente":true`.

### pendentes

→ `{"ok":true,"teste_liberado":false,"envios":[{"envio_id":31,"conta":"acme","versao":2,"chat":"cht_…","para":"…","estado":"reservado","teste":false,"tentado_em":"…","idade_s":420}]}`

Lista os envios em `reservado` ou `incerto`, do mais antigo para o mais novo.

### registro

`registro [--saida <path>]` escreve `$MILO_MESA/registro.md` a partir do banco, com aprovações, envios e recusas. A primeira linha diz: "Gerado por milo-envio. Não editar."

### aprovadores, nunca-contatar, config

```
aprovadores add --uid <sender.id> --nome <nome> [--enviar] [--regras] --por <sender.id>
aprovadores remove --uid <sender.id> --por <sender.id>
aprovadores list
nunca-contatar add --chave <valor> --tipo email|dominio|empresa|chat --motivo <texto> --por <sender.id>
nunca-contatar list
config get [--chave <nome>]
config set --chave limite_diario|aprovacao_so_dono --valor <v> --por <sender.id>
```

- **`aprovadores add` / `remove` e `config set`:** só com `--por plow-owner`; senão, `somente_dono`. O `remove` zera as permissões e mantém a linha para o histórico. `plow-owner` não pode ser alterado.
- **`nunca-contatar add`:** aceita qualquer `--por`, porque a lista só restringe. O "PARAR" de um lead entra com o `sender.id` do lead. Não existe `remove`: tirar alguém da lista é feito à mão, fora do Milo. Com `--tipo chat`, a resposta traz `"rotulos":[…]`, os e-mails de rótulo dos envios reais anteriores para aquele chat, para a skill gravar cada um como `email`.
- **Como a checagem casa**, sempre contra o `chat_uid`, o endereço do rótulo e a conta:
  - `chat`: igual ao `chat_uid` do envio;
  - `email`: igual, depois de passar para minúsculas e tirar espaços;
  - `dominio`: o domínio do rótulo é igual à chave ou termina em `.chave`;
  - `empresa`: o slug da conta é igual ao slug da chave (minúsculas, sem acento, e o que não for letra ou número vira hífen).

  "Acme" não casa com "Acme Logística", então registre sempre o domínio junto.

## 5. Estados e limite

```
reservado ──concluir──▶ enviado | incerto | falhou
incerto  ──resolver──▶ enviado | falhou | bloqueado
falhou   → permite novo preparar da mesma aprovação, até 2 falhas por chave
enviado, bloqueado → finais
```

- Nenhum estado muda sozinho com o tempo.
- Recusas não criam envio; vão para `eventos`.
- **Limite diário:** conta os envios reais em `reservado`, `enviado` ou `incerto` com `tentado_em` nas últimas 24 h, numa janela móvel em UTC. O padrão é 10 (`config limite_diario`). Teste, `falhou` e `bloqueado` não contam.

## 6. Esquema

Em toda conexão: `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=FULL`, journal no modo padrão (sem WAL). Toda escrita acontece dentro de `BEGIN IMMEDIATE`.

```
aprovadores(identificador TEXT PK, nome TEXT, pode_enviar INT, pode_regras INT,
            criado_em TEXT, criado_por TEXT)                     -- linha fixa ('plow-owner','dono',1,1)
nunca_contatar(chave TEXT PK, tipo TEXT CHECK(email|dominio|empresa|chat), motivo TEXT,
               criado_em TEXT, criado_por TEXT)
aprovacoes(id INTEGER PK, conta TEXT, versao INT, hash_texto TEXT, chat_uid TEXT, para TEXT,
           aprovador_id TEXT FK→aprovadores, canal TEXT CHECK(dm|grupo|email), aprovado_em TEXT,
           UNIQUE(conta, versao))
envios(id INTEGER PK, aprovacao_id INT FK→aprovacoes, teste INT, chat_uid TEXT, para TEXT,
       executor TEXT CHECK(milo|humano) DEFAULT 'milo',
       chave_dedup TEXT, estado TEXT CHECK(reservado|enviado|incerto|falhou|bloqueado),
       tentado_em TEXT, concluido_em TEXT, id_provedor TEXT, confirmado_por TEXT, nota TEXT,
       erro TEXT, resolvido_por TEXT)
  -- aprovacoes.chat_uid e envios.chat_uid ficam vazios quando o destino é só o endereço (plano B)
  UNIQUE INDEX envios(chave_dedup) WHERE estado IN (reservado, enviado, incerto, bloqueado)
config(chave TEXT PK, valor TEXT, alterado_em TEXT, alterado_por TEXT)
  -- limite_diario=10, aprovacao_so_dono=1, teste_liberado_em, teste_liberado_por
eventos(id INTEGER PK, em TEXT, tipo TEXT, ator TEXT, aprovacao_id INT, envio_id INT,
        motivo TEXT, dados TEXT)                                 -- só acréscimo; dados em JSON
```

## 7. Fluxo da skill `executar-envio`

**Gatilho `ok <conta> <versão>`:**

1. Rode `pendentes`.
   - Um `reservado` com `idade_s` acima de 300 é sobra de reinício: rode `concluir --resultado incerto` e avise.
   - Se houver `incerto` ou `reservado` da mesma conta, não siga: diga o estado e quem resolve.
2. Localize `$MILO_MESA/rascunhos/<conta>-v<versao>.txt` e use esse caminho em `--texto-arquivo`. A `executar-envio` só lê esse arquivo, nunca o cria nem o altera. Se ele não existir, não siga e avise: "Não achei o texto da <conta> v<versão>. Não enviei."
3. Rode `aprovar` com o `sender.id` de quem escreveu o `ok`. Se for recusado, responda com a frase da tabela abaixo e pare.
4. Rode `preparar` (real). Se a resposta for `teste_pendente`, siga o fluxo de teste.
5. Com `ok:true`, rode `message(send)` com o `chat` e o `corpo` devolvidos.
6. Rode `concluir` logo em seguida, pela tabela da seção 4, **antes de qualquer outra mensagem**.
7. Se o resultado for `enviado`: confirme no espaço do time e atualize a ficha. Se for `incerto`: não envie mais nada neste turno, porque a Plow recusa. O aviso sai no turno seguinte, via `pendentes`.

**Teste, só no primeiro envio da instalação:**
- Rode `preparar --teste` apontando para a thread de e-mail do aprovador com o Milo, envie e rode `concluir`. Se essa thread não existir, peça ao aprovador que escreva para o e-mail do Milo [depende de T5].
- Depois pergunte: "Chegou o teste em <e-mail>? Se estiver como deve, responda `ok real`."

**Gatilho `ok real`:** rode `liberar --envio <id do teste> --aprovador <sender.id>`, depois o `preparar` real da mesma aprovação, e siga a partir do passo 5.

**Repetição de turno depois de reinício:** o `aprovar` devolve a mesma aprovação e o `preparar` devolve `envio_existente` com o estado. Responda com o estado. Nunca reenvie.

**PARAR:** o lead responde na thread de e-mail pedindo para parar. O modelo não vê o endereço dele, só o `chat_uid` da thread.
1. Rode `nunca-contatar add --tipo chat --chave <chat_uid da thread> --motivo "pediu para parar" --por <sender.id do lead>`.
2. Se a resposta trouxer `rotulos`, grave cada um com `nunca-contatar add --tipo email --chave <rótulo>`, com o mesmo motivo e o mesmo `--por`.
3. Não responda ao lead. Avise o dono da conta no espaço do time e marque a ficha.

**Contrato com a `redigir-abordagem`:**
- O arquivo do corpo nasce quando a versão é criada, em `$MILO_MESA/rascunhos/<conta>-v<versao>.txt`, escrito pela `redigir-abordagem`.
- Ele contém exatamente o corpo que vai sair, sem linha de assunto.
- É imutável: um ajuste gera uma nova versão e um novo arquivo, nunca uma edição do anterior.
- O pedido de aprovação é montado lendo esse arquivo, então o que o aprovador vê é o que o `preparar` confere.

| Motivo | O que o Milo diz |
|---|---|
| `aprovador_sem_permissao`, `somente_dono` | "Obrigado, <nome>. Quem aprova envios aqui é <aprovador>. <aprovador>, confirma?" |
| `texto_diferente`, `versao_conflitante` | "O texto mudou depois do ok. É outra versão e precisa de novo ok." |
| `nunca_contatar` | "<conta> está em nunca contatar (<motivo>). Não enviei." |
| `limite_diario` | "Limite de <n> envios em 24 h atingido. Não enviei; aviso quando liberar." |
| `envio_existente`, `duplicado`, `destinatario_ja_contatado` | "Esse contato já está <estado> desde <data>. Não reenvio." |
| `falhas_esgotadas` | "Falhou duas vezes. Alguém precisa olhar antes de tentar de novo." |
| código 2 ou 3 | "Não consegui registrar o envio. Não enviei." |

### Plano B: quem envia é uma pessoa

Vale enquanto a linha não tiver e-mail (seção 9). O Milo entrega o rascunho aprovado, uma pessoa envia da própria caixa, e o livro continua com as mesmas garantias.

- **`aprovar` sem `--chat`:** o destino é o endereço `--para`, e a chave de deduplicação usa `email:<para>` no lugar do `chat_uid`. Aqui o rótulo é confiável, porque é a pessoa que digita o endereço.
- **`preparar --executor humano`:** faz as mesmas conferências (aprovação, hash, nunca contatar, destinatário, limite e deduplicação), menos `teste_pendente`, que só testa a linha do Milo. Devolve `corpo` e `para`. O Milo entrega esse texto exato e pede: "Responda `enviei <conta> v<versão>` quando mandar."
- **Executor não entra na chave:** o Milo e uma pessoa nunca mandam o mesmo texto ao mesmo destino. O limite diário conta os dois executores.
- **Reservado humano não vira `incerto` por tempo:** a regra dos 300 s do passo 1 vale só para `executor=milo`. `pendentes` mostra o executor.
- **Confirmação:** `concluir --envio N --resultado enviado|incerto|falhou --confirmado-por <sender.id> [--nota "…"]`. Não há `id_provedor`; o registro guarda `confirmado_por`, `concluido_em` e a nota.
  - `enviado` e `incerto` aceitam qualquer `sender.id`, porque só restringem: bloqueiam reenvio.
  - `falhou` ("não vou enviar") exige aprovador com permissão de enviar, e `plow-owner` se `aprovacao_so_dono=1`, porque libera nova tentativa. Não exige padrão de erro.
- **PARAR pela caixa da pessoa:** o lead responde para quem enviou, não para o Milo. A pessoa avisa o Milo, que grava `nunca-contatar add --tipo email --chave <para> --por <sender.id da pessoa>`.

## 8. Limites honestos

- **O Milo pode contornar o script.** Com `message` ele envia sem passar pelo script, e com `exec` pode alterar o SQLite diretamente. As defesas são a regra do prompt, a confirmação no espaço do time depois de cada envio e o `registro.md` auditável.
- **Os identificadores vêm do modelo.** `--aprovador`, `--por` e `--canal` são passados pelo Milo. O script evita confusão, mas não impede um modelo que minta sobre quem aprovou.
- **No plano B, a confirmação humana é uma declaração.** O script registra quem disse que enviou, e quando, mas não vê o e-mail sair.
- **Uma skill no workspace pode sobrepor a nossa.** Skills em `/var/lib/plow/workspace/skills/` têm precedência sobre `/opt/plow/skills/`, e o Milo tem `write`. Uma `executar-envio` gravada ali substituiria a nossa. O prompt precisa proibir escrever em `workspace/skills/`.
- **O rótulo não é verificado.** A Plow não mostra ao modelo o endereço dos participantes de um chat. O script não tem como confirmar que `--para` é o dono daquele `chat_uid`. Por isso "nunca contatar" confere os dois, e o PARAR bloqueia pelo `chat_uid`.
- **`enviado` quer dizer só que a Plow aceitou (`messageId`).** Não há confirmação de entrega, spam ou bounce.
- **`incerto` pode ter saído.** Nunca é reenviado automaticamente.
- **A janela de 24 h usa o relógio do contêiner.**
- **As travas dependem do disco.** O controle de concorrência usa as travas de arquivo do SQLite; em disco de rede elas podem falhar [depende de T3].

## 9. Resultados dos testes e pendências

Testes na instalação Aspen, 25/09:

- **T3, parcial.** `/var/lib/plow/workspace/mesa` foi criada pela DM, lida depois de reinício e persistiu no volume. Por isso `MILO_MESA` está fixado. Ainda falta ler pelo grupo. O tipo de disco na nuvem da Plow continua desconhecido, e por isso o banco fica sem WAL.
- **T8, parcial.** Python 3.11.2 disponível. A versão do SQLite não foi informada. O esquema exige SQLite 3.8 ou mais novo, por causa do índice único parcial. Conferir com `python3 -c "import sqlite3;print(sqlite3.sqlite_version)"`.
- **T5/T2, falhou.** A linha Aspen não tem conta de e-mail. Hoje o Milo não tem como mandar e-mail, nem responder numa thread. Depende da Plow. Enquanto isso, vale o plano B do escopo (5.5 e 11): o Milo entrega o rascunho aprovado e uma pessoa envia.
- **T1, não validado.** O grupo ainda não entrega mensagens. Não se sabe se o `sender.id` aparece no prompt nem se o uid é estável. `aprovacao_so_dono=1` continua sendo o padrão.
- **T6 e T4.** Não há `cron`, nem `web_search`/`web_fetch`; só `exec` + `curl`. Nada disso afeta o `milo-envio`.

Ainda pendente:

- **[depende da Plow]** Uma conta de e-mail para a linha. Com ela: o Milo consegue abrir e-mail para endereço novo? Uma pessoa do time que abre a thread com o Milo em cópia gera uma conversa que o Milo serve? Qual `chat_uid` e qual assunto aparecem?
- **[depende de T1/T2]** O `sender.id` fica visível em DM, grupo e e-mail? É estável entre dias e igual para a mesma pessoa no iMessage e no e-mail?
- **[depende de T3]** A mesa é lida pelo grupo? O disco é local ou de rede?
- **[depende de T8]** Versão do SQLite.
