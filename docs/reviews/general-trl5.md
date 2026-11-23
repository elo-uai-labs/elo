# Revisão geral independente · evidências TRL5

Revisor: agente `trl_geral`, diferente dos autores da integração, operação, avaliação e correção do validador. Delta funcional desde `ebcc525` até snapshot `69a2c6eb4b338c7c9b8ab69e27441002a840e279`; inclui integração `399a4c2`, operação `fc7b248`, conjunto congelado `41cf4bc`, regressão `823e20c` e correção `7ede206`. Data:23/11/2026.

**Sem bloqueador funcional identificado no escopo examinado.** Isto não aprova automaticamente todos os critérios da avaliação, a representatividade do ambiente ou TRL5. A primeira avaliação IA e a triagem OCR falharam em seus critérios prévios; esses resultados precisam permanecer explícitos no fechamento.

## Código e comportamento

- Fonte sintética: cliente de loopback literal, proxy desativado e redirects recusados; paginação/versão/snapshot/contagens/bytes limitados. O lote completo é coletado antes de `integration/import`, que mantém a transação e validação existente. A origem e a idempotência são fonte+conteúdo; novo nome do snapshot não substitui IDs nem torna dados confiáveis. CLI recusa `data/` antes de abrir Store. Token não faz parte do estado ou relatório.
- Operação: servidor HTTP real e contas aleatórias em diretório temporário; síntese local explícita e chave vazia. Três leitores competem com um fluxo de escrita; as negativas são esperadas separadamente. Recuperação ocorre após encerramento dos clientes/commits reconhecidos; documentação não alega interrupção no meio de transação. Sessões e arquivos de contas não são confundidos com conteúdo do backup.
- Validador de dossiê: passa as fontes para a mesma verificação de menções já usada nas consultas. Entidade literal precisa aparecer na fonte efetivamente citada; não vira novo ID de fonte. Referências inexistentes, menções em fonte não citada e entidades inventadas continuam recusadas. Ambos provedores exercitados por mocks, sem API paga nesta revisão.
- Nenhum delta em `src/` ou estilos/componentes PDS nesta rodada. A suíte canônica desktop/celular final continua responsabilidade do aceite integrado, não foi presumida por esta revisão estática.

## Integridade das evidências

Conferidos runners, manifests de corpus e relatórios disponíveis. O primeiro conjunto foi commitado antes das chamadas; código e bytes das fixtures têm hashes nos artefatos. A avaliação não sobrescreve diretório anterior. OCR verifica hashes dos bytes de entrada; contagens de caracteres de falhas legíveis não são excluídas silenciosamente. O documento explica que7arquivos não representam7conteúdos independentes e que o controle degradado não é um scan de campo.

A primeira rodada IA tem16tentativas,1falha,20/20referências válidas nas respostas aceitas. A adjudicação é identificada como agente independente, com falha fora do denominador de afirmações; não se confunde com avaliação humana. A falha guarda somente tipo genérico e não permite atribuir retrospectivamente sua causa exata. O bug do validador foi demonstrado separadamente por teste controlado; uma regressão posterior de1caso em diretório novo retornou sucesso e referência/âncora esperadas. Isso não transforma a primeira rodada em16/16 nem cria novo holdout.

A primeira rodada OCR temCER0/1170caracteres legíveis, mas triagem4/7: três legíveis permaneceram inconclusivos. O critério não foi relaxado e `automatic_passed=false` foi preservado. CER zero não deve ser apresentado como aprovação total do OCR. A referência de representatividade continua hipótese, não confirmação por CAIXA, profissionais ou amostra de campo.

## Verificação independente executada

`PYTHONPATH=backend .venv/bin/python3 -m unittest backend.tests.test_dossier_cited_mentions backend.tests.test_synthetic_source -v`: **8testes passaram em1,377s**. Fonte HTTP separada, bancos temporários, sem banco manual ou segredo real. Não repeti a carga60s, OCR ou chamadas reais; os artefatos correspondentes foram inspecionados, e há revisões especializadas separadas.

O registro `docs/trl5/execucao.md` ainda tinha estados iniciais durante a revisão; o fechamento deve atualizar os estados e vincular os testes finais, mantendo IA/OCR com seus resultados completos. A revisão não autoriza publicação, operação corporativa ou promoção automática de TRL.

## SHA-256 do código/corpus examinado

- `backend/synthetic_source.py`: `3c24fac96c80cd403efec59dc727bbdb4c1c75e5b46860e1e3a66df6e3b768e8`.
- `backend/dossier.py`: `fb22cb6841ab44db0fd898592912875c20af1a30a25696864928d05f330efc59`.
- `backend/tests/test_dossier_cited_mentions.py`: `52ccfbd9cb713cec7afc86d8c59f36b2f62219876ba2f5efd7a1c0cd79cda8c6`.
- `scripts/trl-operation.py`: `1257c0679efef0bc0d7535ff4b64c7ea6a9e53ba82019fe58fc25856e0443e95`.
- `scripts/trl-evaluation.py`: `74915acda00848a88c061c6e6be3de885bdaf9aabe0d564b32b5b5f8e1a9a88a`.
- `scripts/trl-evaluation-regression.py`: `cb65ebad452b5fcc6c6c84f4625232696e719ce6d026b3f9afdec8d31a8e560e`.
- `tests/fixtures/trl-evaluation/ai.json`: `a28068b898a524433d9eb4e8fe37a733d591f52b3314905814eadaf6e1c06a59`.
- `tests/fixtures/trl-evaluation/ocr.json`: `e67fef8e45a6c54522c62be2d74c687c7977c49a401e662762533280c94d40ca`.

## Delta final: interrupção transacional e pacote

Revisados `a4ef5f9` e `e6ed7ff` (snapshot `e6ed7ff972bba613c8edd086d1f17d21d3784189`), sem mudança de runtime. Sem bloqueador de correção encontrado.

O ensaio de interrupção cria seu próprio diretório temporário e recusa banco externo. Worker limitado ao layout temporário conhecido, sem symlink de banco/marcador. Trigger existe apenas na cópia descartável e pausa antes do UPDATE de workflow, depois do INSERT de auditoria no fluxo normal de Store.apply. SIGKILL provoca rollback; a comparação completa exige que não sobrevivam nem workflow nem evento não confirmados. Removido o trigger, repetição gera exatamente um trabalho/um evento. Cleanup encerra o worker mesmo em falha. Executei independentemente `.venv/bin/python3 scripts/trl-crash-transaction.py`: passou, SQLite íntegro e hashes de snapshots idênticos. Isso acrescenta interrupção no meio da transação SQLite; não comprova corte elétrico, corrupção de disco, atomicidade do recibo HTTP ou RPO produtivo.

O empacotador seleciona documentos/relatórios obrigatórios e o diretório versionado de fixtures sintéticas. Recusa arquivo ausente, symlink, saída de ROOT e padrão reconhecível de chave OpenAI. Não percorre `.env`, banco ou logs arbitrários. Preserva resultados iniciais falhos e regressão separada; manifesto inclui hashes/bytes, commit e estado dirty, sem classificação automática de TRL. O ZIP é reaberto para conferir CRC, conjunto de entradas e hashes. Revisão estática: geração final depende da conclusão/acceptance ainda em preparação e deve ser executada no fechamento, sem alegar que esta revisão já gerou o pacote.

Hashes do delta:

- `scripts/trl-crash-transaction.py`: `ccc1fe39e0220937e502eceed1c1d12df571bb7488978f9b6e0e243d78cc2e7b`.
- `scripts/trl-bundle.py`: `63f14c43dc2d6d62b873be887dc4e5354ee77d4e9b606fd8cabcdf4864800741`.


## Complemento: OCR e OpenAI durante leituras autenticadas

Revisão estática dos commits `96c0e59`/`a1cc3d2`, no snapshot `01ecb53e341518c100d35765824bed2d91383de7`. Sem bloqueador identificado neste delta de harness/documentação; não alterei runtime nem repeti chamadas pagas. Conferi que os hashes dos dois runners no artefato correspondem aos arquivos revisados.

A subclasse mantém banco/contas temporários e limita o fluxo sequencial a duas tentativas reais, contadas antes da chamada e sem retry. Os flags explícitos são exigidos no wrapper e no Python; smoke esvazia a chave do subprocesso. Leitores executam somente leitura; erros de futures são propagados. A fixture OCR já conhecida é conferida por hash e por texto dos segmentos, preservando o gabarito; a correção do comparador não é apresentada como melhoria do motor. A revisão é automatizada sob conta sintética, expressamente assim registrada, embora o rótulo normal de fonte do produto diga “conferido por pessoa”; este artefato não comprova revisão humana.

O relatório registra duas respostas `gpt-6.2-sol`, 144 leituras em janela curta de 7,801s, p95 de leitura 0,01360s, zero erros inesperados e duas negativas403. Conferi a resposta de total330,00 contra o texto OCR citado, 1639tokens reportados e os indicadores de reinício/integridade:6eventos de negócio e157eventos de acesso. O dossiê cita dados sintéticos do caso e a consulta cita EVD-0001; a asserção de estado protegido impede que a consulta mude os objetos comparados. São verificações funcionais limitadas; não estimam precisão populacional, capacidade sustentada com IA, percentis de geração ou representatividade corporativa.

O complemento permanece separado da primeira avaliação e da regressão exposta. Não apaga as falhas prévias IA/OCR, não constitui novo holdout e não promove TRL automaticamente. A discrepância documentada entre timeout HTTP15s e provedor30s continua limite explícito: uma falha pode ter custo sem resposta persistida. O aceite canônico final continua responsabilidade da integração.

Hashes SHA-256:

- `scripts/trl-real-operation.py`: `3f89ef5ff2b54d7c7e4171e094313f1d66e5ff7242e1357497f986041ffe6196`.
- `scripts/trl-real-operation.mjs`: `487d17a3479f1424c331c25fdafde1bca8276e6bc49531674d520479f5ef4c05`.
- `docs/trl-real-operation.md`: `db0fd46df0406a833dfdbc646539de49087d17865eb10a3324d9379f360be122`.
- `output/validation/trl5/real-operation.json`: `d1d0ebd4ce5938546e469036b52dd30174aae40a2c20e2b610ba03d9109a7a74`.
