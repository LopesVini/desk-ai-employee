# milo-envio: interface e esquema

> Estado em 28/09 (PRs #13 e #14): com o envio ligado pelo dono (`envio_automatico=1`), o Milo envia e-mail pelo comando `enviar`. Desligado, vale o plano B: `preparar --executor humano` e uma pessoa envia. Toda aprovação passa por `apresentar` e pela resposta `APROVO <código>` (ou `APPROVE <código>`). O caminho real antigo por conversa continua disponível; o teste antigo por `preparar --teste --chat` é recusado e todo teste sai por e-mail com `enviar --teste`. Um banco novo começa com `limite_diario=0`; o onboarding confirmado precisa definir e conferir esse valor antes de qualquer envio.

v2, 28/09 (v1 em 25/09). Responsável: Leitão. Escrito para quem faz a skill `executar-envio` sem ler o código.

## Para quem escreve a skill

O essencial cabe em seis passos; o resto do doc é referência. Todo comando é `python3 {baseDir}/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite <comando>`, e toda resposta é uma linha JSON.

1. **`pendentes` primeiro.** Se já houver `reservado` ou `incerto` da mesma conta, não siga: diga o estado.
2. **Localize o arquivo da versão** em `$MILO_MESA/rascunhos/<conta>-v<versao>.txt`. A skill nunca cria nem edita esse arquivo; se ele não existir, pare e avise.
3. **`apresentar`** e mostre à pessoa o `texto` inteiro e o `codigo`. Espere uma **nova mensagem** dela.
4. **`aprovar`** com o `sender.id` de quem respondeu, `--resposta` com a mensagem literal (`APROVO <código>` ou `APPROVE <código>`) e o mesmo `--tipo` do `apresentar`. Um "sim", "ok" ou "pode mandar" não aprova.
5. **Envio ligado: `enviar`.** O primeiro envio da instalação vai de teste para a caixa `email_teste` do dono, e o real só sai depois do `liberar`. **Envio desligado: `preparar --executor humano`** e entregue exatamente o `para` e o `corpo` devolvidos.
6. **No plano B, `concluir --confirmado-por`** quando a pessoa disser que enviou. O `enviar` conclui sozinho.

Qualquer `ok:false` significa não enviar. As frases do Milo em cada recusa estão na tabela da skill `executar-envio`. O PARAR e o teste da instalação estão na seção 7. Argumentos e recusas de cada comando estão na seção 4.

## 1. O que é

`milo-envio` é o livro de aprovações e envios do Milo, guardado num SQLite. Ele registra quem aprovou o quê, confere tudo imediatamente antes do envio e reserva o envio para que não saia duas vezes. **Não é uma porta técnica**: o Milo continua tendo `message` e `exec` e pode contorná-lo (seção 8). O script impede erro e confusão. A regra "só envie por aqui" é do prompt.

Quando o Milo passa pelo script, fica garantido que:

1. Nada sai sem aprovação gravada de um aprovador com permissão.
2. O corpo enviado é o aprovado (hash).
3. "Nunca contatar", teste e limite diário são conferidos no momento do envio.
4. A mesma conta, destino e texto nunca geram dois envios. `reservado` ou `incerto` bloqueia até um humano resolver.
5. Depois de um reinício, `pendentes` mostra o que ficou pela metade.
6. `registro.md` é gerado a partir do banco, nunca editado à mão.

O T5 (27/09) confirmou que a API da Plow envia para endereço novo, sem conversa aberta. Por isso o destino é o endereço da linha `Para:` do rascunho (seção 3).

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

- **Destino:** o endereço da linha `Para:` do rascunho, que precisa ser igual ao `--para` (senão, `destinatario_diferente_do_rascunho`). Só endereço simples: `<…>`, nome ou ponto no fim dão `email_invalido`.
  - O remetente é a caixa de e-mail da linha do Milo (ex.: `willow@plow.co`).
  - O `enviar` manda só `to`, `subject` e `body`. A Plow põe o dono em cópia a partir do Gmail conectado à conta.
  - O caminho antigo por conversa (`--chat cht_…`, com o endereço só como rótulo) continua aceito pelo script, mas a skill não usa.
- **Texto:** o arquivo da versão, com `Para: <e-mail>` na primeira linha, `Assunto: <assunto>` (linhas em branco entre os dois são aceitas), uma linha em branco e o corpo. O hash cobre tudo: mudar destinatário, assunto ou corpo é outra versão.
  - **Normalização antes do hash:**
    - exige UTF-8 e remove o BOM;
    - converte CRLF e CR em LF;
    - aplica Unicode NFC;
    - tira espaços e tabs do fim de cada linha;
    - tira linhas em branco do começo e do fim.
  - Nada além disso. Espaço duplo, aspas curvas e espaço não separável contam como diferença.
  - O hash é o SHA-256 do corpo normalizado.
- **Envio:** com o envio ligado, o `enviar` reserva, chama a API e registra o resultado numa chamada só. No plano B, a pessoa envia o `para` e o `corpo` que o `preparar` devolve. Nada é remontado de memória.
- **Aprovadores:** identificados pelo `sender.id`.
  - `plow-owner` é o dono, identificado pelo próprio canal. Vem gravado na criação do banco, com permissão de enviar e de confirmar regras, e não pode ser alterado.
  - Os outros entram por `aprovadores add`, só a pedido do dono.
  - O uid de uma pessoa só é conhecido depois que ela escreve ao Milo. O Milo grava o uid que viu naquela mensagem, nunca um que alguém digitou.
- **Só o dono aprova:** a configuração `aprovacao_so_dono=1` é o padrão. O T1 (27/09) mostrou o `sender.id` estável no grupo, e o dono passa para `0` quando cadastra aprovadores (`aprender-playbook`, seção 3c). Nesse modo, `aprovar` exige `--aprovador plow-owner` e `--canal dm` ou `--canal grupo`; `preparar` recusa aprovações que não cumpram isso; `liberar` e `resolver` exigem `--aprovador plow-owner`. Qualquer outro aprovador, ou o dono com `--canal email`, recebe `somente_dono`. O grupo vale porque o canal marca o dono como `plow-owner` pelo papel de dono no próprio chat, igual na DM (`plugin/index.ts:48` e `:70`, base 7ce757a, coberto por `tests/owner.test.ts` da base).
- **Chave de deduplicação:** SHA-256 de `conta | destino | hash_texto | teste-ou-real`. O destino é o `chat_uid` ou, no plano B, `email:<para>`.

## 4. Comandos

### apresentar

```
apresentar --conta <slug> --versao <n> --texto-arquivo <path> --para <email>
           [--tipo primeiro|followup|resposta]
```

Não grava nada. Devolve o texto inteiro e o `codigo` que a pessoa precisa responder. Confere:
- se a versão ainda é a atual no diário de rascunhos;
- se a linha `Para:` existe e é igual a `--para`;
- se o cabeçalho está no formato que o `enviar` aceita.

O código são os 10 primeiros caracteres (hexadecimal, maiúsculos) do SHA-256 de conta, versão, hash, destinatário e tipo. Por isso o `aprovar` precisa receber o mesmo `--tipo`.

→ `{"ok":true,"conta":"acme","versao":2,"para":"…","tipo":"primeiro","hash":"…","texto":"…","codigo":"7A709A5BDA"}`

**Recusas:** `para_ausente`, `destinatario_diferente_do_rascunho`, `assunto_ausente`, `versao_substituida`, `arquivo_fora_da_mesa`, `registro_versoes_ausente`, `email_invalido`, `texto_inexistente`, `texto_vazio`, `texto_invalido`.

### aprovar

```
aprovar --conta <slug> --versao <n> --texto-arquivo <path> --para <email>
        --aprovador <sender.id> --canal dm|grupo|email --resposta 'APROVO <código>'
        [--tipo primeiro|followup|resposta]
```

Grava a aprovação. Confere:
- se o aprovador tem permissão de enviar e se a regra "só o dono" está sendo respeitada;
- o formato `cht_…`;
- se o e-mail do rótulo é válido;
- "nunca contatar";
- se o texto não está vazio.
- se a resposta é `APROVO <código>` ou `APPROVE <código>`, uma vez só (menção como `@Milo` e pontuação em volta são aceitas; qualquer outra palavra recusa), com o código da conta, versão, destinatário, tipo e hash atuais;
- se as linhas `Para:` e `Assunto:` estão no formato que o `enviar` aceita (o `apresentar` confere o mesmo, antes de mostrar o código);
- se o diário de rascunhos ainda marca esta versão como atual.

O `--tipo` (padrão `primeiro`) é aprovado junto com o texto e fica gravado na aprovação: o pedido de aprovação precisa dizer se é "follow-up <n>" ou "resposta ao lead". O `preparar` usa esse tipo.

É idempotente: com a mesma conta, versão, hash, chat, rótulo e tipo, devolve o mesmo id com `"existente":true`. Mesma conta e versão com qualquer diferença dá `versao_conflitante`.

→ `{"ok":true,"aprovacao_id":17,"hash":"…"}`

**Recusas:** `aprovador_sem_permissao`, `somente_dono` (conferidas antes do código), `confirmacao_da_versao_ausente`, `para_ausente`, `destinatario_diferente_do_rascunho`, `assunto_ausente`, `versao_substituida`, `arquivo_fora_da_mesa`, `registro_versoes_ausente`, `nunca_contatar`, `versao_conflitante`, `texto_inexistente`, `texto_vazio`, `texto_invalido`, `chat_invalido`, `email_invalido` (inclusive `<e-mail>` ou ponto no fim). Toda recusa é gravada em `eventos`. Chame `aprovar` também quando quem responde não pode aprovar: é assim que a recusa fica registrada.

### preparar

```
preparar --aprovacao <id> --texto-arquivo <path>
preparar --aprovacao <id> --texto-arquivo <path> --executor humano
```

Com o envio ligado, a skill não chama o `preparar` direto: o `enviar` chama por dentro. O teste por e-mail é feito pelo `enviar --teste`; o `preparar --teste --chat` é recusado com `teste_exige_enviar`, porque um chat arbitrário não prova que o destino pertence à caixa interna cadastrada.

Antes da transação, lê o arquivo: `texto_inexistente`, `texto_invalido`, `texto_vazio` ou, com a mesa de rascunhos presente, `para_ausente`. Depois roda numa única transação (`BEGIN IMMEDIATE`) e confere nesta ordem:

1. A aprovação existe (senão, `aprovacao_inexistente`) e a versão dela ainda é a atual (senão, `versao_substituida`).
2. Já existe envio desta aprovação, do mesmo tipo (teste ou real), em `reservado`, `incerto`, `enviado` ou `bloqueado`? Então devolve `envio_existente`, com `envio_id`, `estado` e `executor`, e **não cria outro**. É aqui que cai a repetição de turno depois de um reinício.
3. *(Milo, caminho antigo por conversa)* A aprovação tem chat. Senão: `chat_ausente` (use o plano B). Pelo `enviar`, o destino é o e-mail e este passo não se aplica.
4. O aprovador ainda tem permissão (e a regra "só o dono" continua respeitada). Senão: `aprovador_sem_permissao` ou `somente_dono`.
5. O hash do arquivo é igual ao aprovado. Senão: `texto_diferente`.
6. *(real)* Nem o `chat_uid` nem o rótulo estão em "nunca contatar". Senão: `nunca_contatar`.
7. *(real, Milo)* O teste da instalação já foi liberado. Senão: `teste_pendente`.
8. Nenhuma aprovação tem a mesma chave em andamento. Senão: `duplicado`, com `envio_id` e `estado`.
9. *(real, aprovação `primeiro`, o padrão)* Não há outro envio real, com qualquer texto, para o mesmo chat ou rótulo em `reservado`, `incerto` ou `enviado`. Senão: `destinatario_ja_contatado`.
   *(real, aprovação `followup` ou `resposta`)* Continua uma conversa já aberta: não há envio `reservado` ou `incerto` para o destino (`envio_em_aberto`) e já existe envio `enviado` para ele nesta conta (`sem_contato_anterior`). "Último envio" é quando saiu de fato: `concluido_em` (no plano B, a confirmação da pessoa), ou `tentado_em` se não houver.
   - Só no follow-up: no máximo 2 por destino (`followups_esgotados`) e pelo menos 3 dias desde o último envio (`followup_cedo`, com `liberado_em`).
   - Só na resposta: uma resposta do lead registrada com `resposta-recebida` depois do último envio para o destino (`resposta_nao_registrada`). Cada registro libera uma resposta: depois que ela sai, a próxima precisa de um registro novo. A resposta não espera os 3 dias.
10. *(real, aprovação `primeiro`)* O limite diário não foi atingido. Senão: `limite_diario`. Follow-up e resposta não contam no limite, que é de novas abordagens.
11. A chave tem menos de 2 falhas. Senão: `falhas_esgotadas`.
12. Cria o envio como `reservado`, com o tipo da aprovação.

Se o `preparar` receber `--tipo` diferente do aprovado, recusa com `tipo_diferente_da_aprovacao`. Sem `--tipo`, usa o da aprovação.

→ `{"ok":true,"envio_id":31,"estado":"reservado","teste":false,"chat":"cht_…","corpo":"…"}`

**Só `ok:true` autoriza o envio.** Qualquer `ok:false`, inclusive `envio_existente`, significa não enviar. O teste pula os passos 7, 9 e 10, mas confere "nunca contatar" e só vai para a caixa `email_teste` cadastrada pelo dono: `teste_para_destinatario` (o endereço do lead), `email_teste_nao_configurado` e `teste_para_nao_autorizado`.

### enviar (e-mail pelo Milo)

```
enviar --aprovacao <id> --texto-arquivo <arquivo> [--teste --para <email_teste>]
```

Faz numa chamada o que o modelo não deve fazer em passos soltos:
- confere `envio_automatico=1` (padrão `0`; só o dono liga);
- lê o arquivo aprovado e separa as linhas `Para:` e `Assunto:` do corpo (o hash aprovado cobre tudo);
- acha a caixa de e-mail do agente (a linha de e-mail com o mesmo nome da linha de telefone, ex.: `willow@plow.co`);
- roda o `preparar` com executor `milo`;
- chama `POST /v1/email-lines/{uid}/messages` com o corpo que o `preparar` conferiu e reservou (não uma segunda leitura do arquivo);
- roda o `concluir`.

Travas de arquivo fazem a criação de uma versão nova e um `nunca-contatar add` esperarem um envio em andamento.

- `201` com `status: sent` e `message_id`: `enviado`, com o id do provedor.
- `acceptance_unknown`, 5xx, timeout ou conexão caída: `incerto`. Nunca reenvia; a mesma aprovação passa a responder `envio_existente`.
- 4xx da Plow (exceto 408/424): `falhou`, com o erro.
- Recusas antes de reservar: `envio_automatico_desligado`, `sem_credencial`, `para_ausente`, `assunto_ausente`, `caixa_indisponivel`, e todas as do `preparar` (texto diferente, versão substituída, nunca contatar, limite, destinatário já contatado, `teste_pendente` e as do teste).

A Plow põe o dono em cópia a partir do Gmail conectado à conta; sem Gmail conectado, a API recusa com 403 `email_line_owner_not_visible`. Respostas dos leads não chegam ao agente nesta versão (27/09): chegam na caixa do dono, e o time conta ao Milo. Testes: `tests/envio/test_enviar_email.py`, contra uma API falsa local.

### resposta-recebida

```
resposta-recebida --conta <slug> --para <email> [--chat <cht_…>] --por <sender.id> [--nota "…"]
```

Registra que o lead respondeu e libera uma resposta nossa (aprovação `--tipo resposta`). Só vale para um destino que já recebeu envio confirmado (`enviado`) desta conta; senão, `sem_contato_anterior`. No plano B, quem avisa está declarando, como no "enviei": fica gravado quem disse (`--por`) e vai para `eventos`.

→ `{"ok":true,"resposta_id":4,"registrada_em":"…"}`

**Recusas:** `sem_contato_anterior`, `email_invalido`, `chat_invalido`.

### concluir

```
concluir --envio <id> --resultado enviado|incerto|falhou [--id-provedor <messageId>] [--erro "<texto do erro>"]
```

Só aceita envios em `reservado`; qualquer outro estado dá `estado_invalido`. O `enviar` conclui sozinho, e no plano B vale a confirmação humana (seção 7). A tabela abaixo serve ao caminho antigo por conversa; classifique pelo que o `message(send)` devolveu:

| Retorno do `message(send)` | `--resultado` |
|---|---|
| `messageId` | `enviado --id-provedor <messageId>` |
| erro com "delivery is unknown" | `incerto` |
| erro com "Plow HTTP 4xx" ou "does not serve this conversation" | `falhou --erro "<texto>"` |
| qualquer outra coisa, ou nenhum retorno | `incerto` |

O script confere a classificação:
- `enviado` exige `--id-provedor`;
- `falhou` exige um `--erro` que case com um dos dois padrões acima (4xx, exceto 408 e 424); senão responde `falhou_nao_comprovado`, e o certo é usar `incerto`.

**Recusas:** `envio_inexistente`, `estado_invalido`, `id_provedor_ausente`, `falhou_nao_comprovado`. No plano B, também `confirmado_por_ausente`, `aprovador_sem_permissao` e `somente_dono`.

### resolver (decisão humana)

```
resolver --envio <id> --resultado enviado|falhou|bloqueado --aprovador <sender.id> [--nota "…"]
```

- Só aceita envios em `incerto` e exige aprovador com permissão de enviar. Com `aprovacao_so_dono=1`, exige `--aprovador plow-owner`; senão, `somente_dono`.
- `falhou` significa que uma pessoa confirmou que o e-mail não saiu. Isso libera nova tentativa e conta como falha.
- `bloqueado` significa nunca mais enviar com esta chave.
- **Recusas:** `envio_inexistente`, `estado_invalido`, `aprovador_sem_permissao`, `somente_dono`.

### liberar (teste confirmado)

```
liberar --envio <id do teste> --aprovador <sender.id>
```

Roda quando quem recebeu o teste na caixa interna confirma que ele chegou bem. Exige um envio de teste em `enviado` e aprovador com permissão de enviar. Com `aprovacao_so_dono=1`, exige `--aprovador plow-owner`. Grava a liberação da instalação, uma única vez. Depois disso, o `preparar` real deixa de responder `teste_pendente`. Recusas: `envio_inexistente`, `teste_nao_enviado`, `aprovador_sem_permissao` e `somente_dono`. Se repetido, responde `ok` com `"existente":true`.

### pendentes

→ `{"ok":true,"teste_liberado":false,"envios":[{"envio_id":31,"conta":"acme","versao":2,"chat":"cht_…","para":"…","estado":"reservado","teste":false,"executor":"milo","tentado_em":"…","idade_s":420}]}`

Lista os envios em `reservado` ou `incerto`, do mais antigo para o mais novo.

### registro

`registro [--saida <path>]` escreve `registro.md` ao lado do banco (`$MILO_MESA/registro.md`) a partir do banco, com configuração, envios, aprovações, eventos e recusas, "nunca contatar" e aprovadores. A primeira linha diz: "Gerado por milo-envio. Não editar." Grava num arquivo temporário e troca de uma vez, então nunca fica pela metade.

### aprovadores, nunca-contatar, config

```
aprovadores add --uid <sender.id> --nome <nome> [--enviar] [--regras] --por <sender.id>
aprovadores remove --uid <sender.id> --por <sender.id>
aprovadores list
nunca-contatar add --chave <valor> --tipo email|dominio|empresa|chat --motivo <texto> --por <sender.id>
nunca-contatar list
config get [--chave <nome>]
config set --chave limite_diario|aprovacao_so_dono|envio_automatico|email_teste --valor <v> --por <sender.id>
```

- **`config set`:** `limite_diario` é inteiro >= 0; `aprovacao_so_dono` e `envio_automatico` são `0` ou `1`; `email_teste` precisa ser um endereço simples (senão, `email_invalido`).

- **`aprovadores add` / `remove` e `config set`:** só com `--por plow-owner`; senão, `somente_dono`. O `remove` zera as permissões e mantém a linha para o histórico; remover quem não está cadastrado dá `aprovador_inexistente`. `plow-owner` não pode ser alterado: `dono_imutavel`.
- **Chaves inválidas no `nunca-contatar add`:** `email_invalido`, `chat_invalido` ou `dominio_invalido`.
- **`nunca-contatar add`:** aceita qualquer `--por`, porque a lista só restringe. O "PARAR" de um lead entra com o `sender.id` do lead. Não existe `remove`: tirar alguém da lista é feito à mão, fora do Milo. Com `--tipo chat`, a resposta traz `"rotulos":[…]`, os e-mails de rótulo dos envios reais anteriores para aquele chat, para a skill gravar cada um como `email`. Toda resposta de sucesso traz também `"envios_reservados":[{"envio_id","conta","versao","para","executor","teste"}]`: os envios ainda em `reservado` que a nova entrada bloquearia. Vem mesmo quando a chave já existia (`"existente":true`).
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
- **Limite diário:** conta os primeiros contatos reais (`tipo = primeiro`) em `reservado`, `enviado` ou `incerto` com `tentado_em` nas últimas 24 h, numa janela móvel em UTC. Um banco novo começa em 0; o onboarding confirmado define o valor escolhido (10 é somente a sugestão de playbook). Teste, `falhou` e `bloqueado` não contam.

## 6. Esquema

Em toda conexão: `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=FULL`, journal no modo padrão (sem WAL). Toda escrita acontece dentro de `BEGIN IMMEDIATE`.

```
aprovadores(identificador TEXT PK, nome TEXT, pode_enviar INT, pode_regras INT,
            criado_em TEXT, criado_por TEXT)                     -- linha fixa ('plow-owner','dono',1,1)
nunca_contatar(chave TEXT PK, tipo TEXT CHECK(email|dominio|empresa|chat), motivo TEXT,
               criado_em TEXT, criado_por TEXT)
aprovacoes(id INTEGER PK, conta TEXT, versao INT, hash_texto TEXT, chat_uid TEXT, para TEXT,
           aprovador_id TEXT FK→aprovadores, canal TEXT CHECK(dm|grupo|email), aprovado_em TEXT,
           tipo TEXT CHECK(primeiro|followup|resposta) DEFAULT 'primeiro',
           UNIQUE(conta, versao))
respostas(id INTEGER PK, conta TEXT, chat_uid TEXT, para TEXT, registrada_em TEXT, registrada_por TEXT, nota TEXT)
envios(id INTEGER PK, aprovacao_id INT FK→aprovacoes, teste INT, chat_uid TEXT, para TEXT,
       executor TEXT CHECK(milo|humano) DEFAULT 'milo',
       chave_dedup TEXT, estado TEXT CHECK(reservado|enviado|incerto|falhou|bloqueado),
       tentado_em TEXT, concluido_em TEXT, id_provedor TEXT, confirmado_por TEXT, nota TEXT,
       erro TEXT, resolvido_por TEXT,
       tipo TEXT CHECK(primeiro|followup|resposta) DEFAULT 'primeiro')
  -- esquema versão 3 (PRAGMA user_version): envios.tipo (v2), aprovacoes.tipo e respostas (v3).
  -- Ao abrir, bancos da versão 1 ou 2 ganham o que falta, coluna por coluna; o que já existia vira 'primeiro'.
  -- aprovacoes.chat_uid e envios.chat_uid ficam vazios quando o destino é só o endereço (plano B)
  UNIQUE INDEX envios(chave_dedup) WHERE estado IN (reservado, enviado, incerto, bloqueado)
config(chave TEXT PK, valor TEXT, alterado_em TEXT, alterado_por TEXT)
  -- padrões: limite_diario=0, aprovacao_so_dono=1, envio_automatico=0, email_teste=''
  -- gravados depois: teste_liberado_em, teste_liberado_por
eventos(id INTEGER PK, em TEXT, tipo TEXT, ator TEXT, aprovacao_id INT, envio_id INT,
        motivo TEXT, dados TEXT)                                 -- só acréscimo; dados em JSON
  TRIGGER eventos_sem_update / eventos_sem_delete: RAISE(ABORT) em qualquer UPDATE ou DELETE
```

O "só acréscimo" de `eventos` vale no próprio banco: dois gatilhos recusam qualquer UPDATE ou DELETE, inclusive de quem abrir o SQLite direto.

## 7. Fluxo da skill `executar-envio`

**Pedido de aprovação** (na `redigir-abordagem`): rode `apresentar` e mostre o `texto` inteiro e o `codigo`, terminando com `Se estiver tudo certo, responda APROVO <código>.` Depois de mostrar, encerre o turno.

**Gatilho: uma nova mensagem com `APROVO <código>` ou `APPROVE <código>`.**

1. Rode `pendentes`.
   - Um `reservado` do executor `milo` com `idade_s` acima de 300 é sobra de reinício: rode `concluir --resultado incerto` e avise.
   - Se houver `incerto` ou `reservado` da mesma conta, não siga: diga o estado e quem resolve.
2. Localize `$MILO_MESA/rascunhos/<conta>-v<versao>.txt` e use esse caminho em `--texto-arquivo`. A `executar-envio` só lê esse arquivo, nunca o cria nem o altera. Se ele não existir, não siga e avise.
3. Rode `aprovar` com o `sender.id` de quem respondeu, `--resposta` com a mensagem literal e o mesmo `--tipo` do `apresentar`. Se for recusado, responda com a frase da tabela da skill e pare.
4. Confira `config get --chave envio_automatico`. Com `1`, siga "Envio pelo Milo". Com `0`, siga o plano B, abaixo.

**Envio pelo Milo (`envio_automatico=1`):**
- **Primeiro envio da instalação** (`teste_liberado: false` em `pendentes`): `enviar --aprovacao <id> --texto-arquivo <arquivo> --teste --para <email_teste>`. O `email_teste` é pedido ao dono quando ele liga o envio. Quando quem recebeu confirmar que chegou bem, e se essa pessoa puder aprovar, rode `liberar --envio <id do teste> --aprovador <sender.id>`.
- **Envio real:** `enviar --aprovacao <id> --texto-arquivo <arquivo>`. Com `enviado`, confirme no espaço do time e atualize a ficha. Com `entrega_incerta`, não reenvie: peça para conferir na caixa do dono, que está em cópia, e registre a resposta com `resolver`.

**Repetição de turno depois de reinício:** o `aprovar` devolve a mesma aprovação e o `enviar`/`preparar` devolve `envio_existente` com o estado. Responda com o estado. Nunca reenvie.

**PARAR:** as respostas dos leads chegam na caixa do dono (em cópia), não ao Milo.
1. Quando alguém do time avisar que o lead pediu para parar, rode `nunca-contatar add --tipo email --chave <e-mail do lead> --motivo "pediu para parar" --por <sender.id de quem avisou>`.
2. Se um lead escrever direto numa conversa de e-mail com o Milo, grave também o chat (`--tipo chat --chave <chat_uid>`) e cada endereço que vier em `rotulos`.
3. Não responda ao lead. Avise o dono da conta no espaço do time e marque a ficha.

**Contrato com a `redigir-abordagem`:**
- O arquivo nasce quando a versão é criada, em `$MILO_MESA/rascunhos/<conta>-v<versao>.txt`, pelo `criar-rascunho.py`. Ele também grava o diário de versões (`.<conta>.last`), que faz a versão nova invalidar as anteriores.
- Contém `Para:` (quando há destinatário verificado), `Assunto:`, uma linha em branco e o corpo.
- É imutável: um ajuste, inclusive de destinatário, gera uma nova versão e um novo arquivo, nunca uma edição do anterior.
- O pedido de aprovação usa o `texto` do `apresentar`, então o que o aprovador vê é o que o `aprovar` e o `enviar` conferem.

**Frases do Milo em cada recusa:** estão na tabela da skill `executar-envio`, que é a fonte única. Até 28/09 este doc tinha uma cópia da tabela, que ficou desatualizada.

### Plano B: quem envia é uma pessoa

Vale enquanto o envio estiver desligado (`envio_automatico=0`, o padrão), por exemplo numa instalação sem Gmail conectado. O Milo entrega o rascunho aprovado, uma pessoa envia da própria caixa, e o livro continua com as mesmas garantias.

- **`aprovar` sem `--chat`:** o destino é o endereço `--para`, e a chave de deduplicação usa `email:<para>` no lugar do `chat_uid`. Aqui o rótulo é confiável, porque é a pessoa que digita o endereço.
- **`preparar --executor humano`:** faz as mesmas conferências (aprovação, hash, nunca contatar, destinatário, limite e deduplicação), menos `teste_pendente`, que só testa a linha do Milo. Devolve `corpo` e `para`. O Milo entrega esse texto exato e pede, em palavras simples: "Envia da sua caixa e me avisa quando mandar."
- **Executor não entra na chave:** o Milo e uma pessoa nunca mandam o mesmo texto ao mesmo destino. O limite diário conta os dois executores.
- **Reservado humano não vira `incerto` por tempo:** a regra dos 300 s do passo 1 vale só para `executor=milo`. `pendentes` mostra o executor.
- **Confirmação:** `concluir --envio N --resultado enviado|incerto|falhou --confirmado-por <sender.id> [--nota "…"]`. Não há `id_provedor`; o registro guarda `confirmado_por`, `concluido_em` e a nota.
  - `enviado` e `incerto` aceitam qualquer `sender.id`, porque só restringem: bloqueiam reenvio.
  - `falhou` ("não vou enviar") exige aprovador com permissão de enviar, e `plow-owner` se `aprovacao_so_dono=1`, porque libera nova tentativa. Não exige padrão de erro.
- **PARAR pela caixa da pessoa:** o lead responde para quem enviou, não para o Milo. A pessoa avisa o Milo, que grava `nunca-contatar add --tipo email --chave <para> --por <sender.id da pessoa>`.
- **"Nunca contatar" depois do `preparar`:** no plano B, a conferência acontece no `preparar`, mas a pessoa envia depois, fora do script. Por isso todo `nunca-contatar add` devolve `envios_reservados`, e a skill avisa no espaço do time: "<conta> entrou em nunca contatar. Se ainda não enviou o texto de <conta> v<n>, não envie." O estado do envio não muda sozinho: se a pessoa não enviou, quem pode aprovar registra `falhou`; se já tinha enviado, registra `enviado`.

## 8. Limites honestos

- **O Milo pode contornar o script.** Com `message` ele envia sem passar pelo script, e com `exec` pode alterar o SQLite diretamente. As defesas são a regra do prompt, a confirmação no espaço do time depois de cada envio e o `registro.md` auditável.
- **Os identificadores vêm do modelo.** `--aprovador`, `--por` e `--canal` são passados pelo Milo. O script evita confusão, mas não impede um modelo que minta sobre quem aprovou.
- **A resposta de aprovação também vem do modelo.** O `aprovar` confere o código, mas não vê a conversa: depende do Milo ter mostrado a versão inteira e passar a mensagem literal da pessoa.
- **No plano B, a confirmação humana é uma declaração.** O script registra quem disse que enviou, e quando, mas não vê o e-mail sair.
- **No plano B, o aviso de "nunca contatar" depende da pessoa ler.** Se a conta entra na lista entre o `preparar` e o envio humano, o script aponta o envio reservado, mas não impede a pessoa de mandar da própria caixa.
- **Existe uma variável de pausa só para testes.** `MILO_ENVIO_PAUSA_TESTE` faz o `preparar` esperar dentro da transação, para os testes forçarem duas chamadas ao mesmo tempo. Tem teto de 2 s e ignora valores inválidos. Se o Milo a definir, só atrasa o próprio envio; nenhuma conferência muda.
- **Uma skill no workspace pode sobrepor a nossa.** Skills em `/var/lib/plow/workspace/skills/` têm precedência sobre `/opt/plow/skills/`, e o Milo tem `write`. Uma `executar-envio` gravada ali substituiria a nossa. O prompt precisa proibir escrever em `workspace/skills/`.
- **O rótulo não é verificado.** A Plow não mostra ao modelo o endereço dos participantes de um chat. O script não tem como confirmar que `--para` é o dono daquele `chat_uid`. Por isso "nunca contatar" confere os dois, e o PARAR bloqueia pelo `chat_uid`.
- **`enviado` quer dizer só que a Plow aceitou (`messageId`).** Não há confirmação de entrega, spam ou bounce.
- **`incerto` pode ter saído.** Nunca é reenviado automaticamente.
- **A janela de 24 h usa o relógio do contêiner.**
- **As travas dependem do disco.** O controle de concorrência usa as travas de arquivo do SQLite; em disco de rede elas podem falhar [depende de T3].

## 9. Resultados dos testes e pendências

Testes na instalação Aspen, 25/09:

- **T3, parcial.** `/var/lib/plow/workspace/mesa` foi criada pela DM, lida depois de reinício e persistiu no volume. Por isso `MILO_MESA` está fixado. Ainda falta ler pelo grupo. O tipo de disco na nuvem da Plow continua desconhecido, e por isso o banco fica sem WAL.
- **T8, validado em 28/09.** Na imagem do Milo: Python 3.11.2 e SQLite 3.40.1. O esquema exige SQLite 3.8 ou mais novo, por causa do índice único parcial.
- **T5, validado em 27/09.** Com um Gmail conectado à conta Plow do dono, `POST /v1/email-lines/{uid}/messages` enviou de `willow@plow.co` para um Gmail, na caixa de entrada, com o dono em cópia. Pelo Milo: teste para a aprovadora, `liberar`, envio real, todos `enviado` com id do provedor. A resposta do destinatário não apareceu em `/threads` nem virou conversa do agente.
- **T1, validado em 27/09.** No grupo, o `sender.id` de quem não é dono é o uid do participante naquele chat (`cp_…`): estável no grupo, diferente em cada chat. Com `aprovacao_so_dono=0`, aprovadores cadastrados pelo dono aprovam no grupo (`aprender-playbook`, seção 3c). Sem aprovador além do dono, o padrão continua `1`.
- **T6, validado em 27/09.** Com `cron` em `tools.alsoAllow` (`boot/milo-config.js`), o Milo agenda lembretes; um lembrete criado antes de trocar o contêiner disparou na hora depois do reinício. **T4:** ainda sem `web_search`/`web_fetch`; a busca é o `buscar.py`.

**Como a linha ganha e-mail.** O Vinicius confirmou no código da base que o boot só ativa a conta de e-mail se a identidade, lida uma única vez no boot, já trouxer um chat que tenha a linha de e-mail como participante. Talvez nem toda linha Plow tenha e-mail.

**Perguntas enviadas à Plow (Discord, 25/09).** O T5 respondeu a 2 e a 3 na prática: a API envia para endereço novo, com assunto e cópia.
1. Toda linha tem e-mail? Como provisionar o e-mail antes de existir algum chat?
2. A API consegue iniciar conversa com um endereço de e-mail arbitrário?
3. O backend aceita assunto, responder-para e cópia?

**Decisão para a submissão (25/09, superada em 27/09 pelo T5).** Se a resposta à pergunta 2 for não, o envio externo fica no plano B humano (seção 7). Outro transporte (SMTP, Resend, Gmail API) fica para depois do hackathon: até segunda ele exigiria credencial, domínio verificado, DNS do cliente e cuidado com entregabilidade, e o escopo diz que atraso encolhe escopo, não vira feature.

**Um transporte futuro cabe sem mudar o livro.** O script já aceita destino só por endereço (plano B), então um transporte novo precisaria apenas de um executor novo e do id que o provedor devolve.

Ainda pendente:

- **[depende da Plow]** As respostas dos leads chegarem ao Milo. Hoje caem na caixa do dono, que está em cópia, e o time avisa.
- **[depende de T2]** O `sender.id` é estável entre dias e igual para a mesma pessoa no iMessage e no e-mail?
- **[depende de T3]** A mesa é lida pelo grupo? O disco é local ou de rede?
