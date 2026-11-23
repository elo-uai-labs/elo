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
