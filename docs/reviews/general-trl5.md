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
