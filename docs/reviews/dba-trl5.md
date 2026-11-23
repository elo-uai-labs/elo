# Revisão DBA independente · fonte sintética paginada

Data:23/11/2026. Revisor: agente `trl_operacao`, que não implementou o adaptador. **Aprovado no escopo examinado, sem bloqueador de integridade identificado.** Delta `399a4c2ff38cc5101a60d9092a1875c903dd7963`; snapshot da revisão `5a6f181cd464244e2e94aeea865c661fc3c95fab`. Minha implementação própria de operação mista não é objeto desta revisão independente.

## Caminho transacional examinado

`fetch_snapshot` recebe todas as páginas e valida contrato/identidade/contagens/IDs antes de chamar a persistência. A origem HTTP não mantém uma transação de banco aberta enquanto busca páginas. IDs duplicados entre páginas, referência ausente, mudança de snapshot e contagem divergente não produzem importação parcial.

`ingest` usa o comando já existente `integration/import`; não cria SQL ou schema próprios. `monitoring.transition` monta cópia de trabalho, valida/importa o conjunto inteiro e aplica as regras de integração existentes antes de publicar no estado. `Store.apply` lê sob BEGIN IMMEDIATE e persiste evento mais workflow na mesma transação. Hashes e dados anteriores não são reescritos. Falha antes do commit desfaz a transação.

A identidade do lote usa source_id e hash canônico do conteúdo, ordenando IDs na coleta. A checagem prévia de duplicata é complementada pela checagem dentro da transação. Se outro importador vencer, a exceção só vira duplicate quando a releitura íntegra comprova o mesmo lote. Reexecução após reabertura preserva estado e eventos. Reconciliação final compara IDs do lote persistido com os IDs recebidos, sem considerar a mera resposta200 como aceite.

Proveniência registra serviço local/source_id, snapshot no nome de origem, hash, IDs e regras. Isso não é identidade corporativa ou autenticação humana. O CLI exige destino explícito e rejeita caminho resolvido dentro de data/ antes de inicializar Store; o teste usa essa recusa sem abrir o banco manual. A API Python recebe um Store fornecido pelo chamador; a proteção específica de diretório pertence ao CLI, não é sandbox geral.

## Evidência executada

- Seis testes de `backend.tests.test_synthetic_source` passaram em1,255s: duas páginas, reconciliação/restart, retry503/timeout, nove classes de falha sem mutação, duplicata concorrente, isolamento de endpoint e recusa do banco manual.
- Concorrência com duas coletas resulta em um processed e um duplicate, um lote e um evento de negócio, com cadeia válida.
- Prova adicional independente em banco temporário criou trigger de falha no UPDATE de workflow. A integração já havia tentado INSERT do evento; a falha reverteu ambos e preservou exatamente as linhas SQL anteriores. Reabrir o banco confirmou integridade. Removido apenas o trigger de teste, nova coleta gerou um commit, e repetição após reabertura foi duplicate sem alteração das linhas SQL.
- Artefato da prova adicional: `output/validation/dba-trl5.json`, com hashes dos arquivos examinados. Nenhum dado manual ou credencial real utilizado.

## Limites

Sem migração/schema/índices novos. Os limites de volume e número de lotes existentes permanecem. Este parecer não certifica escalabilidade, ambiente multi-instância produtivo, contrato corporativo, autenticidade da origem externa ou representatividade de domínio. Fonte testada é sintética e local. A integração preserva as regras automáticas existentes do conector; não declara que toda tipologia futura é executada automaticamente. Avaliação de performance e segurança têm pareceres separados.

## SHA-256

- `backend/synthetic_source.py`: `3c24fac96c80cd403efec59dc727bbdb4c1c75e5b46860e1e3a66df6e3b768e8`.
- `backend/monitoring.py`: `60c975432dc4f3bcaa509f54f09691eeaff1019827b1b23f752a92517eb61ef0`.
- `backend/domain.py`: `f943739f52d1ae05fb67daf6cf594f29c7269ed298af8958409d1dd9c6620214`.
- `backend/tests/test_synthetic_source.py`: `d0ffdf133ef0b07d98a9ec3657ac336c540c1eed2ad730d3307cd0cf68cfba3c`.

## Complemento DBA · interrupção no meio da transação

Revisados `a4ef5f943eda687f2148962f89d32349b89dd966` e `e6ed7ff972bba613c8edd086d1f17d21d3784189`, exclusivamente `scripts/trl-crash-transaction.py`. **Aprovado no ensaio delimitado**, sem alteração no runtime. O empacotador presente nos mesmos commits não pertence ao escopo DBA deste complemento.

O processo pai cria banco novo em TemporaryDirectory; o launcher normal não aceita caminho externo. O modo worker exige diretório diretamente sob a pasta temporária com prefixo do ensaio, nome fixo do banco/marcador, arquivo existente e ausência de links nos dois arquivos. Essa restrição é proteção de uso do harness, não sandbox contra um operador local malicioso. Nenhum banco manual é aberto.

A subclasse test-only registra função SQLite de pausa. Um trigger BEFORE UPDATE de workflow chama essa função após o INSERT de audit executado por Store.apply e antes do commit. O marcador é gravado dentro da função e o pai exige marcador existente e worker ainda vivo antes de SIGKILL. Assim, a interrupção acontece dentro da transação de escrita, diferentemente da interrupção quiescente do protocolo operacional. O cleanup encerra também o worker quando a prova falha.

Reexecutei independentemente `.venv/bin/python3 scripts/trl-crash-transaction.py`: passou em0,110s. A reabertura recuperou exatamente o snapshot anterior (hashes idênticos), SQLite integrity_check=ok; removido somente o trigger de teste, repetição criou exatamente um trabalho e um evento com cadeia válida. A inserção não confirmada de auditoria não sobreviveu separada do workflow. Evidência `output/validation/trl5/crash-transaction.json`.

Limites preservados: SIGKILL de processo em SQLite local com trigger controlado não equivale a falha elétrica/disco, corrupção do sistema de arquivos, atomicidade conjunta da resposta HTTP e do commit ou garantia produtiva de RPO. A prova complementa a consistência transacional sem afirmar disponibilidade corporativa.

- `scripts/trl-crash-transaction.py`: `ccc1fe39e0220937e502eceed1c1d12df571bb7488978f9b6e0e243d78cc2e7b`.
- `backend/domain.py`: `f943739f52d1ae05fb67daf6cf594f29c7269ed298af8958409d1dd9c6620214`.
