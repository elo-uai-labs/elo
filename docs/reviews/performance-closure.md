# Revisão independente de performance · fechamento local

Revisor: agente `consumo_ia`, diferente dos autores do harness (`capacidade_final`) e das correções de runtime (orquestrador). Revisão de código e evidências; não reivindico execução independente da carga, realizada pelo autor do harness. Data: 23/11/2026.

**Aprovado no protocolo local delimitado**, com runtime `e72d5be81fc61dcc5092d21b674c8d72a3ba72ee`, incluindo `64de64f1b64d09420d168c22e27b0d1f21aa50d5`, e harness `790ce8c`. Não é homologação produtiva nem capacidade garantida do piloto.

## Critérios e cobertura

Conferi os critérios registrados antes da execução: p95 < 2 s, zero erros, estado de negócio idêntico após as leituras, integridade de ambas as trilhas e contagem exata de acessos. O harness usa exclusivamente banco temporário e loopback, sem `.env`, modelos ou banco manual. Seed e histórico passam pelas operações normais; não injeta snapshots. GET `/api/state` lê/decodifica o corpo inteiro e verifica a auditoria; append real da trilha HTTP participa da latência.

São cinco etapas com 200→2.000 contratos, 199→1.999 casos, mais 250 revisões sintéticas; 120 s programados com concorrência 1/4/8. Cada cliente espera 50 ms entre chamadas. Medidas incluem p50/p95/p99/máximo, terços temporais, vazão, tamanho da resposta e RSS amostrado. Conferi identificação do primeiro cenário que falha, critérios booleanos, preservação dos resultados anteriores e hashes do runtime na evidência final.

## Achados e correções

1. A execução `capacity-local-final.json` falhou: c4 grande teve 2 erros HTTP em 433 tentativas e dois eventos de acesso ausentes; c8 teve 2 erros em 109 e p95 3,250 s. Integridades permaneceram válidas. A evidência anterior não tinha classificação suficiente para atribuir causalidade exata; não se conclui retrospectivamente um código SQLite específico. O launcher posterior registra somente tipo/código/nome de erro, sem payloads ou segredos.
2. `64de64f` reduz trabalho redundante: sets para pertencimento, remove deepcopy somente do snapshot de leitura recém-decodificado e libera a transação antes da projeção. Outros chamadores mantêm cópia por padrão. O snapshot consistente já está inteiramente em memória; não há cache compartilhado. Regressões cobrem escrita durante projeção e ausência de persistência por mutação do resultado. Na repetição `capacity-local-optimized.json`, c4 ficou p95 0,442 s e zero erros, mas c8 ainda falhou p95 2,210 s.
3. `e72d5be` coordena append por instância com `Lock`, antes da conexão/BEGIN IMMEDIATE, até commit/rollback e fechamento. Não remove verificação integral da cadeia, não aumenta timeout e não substitui a coordenação SQLite entre processos/instâncias. Context managers liberam o lock em falha; não há chamada recursiva. Teste cobre 8 threads, 40 registros, duas instâncias e recuperação após falha. A repetição coordenada passou.

## Resultado final observado

Fonte: `output/validation/capacity-local-coordinated.json`.

| Etapa | Requisições | p95 (s) | Máximo (s) | Erros |
| --- | ---: | ---: | ---: | ---: |
| 200 contratos, c1 | 139 | 0,021 | 0,040 | 0 |
| 200 contratos, c4 | 699 | 0,073 | 0,214 | 0 |
| Histórico +250, c4 | 792 | 0,087 | 0,371 | 0 |
| 2.000 contratos, c4 | 705 | 0,316 | 0,386 | 0 |
| 2.000 contratos, pico c8 | 173 | 0,792 | 1,036 | 0 |

Total de 2.508 requisições e 2.508 eventos de acesso; contagem exata em cada etapa, snapshots inalterados, cadeias válidas e `PRAGMA integrity_check=ok`. Nenhum diagnóstico de falha de append. Pico RSS amostrado 341.248 KiB no c8.

A comparação usa o mesmo protocolo temporal e volumes de negócio, mas **não a mesma quantidade de chamadas nem o mesmo histórico final de acessos**: clientes de ciclo fechado variam vazão com latência. As sondagens não são amostras randomizadas/repetidas suficientes para atribuir percentuais universais de ganho. A melhora observada e o cumprimento da meta final são válidos apenas nesta execução. Os dois minutos não certificam operação contínua em dias; não medimos CPU/disco saturados, renderização de 2.000 contratos, autenticação, anexos, OCR, IA, rede externa, múltiplas instâncias ou taxa fixa de chegada. Nenhum ponto máximo de capacidade é conhecido porque o último protocolo passou.

## Identificação por SHA-256

- `scripts/capacity-local.py`: `86e9a973d7561ce509ebc4117da8f9bfc02663d907a28d81d79666b5d040ddd2`.
- `scripts/capacity-server.py`: `c8dd2b691d33749c0066dec0d169d7396de7be2e2899625f5856850b7452738e`.
- `backend/domain.py`: `f943739f52d1ae05fb67daf6cf594f29c7269ed298af8958409d1dd9c6620214`.
- `backend/access_audit.py`: `581f9c825ef6753d73bf4e705e1bbc3909feb10845bbed094de1a89d969070fc`.
- `capacity-local-final.json`: `04454780293912b93e780df10ab9c22933f8bf28e9da4b550a5b1ddeeda385a4`.
- `capacity-local-optimized.json`: `ecaa019e76997076f66ccb0aae0c979ce0bdc613d96e789188a43ce4c99c1ce5`.
- `capacity-local-coordinated.json`: `fe8fcc86b3af5ddb70e193014d1940bfd3001fe6bdddd2cb199f5f2579494b09`.
