# Matriz de atendimento do diagnóstico

Estados: **implementado local** significa capacidade exercitável com sintéticos; **experimental** exige avaliação de qualidade/escala adicional; **dependência** exige insumo ou aprovação externos; **preparado** é documento/contrato, não integração operante. Uma linha parcialmente atendida não é considerada homologada.

| Bloco de Ana | Estado atual e evidência | Trabalho ainda necessário | Critério para encerrar |
| --- | --- | --- | --- |
| 1. Entrada | Implementado local: JSON/CSV/XLSX, mapeamento, prévia, erros, gravação atômica; `docs/diagnostico-ana-2026-11-23.md`, testes de importação | Adaptador corporativo condicionado ao contrato de fonte em `contratos-externos.md` | Duas bases reconciliadas, positivo/negativo, duplicata e erro preservam integridade; autorização e reconciliação da fonte real no piloto |
| 2. Detecção/correlação | Implementado local: duas regras versionadas, laboratório, agrupamento pelo mesmo contrato e prioridade humana explicada. Terceira tipologia experimental `repeated-contract-profile` em validação nesta execução; seis cenários locais (2 positivos/4 negativos) aprovados | Novas tipologias precisam de campos, gabarito e validação de negócio; a terceira compara mesmo fornecedor/aprovador/título normalizado, sem inferir duplicidade financeira ou regra oficial | Sinais relacionados sem duplicar trabalho; falsos vínculos/limites explícitos; resultados por tipologia contra gabarito aprovado |
| 3. Dossiê/assistente | Implementado local com IA real `gpt-6.2-sol`, fontes por afirmação e revisão; E2E aprovado | Avaliação sintética ampliada concluída (8 respostas, 9/9 afirmações sustentadas por revisão de agente independente, 0/9 omissões); ainda faltam amostra representativa, política de dados e provedor aprovados | Qualidade medida em amostra acordada, modelo/prompt versionados, fontes abríveis e decisão humana; aceite institucional separado |
| 4. Documentos | PDF digital por página, planilha por célula, OCR local de PNG/JPEG/scan; revisão e bloqueio de inconclusivos | Avaliação sintética 0/198 erros nos legíveis e 6/6 triagens esperadas; precisão em documentos autorizados e amostra representativa pendente; OCR segue experimental | Original e localização conferíveis, erro/ausência de texto explícitos; métricas por tipo/qualidade com revisão independente |
| 5. GRC | Implementado local: risco, controle, avaliação, impacto aprovado, tratamento, revisão e histórico | Metodologia da área e medidas de eficácia dos controles | Ciclo inteiro reproduzível com papéis/justificativas; eficácia sustentada por evidência, não apenas encerramento do plano |
| 6. Maturidade | Questionários/pesos/notas versionados e lacunas, metodologia ilustrativa | Instrumento oficial, limiares, papéis, exemplos calculados e homologação | Mesmos resultados dos exemplos oficiais e recomendações rastreáveis; aceite da área |
| 7. Planos/trabalhos | Implementado local: atribuição, prazos, anexos e encerramento independente; testes autenticados | Avisos calculados in-app, filtros combinados, SLA por prazo vigente e recorrência implementados, com teste próprio desktop/celular aprovado; integração final e concorrência no ambiente-alvo são aceites separados | Gestor cria, executor evidencia, outro perfil encerra; notificações/indicadores reconciliados; conflitos não perdem atualizações |
| 8. Rastreabilidade | Trilhas internas de negócio/HTTP, exportação verificada e backup | Âncora/assinatura e retenção em destino externo independente, auditoria de infraestrutura | Adulteração inclusive por administrador detectável fora da base; retenção/restauração demonstradas |
| 9. Acesso | Contas locais opcionais, RBAC, sessão e segregação verificadas | Restrição local `ELO_ENV` (somente local/test) e `ELO_REQUIRE_AUTH=1` implementadas, em validação integrada; SSO/MFA corporativo, ciclo de vida e isolamento de produção ainda pendentes | Identidades reais autorizadas, revogação/negações auditadas, nenhuma autorização baseada apenas em nome enviado pelo cliente |
| 10. Infraestrutura | Loopback Python/SQLite, build, backup/restauração local | Hospedagem, TLS, banco/objetos/chaves gerenciados, observabilidade e metas de carga/RPO/RTO | Ensaio no ambiente aprovado com restauração/capacidade e aceite técnico/segurança |
| 11. Interface/distribuição | PDS oficial 4.10.1, webfont real e desktop/celular verificados | Direitos de identidade visual/ativos e distribuição controlada aprovados | Build e fontes/ícones funcionam apenas com origens autorizadas; termos documentados, teclado/legibilidade verificados |
| 12. Econômico/contratual | Plano experimental e estrutura de custos; kit preenchível neste pacote | Valores-hora, esforço, cotações, cronograma, modelos oficiais II/II-A e condições do certame | Preço reconciliado com fases, volumes e anexos; responsável confirma antes de submissão |

## Trilhas práticas A/B/C

| Pedido | Cobertura e evidência | Estado/pendência |
| --- | --- | --- |
| A1: duas bases e reinício | Fixtures positivas/negativas, UI de importação e comparação de estado após reinício | Aprovado local; conjunto exportável no roteiro |
| A2: perfis diferentes | Teste autenticado de autoria, segregação, plano/encerramento e exportação | Aprovado com identidades sintéticas; SSO real pendente |
| A3: casos/regras/discordância/fontes | Duas regras, decisões independentes e motivo de discordância no E2E | Aprovado local e OpenAI real; não constitui avaliação semântica abrangente |
| A4: capacidades claras | Painel de capacidades/limites e distinção local/experimental/planejado | Implementado; PDF/OCR agora existem localmente, atualizando a lacuna histórica do diagnóstico |
| A5: demo reproduzível/versão | Roteiro, fixtures, manifesto de hashes e commit base | Preparado neste pacote; o manifesto identifica modificações locais |
| B1: CSV/XLSX | Prévia, mapeamento e validação por linha | Implementado local |
| B2: PDF/planilhas/OCR | Localização, revisão e inconclusivo | Implementado/experimental; homologação externa pendente |
| B3: correlação/prioridade | Mesmo contrato, trabalho compartilhável, prioridade humana e desempate explícitos | Implementado local; novas tipologias dependem de gabaritos |
| B4: identidade/logs/infra | Contratos e critérios preparados, controles locais existentes | Integração corporativa dependente de autorização e ambiente |
| B5: maturidade real | Ficha de metodologia e critérios preparados | Depende do instrumento oficial |
| C1: anexos/pitch/preço | Pitch atualizado e mapa de conteúdo para anexos | Modelos oficiais e valores ainda pendentes; nenhuma submissão |
| C2: custos completos | Insumos CSV, reconciliação de cenários e itens do modelo de custos | Estrutura pronta, preço não calculado |
| C3: comprovantes/prazo | Checklist de protocolo em candidatura.md | Prazo vigente não verificado neste trabalho; só usar publicação oficial |

A interpretação do pedido é avançar em tudo que pode ser feito localmente. Não substituímos decisões da instituição por premissas silenciosas, nem consideramos um documento preparatório uma funcionalidade corporativa implementada.
