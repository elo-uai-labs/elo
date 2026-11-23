# Execução autônoma para evidências de TRL5

Pedido: executar tudo que for possível em paralelo, sem depender do usuário ou da CAIXA, e reportar pendências. Orquestrador pessoal, base `ebcc525`, branch existente `codex/product-vision`. Sem publicação/envio, alteração de credenciais, dados reais ou testes no banco manual.

| ID | Frente / dono | Aceite | Estado final |
| --- | --- | --- | --- |
| T1 | Ambiente e rastreabilidade / orquestrador | Hipótese, correspondência e limites definidos antes dos testes; pacote verificável | Documentado; representatividade continua hipótese |
| T2 | Integração / trl_integracoes | Serviço separado, paginação, autenticação, erro, reconciliação e repetição sem parcialidade | Aprovado no protocolo; detalhes abaixo |
| T3 | Operação / trl_operacao | Perfis, carga mista, falhas/sessões, reinício/restauração e métricas | Aprovado no protocolo; detalhes abaixo |
| T4 | Avaliação / trl_avaliacao | Corpus novo congelado, IA real/OCR, revisão independente e limitações | Parcial: falha original IA e triagem OCR4/7 preservadas |
| T5 | Revisão / agentes independentes | Geral, segurança, DBA, performance nos deltas aplicáveis | Revisões independentes registradas; deltas identificados |
| T6 | Integração / orquestrador | Build, regressão, evidências vinculadas a commit e classificação justificada | Build, 237 testes backend, 5 offline e jornadas locais/reais aprovados |

As implementações foram executadas em paralelo; a carga sustentada foi coordenada para evitar competição com testes pesados. O conjunto de avaliação é novo e reservado à rodada, mas não é um conjunto secreto contra o modelo fundacional nem corpus de domínio homologado. Resultados posteriores serão acrescentados mantendo falhas e critérios originais.

## Resultados e retomada

Fonte399a4c2: seis testes; lote atômico/idempotente e falhas sem mutação. Operaçãofc7b248:60s,1251requisições na carga/1288 totais,zero erros inesperados,99 negativas/conflitos esperados,recuperação/sessões verificadas. Complemento96c0e59:OCRreal+duas chamadas OpenAI durante144leituras autenticadas,zero errosinesperados,documento revisado citado e uso auditado. Interrupçãoa4ef5f9/e6ed7ff:SIGKILL dentro da transação,rollback completo/retryúnico.

Avaliação41cf4bc:16tentativasIA/15aceitas/1falha; nas aceitas20afirmações sustentadas por revisão independente de agente. OCR CER0/1170legíveis,mas triagem4/7. Não alteramos corpus ou limiar para aprovar. Correção7ede206 resolve assimetria comprovada por mocks entre menções em dossiês e consultas; uma regressão real separada passou. Falha original não tem causa detalhada preservada, portanto não se atribui causalidade retroativa.

Revisões estão em `docs/reviews/*-trl5.md`; relatórios individuais no pacote. [Conclusão e pendências](conclusao.md) governam a interpretação do resultado, sem promoção automática a TRL5. A retomada deve tratar representatividade, triagem conservadora do OCR e qualidade em corpus independente; não repetir o mesmo conjunto como se fosse novo holdout.
