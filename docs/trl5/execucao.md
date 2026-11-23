# Execução autônoma para evidências de TRL5

Pedido: executar tudo que for possível em paralelo, sem depender do usuário ou da CAIXA, e reportar pendências. Orquestrador pessoal, base `ebcc525`, branch existente `codex/product-vision`. Sem publicação/envio, alteração de credenciais, dados reais ou testes no banco manual.

| ID | Frente / dono | Aceite | Estado inicial |
| --- | --- | --- | --- |
| T1 | Ambiente e rastreabilidade / orquestrador | Hipótese, correspondência e limites definidos antes dos testes; pacote verificável | Protocolo documentado |
| T2 | Integração / trl_integracoes | Serviço separado, paginação, autenticação, erro, reconciliação e repetição sem parcialidade | Em execução |
| T3 | Operação / trl_operacao | Perfis, carga mista, falhas/sessões, reinício/restauração e métricas | Em execução |
| T4 | Avaliação / trl_avaliacao | Corpus novo congelado, IA real/OCR, revisão independente e limitações | Em execução |
| T5 | Revisão / agentes independentes | Geral, segurança, DBA, performance nos deltas aplicáveis | Pendente |
| T6 | Integração / orquestrador | Build, regressão, evidências vinculadas a commit e classificação justificada | Pendente |

As implementações rodam em paralelo; carga sustentada executará sem competir com outros testes pesados. O conjunto de avaliação é novo e reservado à rodada, mas não é um conjunto secreto contra o modelo fundacional nem corpus de domínio homologado. Resultados posteriores serão acrescentados mantendo falhas e critérios originais.
