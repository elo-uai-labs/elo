# Product Vision · execução e critérios de aceite

Referência: **Elo · Product Vision e definição técnica**, Ana Ju, 18/11/2026, fornecido pelo usuário. Registro iniciado em **22/11/2026**. O documento é fonte de requisitos; datas, atividades de terceiros e publicação de materiais nele descritas não constituem autorização operacional. O pedido atual é continuar o desenvolvimento completo usando o orquestrador pessoal.

## Objetivo e limites

Entregar uma plataforma para a 2ª Linha de Defesa acompanhar um sinal desde sua origem até uma decisão fundamentada, seus impactos em risco e maturidade e a execução do tratamento. Os quatro módulos compartilham registros e histórico. IA organiza e explica evidências; decisões de qualificação, impacto e encerramento pertencem a pessoas.

A stack existente é Vite/JavaScript, Porsche Design System **4.10.1**, Python e SQLite. Manter dados sintéticos e execução local. Não publicar no GitHub ou expor o servidor sem nova instrução. Não usar `data/elo.sqlite3` em testes. Pessoas identificadas por texto ainda são autodeclaradas, sem autenticação.

O desenvolvimento completo inclui P0, P1 e P2 abaixo. Uma sprint concluída não significa produto completo. **O usuário escolheu priorizar piloto com usuários reais e integrações autorizadas.** Isso antecipa identidade, permissões no backend, aprovador independente, evidências protegidas e exportação verificável, antes de funcionalidades avançadas de P2. O ambiente atual continua local/sintético até haver condições e autorização para o piloto. **O usuário confirmou login/provedor de identidade, fonte inicial e hospedagem como “a definir”**; não há uma resposta pendente sobre esses três itens. Integrações autorizadas e metodologia oficial dependem da CAIXA; podem ter contratos e adaptadores preparados localmente, mas não podem ser declaradas operacionais com dados inventados.

## Como ler os estados

- **Existente:** implementação identificada no código anterior; aceite histórico em `entrega.md`. Revalidar quando afetada.
- **Parcial:** existe uma parte da jornada; faltam os elementos explicitados.
- **Em execução:** trabalho desta evolução; só mudar para aprovado após evidência observável.
- **Planejado:** não implementado nem validado.
- **Dependência externa:** aceite depende de acesso, metodologia ou decisão externa; registrar separadamente o que pode ser desenvolvido localmente.

## Matriz P0 · demonstração integrada

| ID | Requisito e aceite observável | Estado inicial e lacuna | Sprint / evidência necessária |
| --- | --- | --- | --- |
| P0-01 | Carregar empregados, fornecedores e contratos sintéticos relacionados; padrão positivo conhecido | Existente em `backend/fixture.json`; importação de novas bases em execução | S1: entrada válida persistida; IDs duplicados/referências inválidas rejeitados atomicamente |
| P0-02 | Regra executável identifica coincidência entre fornecedor e aprovador; resultado explica critérios e versão | Existente para o primeiro caso; múltiplos casos e resultado sem indício em execução | S1: positivos, negativos, repetição e regra visível |
| P0-03 | Dossiê com IA real e fontes; modelo/prompt registrados; erro não disfarçado de síntese local | Existente em `backend/dossier.py`; associação factual frase a frase ainda parcial | S1/S4: abrir registros citados; rejeitar fontes inexistentes; E2E real quando configurado |
| P0-04 | Analista aceita, ajusta ou rejeita; descarta, monitora ou qualifica; responsável e justificativa obrigatórios | Existente; identidade autodeclarada | S1: decisões independentes por caso e proteção contra versão de dossiê não revisada; S3: identidade autenticada |
| P0-05 | Fragilidade cria proposta fundamentada de revisão do risco, sem alteração automática | Existente para risco único e controles fixos | S1: isolamento de casos; S2: vínculo explícito ao catálogo de riscos/controles |
| P0-06 | Fragilidade sinaliza dimensão e proposta de revisão humana, com metodologia ilustrativa configurável | Parcial: dimensão e níveis fixos; configurabilidade/avaliação ausentes | S2: metodologia versionada, questionário, evidência, lacuna e cálculo reproduzível |
| P0-07 | Risco e maturidade apresentados juntos; aprovação ou recusa independente com auditoria | Existente | S1: aprovar um e recusar outro, sem decisão cruzada entre casos |
| P0-08 | Recomendação e plano com responsável, prazo, status e evidência | Existente com evidência textual; edição de prazo/responsável, anexos e encerramento separado pendentes | S2/S3: tratamento completo e autoria de cada transição |
| P0-09 | Indicadores refletem alertas, riscos por criticidade, pendências, atrasos e avaliações | Parcial: caso/risco/dimensão únicos; agregação de casos em execução | S1/S2: totais reproduzíveis a partir dos registros, inclusive zero casos |
| P0-10 | Auditoria persistida só de inclusão, com usuário, data, ação, registros e cadeia verificável | Existente com hashes e transação SQLite | S1: compatibilidade com banco anterior e detecção de adulteração; S4: pacote verificável fora da aplicação |
| P0-11 | Sugestão, decisão final e justificativa lado a lado | Existente | S1: seleção correta por caso e persistência após reiniciar |
| P0-12 | Quatro telas conectadas, responsivas e com selo de estado real | Existente; alterações precisam de nova homologação | Todas: Playwright desktop/celular, teclado, PDS hidratado, Porsche Next e glifos webfont reais |
| P0-13 | Relações preservam origem, autor e momento; usuário não copia informações entre módulos | Parcial: vínculos por caso/fonte e eventos, sem catálogo relacional completo | S2: navegar risco → controle → caso → avaliação → recomendação → ação → decisão/evento |
| P0-14 | Jornada inteira executa sem resultados estáticos apresentados como operacionais | Aceite histórico registrado; novo aceite pendente | Todas: banco temporário conhecido, detecção, IA real, discordância, impactos, plano, histórico e reinício |

## Matriz P1 · evolução e piloto

| ID | Requisito e aceite observável | Estado inicial | Dependência / sprint |
| --- | --- | --- | --- |
| P1-01 | Múltiplas tipologias de alertas, cada regra com versão, parâmetros e explicação | Planejado; só vínculo cadastral v1 existente | S4; casos positivos/negativos por tipologia, sem atribuição de culpa |
| P1-02 | Integrações reais autorizadas, com contrato de dados, origem, reconciliação, erro e repetição segura | Dependência externa | S5; autorização, credenciais, amostra e contrato fornecidos pelo titular; adaptadores sintéticos podem anteceder acesso |
| P1-03 | Metodologia oficial de maturidade da CAIXA com versões e rastreabilidade | Dependência externa | S2 prepara motor configurável; S5 aplica metodologia fornecida e homologa resultados |
| P1-04 | Perfis/permissões no backend, segregação e identidade verificável | Planejado | S3; matriz de papéis, autenticação, sessões, testes de negação e limites por operação |
| P1-05 | Relatórios gerenciais com IA; cada frase factual ligada à evidência | Planejado | S4; contrato de afirmações/citações, validação de referências e revisão humana antes da versão final |
| P1-06 | Pacotes completos e verificáveis de auditoria | Planejado | S4; exportar fontes, versões, decisões, planos e manifesto de hashes; verificador independente detecta alterações/omissões |
| P1-07 | Painel de supervisão: concordância, discordância/motivos e alerta de possível aprovação automática | Parcial: comparação individual existente; métricas ausentes | S4; denominadores explícitos, amostra vazia, filtros e heurística explicável sem concluir conduta indevida |
| P1-08 | Laboratório sintético com gabarito e medição de acertos/falsos alarmes | Planejado | S4; organização fictícia versionada, TP/FP/FN, precisão/recall e reexecução reproduzível |
| P1-09 | GRC completo: criar/editar riscos, controles, vínculos, tratamento e revisões | Planejado; catálogo atual fixo | S2; entidades identificáveis, histórico e aprovação dos impactos |
| P1-10 | Maturidade: dimensões, questionário, evidências, lacunas e avaliação versionada | Planejado; só proposta sobre dimensão fixa | S2; resultado reproduzível e rotulagem ilustrativa enquanto metodologia oficial não chega |
| P1-11 | Tratamento: editar atribuição/prazo, anexar execução, solicitar e aprovar encerramento | Parcial: criação e atualização textual existentes | S2/S3; validação de arquivos, segregação e manutenção do histórico |

## Matriz P2 · escala e evolução comercial

| ID | Requisito e aceite observável | Estado inicial | Dependência / sprint |
| --- | --- | --- | --- |
| P2-01 | Integrações adicionais e monitoramento recorrente | Planejado / dependência externa para fontes reais | S6 após S3/S5; agenda, retomada, idempotência, falha visível e origem preservada |
| P2-02 | Análise de vínculos e tendências, com critérios explicáveis | Planejado | S6 após S1/S2; conexões navegáveis, períodos comparáveis e ausência de inferência de culpa |
| P2-03 | Simular cenários e impactos no risco sem alterar avaliação vigente | Planejado | S6 após S2; premissas versionadas, comparação e eventual proposta sujeita à decisão humana |
| P2-04 | Memória institucional apresenta casos semelhantes já tratados | Planejado | S6 após S3; critérios de similaridade, fontes e controles de acesso; similaridade não impõe decisão |
| P2-05 | Assistente conversacional com acesso governado aos dados | Planejado | S6 após S3/S4; recuperação com autorização no backend, citações, abstenção e resistência a instruções nos documentos |
| P2-06 | Ampliação de casos de uso, dados e usuários | Planejado | S7; volume/concorrrência acordados, métricas de cauda/erros, recuperação, migração e testes de carga |

## Ordem de execução e critérios entre sprints

| Sprint | Jornada que deve terminar utilizável | Dependências e critério de passagem |
| --- | --- | --- |
| S1 · Base e inteligência | Importar base sintética, executar detecção, escolher casos, consultar fontes, decidir e acompanhar impactos/planos independentes | Preservar comportamento anterior; importação atômica; ausência de indício válida; indicadores agregados; auditoria íntegra; testes canônicos e E2E |
| S2 · GRC, maturidade e tratamento | Gerenciar registros reutilizáveis e avaliações ilustrativas; criar tratamento completo e solicitar encerramento | S1; relacionamentos sem cópia, versões e justificativas; nada altera risco/maturidade sem pessoa; desenvolver junto aos contratos de acesso de S3 |
| S3 · Identidade e governança de acesso | Entrar com identidade verificável, executar somente ações permitidas e aprovar encerramento por responsável independente | **Prioridade de piloto logo após S1**; pode começar antes de S2 concluir; testes de autorização em cada endpoint, sessões, evidências protegidas e aprovação separada; provedor real pendente; não confundir autenticação local com SSO corporativo homologado |
| S4 · Inteligência verificável | Regras adicionais, laboratório com gabarito, relatório citado, supervisão agregada e pacote de auditoria | S1–S3; avaliação medida e reproduzível; fontes verificáveis; exportação íntegra |
| S5 · Piloto autorizado | Conectar fontes reais permitidas e metodologia oficial | S3/S4 + dependências externas; contrato de dados, segurança/homologação e ambiente aprovados pelo responsável |
| S6 · Análises e assistência | Tendências, cenários, memória institucional, assistente e monitoramento | S2–S4; pode começar com dados sintéticos antes de S5; permissões, explicações e ausência de efeitos automáticos |
| S7 · Escala e operação | Operar o volume acordado com recuperação e evidência de confiabilidade | Metas de usuários/dados/latência e ambiente conhecidos; teste de carga, backup/restauração e observabilidade |

Ordem priorizada para o piloto: S1 → fundamentos de S3 e S2 → pacote verificável/evidências protegidas de S4 → S5; demais análises de S4 e P2 seguem após esses controles. Nenhuma integração com dados reais deve preceder autorização de acesso e controles necessários. O escopo completo permanece registrado; a priorização não o reduz à primeira sprint.

As sprints organizam o trabalho técnico. Não substituem os cinco marcos contratuais mencionados no documento, cujo conteúdo estava em elemento incorporado não fornecido. Não estimar pagamentos ou declarar aceite contratual a partir desta tabela.

## Dependências e trabalho fora do código

| Item | Ação possível agora | O que falta para concluir |
| --- | --- | --- |
| Identidade do piloto | Definir matriz de permissões no backend, sessões e aprovador independente; testar com identidades sintéticas | Provedor escolhido e configuração autorizada; critérios de segregação e ciclo de acesso |
| Hospedagem do piloto | Preparar configuração, inventário de segredos e requisitos de operação sem publicar | Ambiente-alvo, responsáveis, acesso e autorização de implantação |
| Metodologia oficial CAIXA | Motor ilustrativo configurável, claramente rotulado | Documento oficial, pesos, regras e validação do responsável |
| Fontes corporativas | Contratos de importação, dados sintéticos e testes de falhas | Autorização de uso, acesso, classificação, retenção e homologação |
| Segurança corporativa/nuvem | Revisões defensivas e documentação do ambiente local | Anexo de requisitos, ambiente-alvo e avaliação técnica; não declarar conformidade antecipada |
| Escala | Medições locais com limites documentados | Volumes, concorrência, disponibilidade e infraestrutura-alvo acordados |
| Licenças/custos/horas | Inventário da stack e premissas de esforço por sprint | Dimensionamento, fornecedores/modelos e licenças de distribuição verificadas; nenhuma estimativa validada ainda |
| Benefício operacional | Definir tarefas comparáveis antes/depois, duração, retrabalho e completude | Medição com usuários; não prometer redução percentual sem evidência |
| Vídeo, anexos e submissão | Roteiro de demonstração apoiado em funcionalidades comprovadas | Solicitação específica, revisão humana e autorização de publicação/envio; datas do documento não acionam esses atos |

Público usuário: analistas e gestores da 2ª Linha. Comprador pretendido no documento: CAIXA no contexto do CPSI. Hipótese de valor: reduzir reunião manual de evidências e tornar decisões/impactos rastreáveis. Esta execução técnica não conclui análise comercial, comparação de concorrentes ou precificação.

## Verificação e retomada

Comandos canônicos: `npm run build`, `npm test`; modelo real configurado: `ELO_TEST_DOSSIER=real npm run test:e2e`. Os testes devem usar bancos temporários, preservar o banco manual e comparar persistência após reiniciar. Alterações de schema/importação acionam revisão DBA; entradas e permissões acionam segurança; lotes e escala acionam performance com limites explícitos.

Evidências executadas e revisões devem ser registradas em `entrega.md`, com versão/snapshot, ambiente, resultado e limitações. A matriz é planejamento verificável, não prova de aprovação. Antes de cada retomada, conferir os arquivos atuais, testes, mudanças locais e o estado de cada requisito; antes de encerrar o produto completo, exigir evidência para todos os IDs, distinguindo claramente dependências externas.

### Registro incremental S1

Revisão DBA independente, somente leitura: 23 testes de backend passaram; conferidos estado bruto antes da projeção, compatibilidade de hashes legados, importação atômica, limites de registros, isolamento de atualização de planos entre casos, preservação das fontes e exportação do estado bruto. Sem achado bloqueador no escopo local/sintético. Snapshot revisado por SHA-256: `backend/domain.py` = `45d2db8069235b170034d8486e65ca2ab11e4d32f0b1326ae12d61d48fd581d0`; `backend/server.py` = `2cd4a03f18dcb5d1b9a340bd442539917dcf5ff5bb3341db9ca888b70863bd51`; `backend/audit_export.py` = `96f228b559f73bed6d7c402a3c64723bb69e0ce4a4ff6b48694564fcae6d0cd1`. Alterações posteriores exigem nova conferência do trecho afetado. O repositório não tinha HEAD no início da revisão; hashes identificam os arquivos sem alegar revisão de commit inexistente.

Medição local **informada pelo orquestrador**, sem revisão independente de performance por este revisor DBA: 2.000 contratos, 1.999 casos, 40 leituras com concorrência 4; detecção em 0,062 s; leituras p95 de 0,237 s e máximo de 0,254 s. Limite provisório: abaixo de 2 s. Essa amostra não certifica capacidade do piloto, carga sustentada ou comportamento com histórico longo. Leitura/verificação integral da trilha e serialização do estado por operação permanecem pontos de atenção para escala.

Próximo trabalho de modelagem: S2, registros reutilizáveis de GRC/maturidade e relações versionadas; aceite ainda pendente. Manter o planejamento de identidade/permissões de S3 junto a essa modelagem e conservar os estados da matriz até a verificação correspondente.
