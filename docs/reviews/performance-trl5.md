# Revisão independente de performance · operação mista TRL

Revisor: agente `trl_integracoes`, diferente do autor do ensaio (`trl_operacao`). Revisão de código e evidências; a carga foi executada pelo autor, não repetida por este revisor. Commit do harness: `fc7b248ae5c82bf7a875f18c0b901b64574c7dd0`. **Aprovado no protocolo local delimitado**, sem achado bloqueador. Não é aprovação de TRL5 nem capacidade produtiva.

## Critérios e isolamento

Conferidos antes da execução:60s de mistura autenticada, p95 das leituras <2s, zero erros inesperados, negativas/conflitos separados, trilhas válidas e recuperação exata dos registros reconhecidos. O harness usa processos/bancos/contas temporários, bind127.0.0.1, credenciais sintéticas aleatórias e chave de modelo vazia. Nenhum banco manual ou serviço externo participa.

São três clientes de leitura e um cliente que serializa o workflow de escrita, não quatro escritores concorrentes. As pausas200ms/500ms caracterizam ciclo fechado; vazão não representa taxa fixa de chegada nem saturação máxima. O tempo inclui requisição HTTP, leitura/decodificação da resposta e lógica do servidor, inclusive auditoria. Hashes dos scripts e de todos os módulos backend conferem com a evidência desta execução.

## Conferência independente dos resultados

Fonte `output/validation/trl-operation.json`; todos os1.288registros de requisição têm status igual ao esperado e `error_type=null`. O total coincide com1.288eventos de acesso no estado final.

| Medida | Resultado conferido |
| --- | --- |
| Janela mista programada / observada |60s /60,363s |
| Requisições na mistura |1.251 |
| Leituras na mistura |792:264state,264work/summary,264supervision |
| Escritas na mistura |459, incluindo90conflitos409 esperados |
| p50 / p95 / p99 de leitura |0,01976s /0,05475s /0,07223s |
| p95 das escritas com expectativa200 |0,07833s |
| Negativas/conflitos em toda a jornada |99, dos quais90conflitos na carga |
| Erros inesperados |0 |
| Estado final |41contratos,40casos,90trabalhos concluídos,19anexos,1relatório,384eventos de negócio |

Conferi a mistura pelas rotas individuais:90criações de trabalho,180transições aceitas e90transições com versão obsoleta recusadas;9importações/detecções/dossiês e18uploads/extrações/revisões/consultas. Dossiês/consultas são síntese local explícita e documentos são TXT literais. Não se atribuem a esses percentis o custo de OpenAI ou OCR.

A contagem de trabalhos coincide com os90ciclos concluídos. Plano encerrado e relatório aprovado. SQLite retorna `ok`, ambas as cadeias são válidas e os acessos são reconciliados com as respostas. As negativas esperadas não são escondidas no indicador de erro inesperado; os denominadores/metadados individuais permitem recontagem. O critério previamente declarado de2s se aplica às leituras; a latência de escrita é descritiva, sem SLA inventado posteriormente.

## Recuperação e limites

O SIGKILL acontece depois dos clientes concluírem e dos commits serem reconhecidos: o snapshot completo permanece igual no reinício, mas isso não prova resistência a corte no meio do commit ou perda elétrica. Sessão anterior é recusada; expiração1s usa relógio real em configuração exclusiva do launcher; logout e conta desativada após reinício são verificados. Não é revogação federada instantânea.

Backup/restauração para destinos novos preserva estado/anexos/trilha e hash da origem. O reinício até health levou0,231s; duas cópias verificadas levaram0,0425s nesta pequena base. Esses tempos não são RTO/RPO contratual nem medição de failover. Configuração de contas e segredos não integra o backup de negócio.

A amostra de60s e41contratos amplia cobertura de concorrência funcional, não substitui ensaio de volume máximo ou observação prolongada. Não mede CPU/RSS/saturação, navegador, TLS, SSO/MFA, rede externa, múltiplas instâncias, participantes humanos, IA real ou OCR. Não há comparação causal antes/depois. A representatividade em relação ao ambiente pretendido continua hipótese a fundamentar separadamente.

SHA-256 da evidência: `42bb3421db0b33597076970cfc202da45bf8bf612c817ed9da7405896f09170d`. Os hashes completos de execução estão no campo `source_sha256` e foram comparados aos arquivos locais pelo revisor.


## Complemento independente: OCR e OpenAI durante leituras

Revisado o commit `96c0e59a629fdf5c10081826e9943e85991164c5`, os dois launchers `scripts/trl-real-operation.py` e `.mjs`, seu protocolo e `output/validation/trl5/real-operation.json`. Não executei chamadas pagas nem repeti carga. **Aprovado como observação funcional curta com concorrência**, sem bloqueador no escopo declarado. Esta evidência não substitui o ensaio de 60s e não demonstra capacidade, saturação ou desempenho causal isolado; outras verificações locais podem compartilhar recursos da máquina.

Conferi os critérios definidos no harness antes da rodada: zero erros inesperados, limite de duas tentativas pagas, documento OCR revisado citado, uso do provedor auditado, integridade/reinício e p95 de leituras inferior a 2s. A exigência de duas respostas na rodada real é mais estrita que o teto de duas tentativas. Os flags são exigidos antes de carregar o ambiente; a contagem ocorre antes de enviar cada chamada real e não há retry no harness. O cliente tem timeout de 15s, menor que os 30s do provedor: uma falha pode consumir tokens sem resposta persistida, limite documentado e não observado nesta rodada.

Recontagem independente dos registros e recálculo do percentil por nearest-rank:

| Medida | Valor conferido |
| --- | --- |
| Janela concorrente observada | 7,8013s |
| Leituras de `/api/state` | 144, todas HTTP 200; 48 por conta |
| p50 / p95 / máximo das leituras | 0,005924s / 0,013602s / 0,017913s |
| OCR / dossiê / consulta | 0,3292s / 4,3341s / 3,1295s |
| Total de respostas API / eventos de acesso | 157 / 157 |
| Negativas esperadas / erros inesperados | 2 respostas 403 / 0 |
| Tentativas pagas / respostas com uso persistido | 2 / 2, modelo `gpt-6.2-sol` |

Os 157 registros se decompõem em 144 leituras, 10 requisições de preparação/revisão/reinício e uma requisição para cada operação OCR, dossiê e consulta. Readiness fica fora desse denominador. Cada status corresponde à expectativa e nenhum `error_type` foi registrado. Há três leitores em ciclo fechado, com espera de 150ms, e uma jornada serial de OCR/revisão/dossiê/consulta; não há três gerações ou três OCR simultâneos. Os tempos individuais de escrita incluem HTTP/processamento, e são uma amostra por operação, sem percentil ou SLA de IA/OCR. A janela não foi fixada antes em 7,8s: termina ao concluir a jornada.

A fixture sintética `table.png` já estava exposta, conferida pelo hash e comparada ao gabarito após normalização NFC/espaços. A aceitação é automatizada pela conta de revisor e não corresponde a validação humana independente. As referências conhecidas no dossiê e o total 330,00 citado na consulta verificam este caso específico, sem estimativa de acurácia geral. Estado protegido permaneceu idêntico após a consulta; reinício preservou snapshot, ambas as cadeias foram verificadas e SQLite retornou `ok`.

Todos os hashes `source_sha256` coincidiram com os arquivos locais no momento desta revisão. SHA-256 do relatório observado: `d1d0ebd4ce5938546e469036b52dd30174aae40a2c20e2b610ba03d9109a7a74`. A conclusão permanece restrita a laboratório sintético, contas locais e loopback, sem extrapolação para CAIXA, TRL5 homologado, produção, distribuição documental, desempenho prolongado ou latência futura do modelo.
