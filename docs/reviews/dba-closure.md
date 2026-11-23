# Revisão DBA independente · consumo de IA

**Estado:** aprovado no escopo local examinado, sem achado bloqueador. Revisão do delta `f9a573c667bf6b3fe0a7e6aeb1dfdbfc1acce113` em HEAD `8beeeb122b87c3add71281b52973e14912dc9895`. Revisor: agente de supervisão, que não implementou o consumo. A implementação própria de filtros de supervisão não é reivindicada como revisada independentemente neste relatório.

## Escopo e inspeção

Examinados `backend/ai_usage.py`, `backend/dossier.py`, `backend/consultation.py` e caminhos existentes de persistência, exportação e backup. Não há mudança de SQL, schema, migração ou índices. Os metadados de consumo são acrescentados somente à resposta nova; normalização não preenche retrospectivamente consumo em eventos/snapshots antigos. Dossiê persiste conteúdo e evento na transação existente; consulta copia somente o formato validado para o registro e evento. As rotas HTTP geram a resposta no servidor, não aceitam consumo enviado pelo cliente como resposta de IA.

Cada geração de dossiê persistida permanece em seu evento, mesmo quando uma geração posterior substitui a apresentação atual. O relatório soma os eventos de geração/consulta, sem somar novamente cópias dos mesmos dados no estado. Cached/reasoning tokens são subconjuntos: não se somam novamente ao total/custo de saída. Ausência em histórico continua ausência, não zero. Campos desconhecidos da resposta de uso do provedor são descartados.

O CLI lê pacote exportado já verificado e tarifas explícitas; não abre banco, altera dados ou chama API. Estimativa abrange apenas respostas persistidas e não é contabilidade/fatura completa de requisições recusadas, falhadas ou não gravadas.

## Evidência executada

- Quatro testes de consumo passaram: validação de metadados, ausente/parcial/inválido/zero, preços explícitos e conservação após reabertura/exportação com dossiês repetidos e assistente.
- Sete testes existentes de backup passaram, incluindo escrita concorrente, destino novo, corrupção e trilha de acesso.
- Prova adicional independente criou um banco temporário com código anterior ao consumo (`49bcd65a3f93d4871d8706246385ab8d8c048d2c`), via cópia `git archive` da pasta backend. Nenhum arquivo/banco manual foi acessado.
- Abrir com código novo preservou byte a byte os valores SQL de `workflow` e `audit`; o pacote legado permaneceu válido. Acrescentar um dossiê e uma consulta com metadados sintéticos preservou os eventos/hashes legados.
- Backup e restauração para destinos temporários novos preservaram exatamente linhas SQL, eventos, metadados e exportação; a origem permaneceu inalterada. A cadeia restaurada é válida.
- Relatório dos três registros de IA (um legado, dois novos) mostrou 60 tokens informados, dois registros medidos e um não medido. Não foram usados dados de fatura nem chamadas reais de IA.

Evidência estruturada: `output/validation/dba-closure.json`, vinculada ao HEAD examinado. A capacidade com histórico crescente é responsabilidade do ensaio especializado separado; esta revisão não certifica escala corporativa nem contabilização financeira completa.

## Delta de leitura e projeção · 64de64f

**Aprovado:** revisão independente de `64de64f1b64d09420d168c22e27b0d1f21aa50d5`. `Store.read` conserva `BEGIN` durante todas as consultas do snapshot (estado, eventos e BLOBs); fecha a conexão antes da projeção puramente em memória. O snapshot está integralmente materializado por JSON/listas/bytes e não conserva cursor/lazy query. O parâmetro `copy_state=False` é usado somente nesse snapshot recém-criado e privado. Os outros caminhos, inclusive o retorno de `Store.apply`, mantêm a cópia defensiva padrão. Os sets de IDs são variáveis locais de projeção; não substituem listas persistidas nem alteram serialização/hashes.

Dois testes `test_read_projection.py` passaram: escritor da trilha HTTP consegue concluir durante a projeção; mutação pelo chamador não altera persistência; projeção padrão preserva a entrada; contagens pendentes equivalem ao cálculo anterior. Prova adicional independente, temporária e sem carga prolongada, inseriu uma segunda detecção válida por outra conexão durante a projeção: commit concluído, resposta antiga permaneceu igual ao snapshot auditado anterior, estado posterior ganhou exatamente um evento e ambas as cadeias permaneceram válidas. Uma primeira tentativa da sonda repetiu a mesma regra e foi corretamente recusada 409 pela regra de negócio; a sonda válida usou a segunda tipologia. Isso não foi falha do delta.

Hashes examinados: `backend/domain.py` SHA-256 `f943739f52d1ae05fb67daf6cf594f29c7269ed298af8958409d1dd9c6620214`; `backend/tests/test_read_projection.py` SHA-256 `39fe1d3e0e4c10981fdb3a8df564b1370cd668ef49f7c1651fdefea5293281fd`. Sem alteração de schema, escrita de leitura ou exposição do banco manual. Testes de capacidade prolongada ficam no relatório especializado separado.
