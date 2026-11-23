# Integração de fonte sintética independente

**Implementação e ensaio local**, sem conexão corporativa ou declaração de TRL5 homologado. O adaptador acessa um serviço HTTP em processo separado, usa contrato paginado versionado e importa somente depois de reunir e reconciliar o snapshot inteiro. Usa a operação existente `integration/import`, preservando transação, identidade de serviço, detecção e idempotência. Não cria rotas na API do Elo.

## Protocolo e limites

Endpoint único `http://127.0.0.1:PORT/snapshot?page=N`. Somente IPv4 literal de loopback; DNS, outros hosts, credenciais na URL, query fornecida, fragmentos e redirects são recusados. Proxy do ambiente é desativado para esse cliente. Bearer sintético é recebido pelo adaptador e enviado apenas ao endpoint explícito; o CLI o lê de `ELO_SYNTHETIC_SOURCE_TOKEN`, nunca de `.env`. Não registre o valor em comando, arquivo de evidência ou log.

Cada página JSON tem exatamente `contract=elo-synthetic-source-v1`, `synthetic=true`, `snapshot_id`, `page`, `total_pages`, `total_counts` e `dataset` com `employees`, `suppliers`, `contracts`. Snapshot, total de páginas e contagens precisam permanecer iguais. Até10páginas,500registros por tabela e512KiB somados das páginas; também vale o limite canônico512KiB do lote. Índices são1..N, sem links `next` arbitrários. IDs repetidos entre páginas, campos de contrato desconhecidos, versões diferentes, contagens incorretas ou referências inválidas recusam o lote. O schema de cada registro e suas relações são revalidados pela importação existente dentro da transação.

Timeout padrão1s por operação de transporte, até2tentativas por página e orçamento de coleta15s. Só HTTP503 e falhas de transporte recebem retry limitado. HTTP401 e demais estados são erros imediatos. O orçamento é conferido entre leituras do corpo e páginas; uma leitura bloqueada pode ultrapassar o orçamento até o timeout em curso. Não há retry automático da gravação, job persistente ou agendamento instalado.

A origem persistida é `source_id`, nome `http-<snapshot_id>.json`, hash SHA-256 do lote canônico, IDs e contagens. Cada tabela é ordenada por ID antes do hash: mudar a ordem das páginas sem alterar registros não cria novo lote. A identidade idempotente é fonte+conteúdo, não apenas o nome anunciado pelo servidor. A operação registra `local-service`; token, URL e cabeçalhos não são persistidos. Mesma fonte+conteúdo depois de reiniciar ou concorrentemente resulta em um único lote. Fonte ou conteúdo diferente passa novamente pela validação; IDs já existentes não são sobrescritos.

Reconciliam-se IDs recebidos/importados e contagens. Isso comprova consistência da transferência no contrato sintético, **não veracidade ou legitimidade dos dados da fonte**. Nenhuma decisão humana ou impacto é automatizado. A detecção herdada do conector executa as duas regras originais; a terceira regra experimental continua acionada explicitamente, sem mudança silenciosa de escopo.

## Executar o ensaio completo

```sh
.venv/bin/python3 scripts/trl-source-acceptance.py
```

O harness cria processos de fonte separados e bancos temporários próprios. Exercita paginação, sucesso e reinício, concorrência/idempotência,401,503/transporte com retry limitado, schema e snapshot alterados, IDs repetidos, referência ausente, contagem divergente, excesso de bytes, redirect e endpoint externo recusados. Falhas posteriores à primeira página deixam o estado de negócio inalterado. O resultado fica em `output/validation/trl5/source-integration.json`, com hashes e limites. O teste do guard do CLI recusa `data/elo.sqlite3` antes de criar Store; não acessa o banco manual.

Para ensaio manual isolado, o serviço de teste `scripts/trl-source-server.py` usa a mesma variável de token e imprime apenas porta/PID. Inicie em terminal próprio, depois use outro banco fora de `data/`:

```sh
.venv/bin/python3 scripts/trl-source-server.py
.venv/bin/python3 backend/synthetic_source.py --endpoint http://127.0.0.1:PORT/snapshot --source-id ensaio-http --db /caminho/ensaio.sqlite3 --synthetic
```

Configure a variável sintética sem reutilizar a chave OpenAI. Os comandos não definem um serviço permanente. Encerre o servidor ao terminar. O CLI imprime metadados, hashes e IDs sintéticos; erros são genéricos sem corpo remoto ou credenciais.

## Critérios para evolução

Este ensaio demonstra aspectos de falha e transferência possíveis em integrações, com requisitos explícitos definidos antes da execução. O contrato foi criado para o laboratório, não derivado de uma interface corporativa fornecida. Representatividade de schemas, volume, identidade, confidencialidade, periodicidade e semântica ainda precisa ser fundamentada. TLS, mTLS, SSO/MFA, rotação real de credenciais, conectividade externa e disponibilidade não são comprovados por esse serviço local. Revisão independente, validação profissional dos cenários e ambiente-alvo permanecem separadas deste resultado.
