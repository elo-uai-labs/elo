# Revisão independente de performance · 23/11/2026

Revisor: agente `/root/revisao_performance`, distinto dos autores de detecção e operação. Commit revisado: `9e4d31834ad6013ef096b2512c4446ab1e511e45`; arquivos conferidos byte a byte contra o commit antes do ensaio. Hashes preservados em `output/validation/performance-parallel.json`. Nenhum código alterado, banco manual acessado, chamada de IA ou serviço externo utilizado.

**Aprovado no escopo local medido, sem bloqueador de performance.** Aceite de capacidade corporativa permanece pendente.

## Critérios definidos antes do ensaio

Meta provisória: p95 inferior a 2 s e zero erros. É a ordem de grandeza usada em verificações locais anteriores, não um SLA acordado com a CAIXA. Cinco segundos por cenário, concorrência 1 e 4, pausa de 50 ms por trabalhador entre chamadas. Carga sintética: 2.000 contratos, 2.000 sinais e 2.000 trabalhos em memória (limite efetivo `MAX_ITEMS=2000`). Comparação de `work.summary` anterior (`ffe684e`) e atual. Leitura transacional/auditoria SQLite em banco temporário com 2.000 contratos e 1.998 sinais; segundo extremo com as três regras e 5.996 sinais sobre os mesmos 2.000 contratos. Os cenários SQLite não possuem 2.000 trabalhos nem histórico extenso de mudanças nesses trabalhos.

## Resultados

| Cenário | Concorrência | Chamadas | p50 | p95 | Máximo |
|---|---:|---:|---:|---:|---:|
| Resumo anterior, memória | 1 | 91 | 0,00116 s | 0,00390 s | 0,00602 s |
| Resumo novo, memória | 1 | 83 | 0,00541 s | 0,01106 s | 0,01606 s |
| Resumo anterior, memória | 4 | 364 | 0,00117 s | 0,00295 s | 0,00644 s |
| Resumo novo, memória | 4 | 338 | 0,00463 s | 0,00759 s | 0,02912 s |
| Leitura SQLite + resumo, 1.998 sinais | 4 | 40 | 0,41062 s | 1,04561 s | 1,10213 s |
| Leitura SQLite + resumo, 5.996 sinais | 4 | 17 | 1,21255 s | 1,58121 s | 1,64269 s |

Zero erros nos cenários. Snapshots e integridade de auditoria mantidos após todas as leituras. Bancos temporários removidos. O banco com 1.998 sinais ocupou 4.861.952 bytes; com 5.996 sinais, 19.423.232 bytes. As três detecções nesse último extremo duraram respectivamente 0,144 s, 0,316 s e 0,546 s. Esses tempos incluem transação, trilha e apresentação.

O agrupamento isolado de perfis repetidos teve medianas de 0,00378 s, 0,00757 s e 0,01637 s para 500, 1.000 e 2.000 contratos. A seleção `next(peer ... != row)` não percorre o grupo inteiro: com IDs distintos, encontra o primeiro ou segundo elemento; portanto não introduz busca quadrática nesse contrato válido. Agrupamento e cópias crescem com os registros; ordenação é O(n log n). Avisos/recorrência também usam agrupamento linear e ordenação das saídas.

## Limites e observações

- O incremento do resumo de operação custa aproximadamente alguns milissegundos nesta amostra. A leitura completa do estado, cópia para apresentação e verificação da trilha dominam a latência SQLite; o servidor continua reescrevendo snapshots completos por alteração, desenho preexistente.
- Retorno do resumo com 2.000 trabalhos/2.000 sinais: 532.788 bytes (2.000 notificações e um grupo de recorrência). A UI limita avisos a 50 e grupos a 20, mas imprime todos os IDs de contratos de cada grupo. Isso pode gerar um bloco de texto longo de até 2.000 IDs; recomenda-se limitar a prévia e oferecer expansão/paginação em evolução futura. Não foi observado bloqueio de execução nesse caminho, mas renderização no volume máximo não foi medida por este ensaio.
- Os cinco segundos são sondas curtas sob carga concorrente, não carga sustentada corporativa. As taxas incluem a pausa de 50 ms e não representam vazão máxima. Não houve curva até saturação, medição de RSS/CPU, HTTP, renderização de 2.000 cartões de trabalho, todos os formatos/anexos, chamadas IA ou longa trilha de eventos. Primeiro ponto de saturação não estabelecido.
- O extremo das três regras ainda ficou abaixo de 2 s, mas o custo cresce materialmente com a quantidade de sinais. Aprovação de capacidade, volumes/concorrência reais, memória, retenção, banco gerenciado e carga sustentada exigem ambiente-alvo e critérios acordados.
