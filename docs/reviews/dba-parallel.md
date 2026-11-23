# Revisão DBA independente · evolução paralela

Revisor: agente `/root/pacote_ana`, autor apenas do pacote documental, sem participação na implementação de domínio, operação, runtime ou persistência. Commit revisado: `9e4d31834ad6013ef096b2512c4446ab1e511e45`, delta desde `ffe684ea2faf054ecf17607818dbf38576eb69b9`. Revisão somente leitura de código; testes exclusivamente em SQLite temporário. Nenhuma leitura/escrita do banco manual `data/elo.sqlite3`.

**Resultado: aprovado no escopo local; nenhum achado bloqueador de integridade, migração ou concorrência no delta revisado.** Não equivale a homologação de capacidade ou banco corporativo.

## Inspeção

- `Store.apply` mantém `BEGIN IMMEDIATE`, valida a cadeia antes da transição e grava evento/estado na mesma transação; falha reverte o lote. Não houve alteração de schema, índices ou triggers.
- Entrada de contratos invalida a marca da nova tipologia, portanto comparação incremental reavalia também contratos antigos. Só anexar `pending` sem essa invalidação perderia pares; esse erro não ocorre no caminho inspecionado.
- IDs `SIG-REP-<contrato>` e filtro de IDs já conhecidos preservam casos, decisões e fontes históricos, mesmo quando um novo par lexicalmente anterior é importado. Fonte do novo caso é determinística. Mudança de parâmetro não remove nem reescreve sinais anteriores.
- Resumo operacional deriva avisos/SLA/recorrência de snapshot íntegro, sem persistir resultados. Recorrência exige ID do contrato nas evidências e deduplica contratos por fornecedor/regra. A mesma transação de escrita/CAS de trabalhos continua em vigor.
- Compatibilidade: valores novos de regra são apresentados por defaults sem exigir migração destrutiva. A verificação da cadeia usa o estado bruto antes da normalização de leitura.
- CLI valida runtime antes de criar pasta/banco. `EloServer` também aplica validação antes de inicializar trilha HTTP; callers embutidos continuam responsáveis pelo `Store` que criaram antes da chamada. A garantia de não criar banco declarada é do CLI e foi testada nesse escopo.

## Verificações executadas

32 testes existentes passaram: `test_repeated_rule` (5), `test_operations` (5), `test_work` (5), `test_runtime_policy` (3), `test_monitoring` (11) e `test_rule_config` (3). Incluem CAS concorrente, atomicidade, ausência de mutação, idempotência do conector, restart e rejeição de startup sem criar banco.

Sonda independente em banco temporário:

- Quatro importações concorrentes do mesmo contrato: uma 200, três 422; um único registro persistido.
- Quatro detecções concorrentes: uma 200, três 409; sem sinal duplicado.
- Revisão humana registrada e depois terceiro contrato lexicalmente anterior importado: casos anteriores, dossiê, decisão e fontes ficaram byte-equivalentes na estrutura; novo sinal criado sem reescrever os anteriores.
- Importação com referência inexistente: estado/exportação e cadeia inalterados.
- Leitura de resumo: snapshot antes/depois idêntico.
- Alteração de filtro e reexecução: casos históricos preservados; reinício verificou cadeia íntegra.

Migração ensaiada: código `ffe684e` criou e detectou em SQLite temporário; `9e4d318` leu esse banco sem reescrever `workflow.value`, preservou `audit_valid` e acrescentou execução da terceira regra mantendo casos anteriores. Nenhum banco de trabalho real foi copiado.

Hashes dos seis módulos revisados foram comparados ao commit exato antes da sonda e estão em `output/validation/dba-parallel.json`, junto aos resultados. O relatório inicial da sonda usou por engano o comando inexistente `rule/configure`; foi corrigido para o contrato existente `rule/config` e a sonda inteira foi reexecutada com sucesso, sem mudança de produto.

## Limites mantidos

O estado JSON ainda é reescrito integralmente e as escritas são serializadas no SQLite. A nova comparação e o cálculo de recorrência não demonstram escala corporativa por passar nesses testes. O conector de pasta mantém as regras previamente implementadas; a nova tipologia é executada explicitamente pela aplicação. Retenção/âncora externa, DB gerenciado, RPO/RTO e carga sustentada continuam dependendo do ambiente-alvo. Nenhuma alteração exigida ao código nesta revisão.
