# Capacidade HTTP local e histórico crescente

O ensaio reproduzível exercita o servidor Python real em loopback, com banco SQLite temporário exclusivo e dados sintéticos. Não lê nem altera `data/elo.sqlite3`, não carrega `.env` e não chama modelos. O banco temporário e o processo são removidos ao terminar.

```sh
.venv/bin/python3 scripts/capacity-local.py
```

A saída detalhada é `output/validation/capacity-local.json`. `--output` escolhe somente o arquivo de relatório; não é possível apontar o harness para um banco existente. `--duration-scale 0.02 --output /tmp/elo-capacity-smoke.json` executa uma verificação curta, que **não é evidência de carga sustentada**.

## Protocolo e critérios anteriores à execução

Meta provisória herdada das sondagens locais: p95 abaixo de 2 segundos e zero erros, sem alterações de negócio pelas leituras, com as cadeias de negócio/acesso íntegras. Esses limites não são SLA negociado com a CAIXA. A janela programada soma 120 segundos, mais preparação, chamadas em andamento e verificações.

| Etapa | Base sintética | Concorrência | Janela |
| --- | --- | --- | --- |
| small-c1 | 200 contratos, 199 casos | 1 | 10 s |
| small-c4 | Mesma base | 4 | 15 s |
| history-c4 | Mesma base e 250 revisões de configuração auditadas | 4 | 20 s |
| large-c4 | 2.000 contratos, 1.999 casos, histórico anterior preservado | 4 | 60 s |
| large-spike-c8 | Mesma base ampliada | 8 | 15 s |

Todas as revisões de configuração e importações passam por `Store.apply`, com auditoria normal. Não há injeção direta de snapshots. A configuração continua equivalente e as revisões são sintéticas, sem atividade de analistas reais. O histórico de acesso cresce a cada GET; a contagem final deve corresponder exatamente às tentativas de leitura.

Cada cliente faz GET `/api/state`, lê e decodifica o corpo inteiro, confere `audit_valid` e espera 50 ms antes da próxima chamada. A medição engloba rede local, serialização, projeção do estado e gravação da trilha HTTP. São clientes de ciclo fechado; a vazão diminui quando a latência cresce. O ensaio não representa uma taxa fixa de chegadas e não comprova resistência a sobrecarga ilimitada.

O relatório registra p50/p95/p99/máximo, vazão, erros, p95 em três partes da janela, volume da resposta, pico amostrado de RSS do servidor, tamanhos das trilhas, igualdade do snapshot de negócio e `PRAGMA integrity_check`. Registra hashes do harness e dos módulos Python para identificar o código medido. O primeiro cenário que viola os critérios é identificado explicitamente; ausência de violação não identifica o limite máximo suportado.

## Limites de interpretação

O ensaio mede HTTP e SQLite no computador local. Não mede renderização do navegador com 2.000 contratos, login corporativo, OCR, chamadas de IA, anexos, rede externa, infraestrutura em nuvem, failover ou várias instâncias. O pico de RSS vem de amostras a cada 500 ms e pode perder picos mais curtos; não é medição de saturação de CPU/disco. A duração de dois minutos não demonstra disponibilidade prolongada em dias ou meses. Outros processos locais podem afetar os tempos.

A leitura do estado completo e a verificação integral da cadeia HTTP em cada append continuam pontos de atenção conforme o histórico cresce. Este ensaio amplia a evidência anterior, mas os volumes, taxas de chegada, retenção e metas do piloto real ainda precisam de definição e homologação no ambiente autorizado.
