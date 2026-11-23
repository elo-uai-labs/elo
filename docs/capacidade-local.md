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

## Primeira medição e diagnóstico

A rodada anterior à otimização, preservada em `output/validation/capacity-local-final.json`, **falhou** no critério de zero erros: quatro clientes/2.000 contratos tiveram 2 falhas HTTP em 433 tentativas (p95 0,931 s); o pico de oito clientes teve 2 falhas em 109 tentativas (p95 3,250 s). As quatro respostas falhas não produziram eventos de acesso. As cadeias existentes permaneceram íntegras e o estado de negócio não mudou. A medição anterior só registrava a classe `HTTPError`, portanto não permite atribuir retrospectivamente um código de status ou uma causa SQLite específica.

O microperfil `scripts/capacity-profile.py` constrói outro banco temporário com 2.000 contratos e 2.000 eventos HTTP. Mede cinco chamadas isoladas de leitura e cinco de append com overhead do profiler. Em `output/validation/capacity-profile.json`, as cinco leituras somaram 0,789 s; `deepcopy` consumiu 0,455 s acumulados. Os cinco appends somaram 0,202 s e a verificação integral da cadeia 0,197 s. Tempos acumulados são sobrepostos e não devem ser somados. O perfil identifica candidatos, sem reproduzir a contenção HTTP concorrente.

O launcher de teste `scripts/capacity-server.py` acrescenta observação somente das falhas: classe da exceção e nome/código SQLite, sem mensagens, payloads ou credenciais. O harness registra agora códigos HTTP, preservando os critérios originais. Nenhuma alteração de timeout ou flexibilização do critério é necessária para coletar esse diagnóstico.

## Repetição após otimização de leitura

O runtime `64de64f1b64d09420d168c22e27b0d1f21aa50d5` libera a transação SQLite antes da projeção, evita cópia redundante do snapshot recém-decodificado e usa conjuntos na contagem de contratos pendentes. O mesmo protocolo foi repetido, com diagnósticos de falha habilitados. Evidência: `output/validation/capacity-local-optimized.json`.

| Cenário | Requisições | p95 | Erros | Critério local |
| --- | ---: | ---: | ---: | --- |
| 200 contratos, c1 | 147 | 0,024 s | 0 | Aprovado |
| 200 contratos, c4 | 829 | 0,034 s | 0 | Aprovado |
| 200 contratos + 250 revisões, c4 | 726 | 0,121 s | 0 | Aprovado |
| 2.000 contratos + histórico, c4 | 677 | 0,442 s | 0 | Aprovado |
| Mesma base, pico c8 | 172 | **2,210 s** | 0 | **Falhou p95 < 2 s** |

As 2.551 tentativas resultaram em 2.551 eventos HTTP, sem erro do ledger observado. Estado de negócio inalterado, cadeias válidas e `integrity_check=ok`. O pico de RSS amostrado foi 346.304 KiB no cenário c8; sua resposta máxima tinha 3.890.868 bytes. No c4 ampliado, vazão 11,25 req/s e máximo 1,096 s; no c8, vazão 11,21 req/s e máximo 4,563 s. A maior concorrência não aumentou a vazão nessa amostra e elevou a cauda de latência.

A repetição eliminou os erros observados na rodada anterior e melhorou a leitura no cenário c4, mas **o aceite conjunto de capacidade continua reprovado pelo pico c8**. Não aumentamos timeout nem alteramos a meta para aprovar o resultado. A comparação é uma repetição de protocolo local, não experimento rigorosamente controlado: a maior vazão produziu mais eventos de acesso durante a segunda execução. O primeiro limite observado agora é a latência no pico c8. Próximo trabalho concreto: reduzir payload/projeções por consulta e investigar contenção da trilha preservando sua verificação; depois repetir os mesmos cenários. Nenhuma capacidade produtiva foi homologada.
