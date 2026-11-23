# Product Vision · execução e critérios de aceite

Referência: **Elo · Product Vision e definição técnica**, Ana Ju, 18/11/2026, fornecido pelo usuário. Registro iniciado em **22/11/2026**. O documento é fonte de requisitos; datas, atividades de terceiros e publicação de materiais nele descritas não constituem autorização operacional. O pedido atual é continuar o desenvolvimento completo usando o orquestrador pessoal.

## Objetivo e limites

Entregar uma plataforma para a 2ª Linha de Defesa acompanhar um sinal desde sua origem até uma decisão fundamentada, seus impactos em risco e maturidade e a execução do tratamento. Os quatro módulos compartilham registros e histórico. IA organiza e explica evidências; decisões de qualificação, impacto e encerramento pertencem a pessoas.

A stack existente é Vite/JavaScript, Porsche Design System **4.10.1**, Python e SQLite. Manter dados sintéticos e execução local. Não publicar no GitHub ou expor o servidor sem nova instrução. Não usar `data/elo.sqlite3` em testes. O modo demonstrativo mantém pessoas autodeclaradas. O modo opcional de autenticação local está integrado e aprovado no checkpoint S3, com autorização transacional e segregação; não equivale a identidade corporativa homologada.

O desenvolvimento completo inclui P0, P1 e P2 abaixo. Uma sprint concluída não significa produto completo. **O usuário escolheu priorizar piloto com usuários reais e integrações autorizadas.** Isso antecipa identidade, permissões no backend, aprovador independente, evidências protegidas e exportação verificável, antes de funcionalidades avançadas de P2. O ambiente atual continua local/sintético até haver condições e autorização para o piloto. **O usuário confirmou login/provedor de identidade, fonte inicial e hospedagem como “a definir”**; não há uma resposta pendente sobre esses três itens. Integrações autorizadas e metodologia oficial dependem da CAIXA; podem ter contratos e adaptadores preparados localmente, mas não podem ser declaradas operacionais com dados inventados.

## Como ler os estados

- **Existente:** implementação identificada no código anterior; aceite histórico em `entrega.md`. Revalidar quando afetada.
- **Parcial:** existe uma parte da jornada; faltam os elementos explicitados.
- **Em execução:** trabalho desta evolução; só mudar para aprovado após evidência observável.
- **Planejado:** não implementado nem validado.
- **Dependência externa:** aceite depende de acesso, metodologia ou decisão externa; registrar separadamente o que pode ser desenvolvido localmente.
- **Aprovado no checkpoint:** evidência do escopo e versão especificados; não estende o aceite automaticamente a mudanças posteriores nem ao produto inteiro.

Checkpoint atual: **S1 `fb98394`, S2 `4dfb5b5`, S3 `7a86178`, S4 `5c8958a` e S5 `74e512e` aprovados, somente locais**. S6 (consulta governada e backup/restauração) aprovado localmente: 116 testes backend, jornadas canônicas/autenticadas e IA Apple real; evidências em `entrega.md`. A numeração dos checkpoints descreve entregas incrementais executadas e **não equivale à numeração das sprints planejadas abaixo**: em particular, checkpoint S5 não significa realização da sprint de piloto externo. Login corporativo, fonte real e hospedagem permanecem a definir. Produto completo e piloto real não estão concluídos.

## Matriz P0 · demonstração integrada

| ID | Requisito e aceite observável | Estado atual e lacuna | Sprint / evidência necessária |
| --- | --- | --- | --- |
| P0-01 | Carregar empregados, fornecedores e contratos sintéticos relacionados; padrão positivo conhecido | Aprovado S1: importação incremental e validação atômica | S1: testes de entrada válida, IDs duplicados e referências inválidas; revalidar alterações posteriores |
| P0-02 | Regra executável identifica coincidência entre fornecedor e aprovador; resultado explica critérios e versão | Duas regras determinísticas aprovadas no checkpoint S5: aprovador e cadastro compartilhado entre fornecedores | Versões, positivos/negativos, ausência de sinais e repetição; indício não prova culpa |
| P0-03 | Dossiê com IA real e fontes; modelo/prompt registrados; erro não disfarçado de síntese local | Dossiê estruturado v3/v4 com IA real aprovado até checkpoint S6 | Fontes por afirmação e metadados preservados; associação não prova sustentação semântica |
| P0-04 | Analista aceita, ajusta ou rejeita; descarta, monitora ou qualifica; responsável e justificativa obrigatórios | Decisões por caso e identidade local autenticada aprovadas S3 | Justificativa, revisão de dossiê e ator canônico; identidade corporativa a definir |
| P0-05 | Fragilidade cria proposta fundamentada de revisão do risco, sem alteração automática | Aprovado S2: catálogos, vínculos, controle de versão e jornada na interface | Teste impede reduzir risco Crítica após sinal adverso; propostas obsoletas rejeitadas |
| P0-06 | Fragilidade sinaliza dimensão e proposta de revisão humana, com metodologia ilustrativa configurável | Aprovado S2: perguntas/pesos, evidências, lacunas e avaliação versionada | Cálculo e histórico demonstráveis; metodologia continua ilustrativa |
| P0-07 | Risco e maturidade apresentados juntos; aprovação ou recusa independente com auditoria | Impactos separados e revisor autenticado distinto do qualificador aprovados S3 | Versões obsoletas rejeitadas, inclusive administrador sem exceção de segregação |
| P0-08 | Recomendação e plano com responsável, prazo, status e evidência | Planos, encerramento independente e anexos protegidos aprovados S4 | Arquivos imutáveis, limites e snapshot de evidências no encerramento |
| P0-09 | Indicadores refletem alertas, riscos por criticidade, pendências, atrasos e avaliações | Agregação de casos aprovada S1; novos catálogos/avaliações aprovados no checkpoint S2 | Totais reproduzíveis a partir dos registros, inclusive zero casos |
| P0-10 | Auditoria persistida só de inclusão, com usuário, data, ação, registros e cadeia verificável | Auditoria transacional e origem de identidade aprovadas S3; BLOBs e pacote v2 aprovados S4 | Hash verifica consistência local; não prova autoria externa ou resistência a administrador |
| P0-11 | Sugestão, decisão final e justificativa lado a lado | Existente | S1: seleção correta por caso e persistência após reiniciar |
| P0-12 | Quatro telas conectadas, responsivas e com selo de estado real | Jornadas desktop/celular aprovadas até checkpoint S6 | PDS, fontes e glifos oficiais; testes por checkpoint em bancos temporários |
| P0-13 | Relações preservam origem, autor e momento; usuário não copia informações entre módulos | Aprovado S2: IDs, revisões, vínculos e navegação entre registros | Risco → controle → caso → avaliação → recomendação → ação → decisão/evento |
| P0-14 | Jornada inteira executa sem resultados estáticos apresentados como operacionais | Jornada com IA real aprovada até S6, incluindo consulta e recuperação local | Nenhum ambiente corporativo ou escala produtiva homologado |

## Matriz P1 · evolução e piloto

| ID | Requisito e aceite observável | Estado atual | Dependência / sprint |
| --- | --- | --- | --- |
| P1-01 | Múltiplas tipologias de alertas, cada regra com versão, parâmetros e explicação | Duas tipologias executáveis aprovadas S5 | Regra de aprovador e regra de fornecedores compartilhando código; parâmetros determinísticos explícitos |
| P1-02 | Integrações reais autorizadas, com contrato de dados, origem, reconciliação, erro e repetição segura | Dependência externa | S5; autorização, credenciais, amostra e contrato fornecidos pelo titular; adaptadores sintéticos podem anteceder acesso |
| P1-03 | Metodologia oficial de maturidade da CAIXA com versões e rastreabilidade | Dependência externa | S2 prepara motor configurável; S5 aplica metodologia fornecida e homologa resultados |
| P1-04 | Perfis/permissões no backend, segregação e identidade verificável | Autenticação local opcional e permissões integradas aprovadas S3 | Provedor corporativo a definir; sem contas padrão, sem SSO homologado |
| P1-05 | Relatórios gerenciais com IA; cada frase factual ligada à evidência | Relatório governado aprovado S4: reutiliza claims de dossiês revisados | Não faz nova chamada de IA; preserva fontes, modelo, prompt, ressalvas e decisão humana; revisão independente e CAS |
| P1-06 | Pacotes completos e verificáveis de auditoria | Pacote v2 com estado, eventos, manifesto e bytes dos anexos aprovado S4 | Verificador externo à aplicação, cobertura exata e compatibilidade v1 sem arquivos; sem assinatura externa |
| P1-07 | Painel de supervisão: concordância, discordância/motivos e alerta de possível aprovação automática | Supervisão implementada e integrada; proveniência de identidade corrigida S3 | Denominadores real/local e históricos separados; heurística não prova automação; filtros avançados não implementados |
| P1-08 | Laboratório sintético com gabarito e medição de acertos/falsos alarmes | Laboratório sintético reproduzível implementado; gabarito independente e métricas por regra | TP/FP/FN/TN e denominadores explícitos; testes alteram resultados para provar contagem; não estima desempenho real |
| P1-09 | GRC completo: criar/editar riscos, controles, vínculos, tratamento e revisões | Aprovado no checkpoint local S2 | Entidades identificáveis, histórico, arquivamento preservando relações e aprovação dos impactos |
| P1-10 | Maturidade: dimensões, questionário, evidências, lacunas e avaliação versionada | Aprovado no checkpoint local S2 com metodologia ilustrativa | Resultado reproduzível; metodologia oficial continua dependência externa |
| P1-11 | Tratamento: editar atribuição/prazo, anexar execução, solicitar e aprovar encerramento | Tratamento com anexos e segregação autenticada aprovado S4 | Validação e limites de arquivos, download protegido, transação BLOB+evento e encerramento independente |

## Matriz P2 · escala e evolução comercial

| ID | Requisito e aceite observável | Estado inicial | Dependência / sprint |
| --- | --- | --- | --- |
| P2-01 | Integrações adicionais e monitoramento recorrente | Conector sintético por pasta e execução recorrente opcional aprovados S5; integrações reais externas | CLI explícita, idempotência e falha/repetição; nenhum agendamento instalado, nenhuma fonte real conectada |
| P2-02 | Análise de vínculos e tendências, com critérios explicáveis | Vínculos e tendências explicáveis aprovados S5 | Critérios determinísticos, fontes e eventos de integração incluídos; não inferem culpa |
| P2-03 | Simular cenários e impactos no risco sem alterar avaliação vigente | Cenários hipotéticos versionados aprovados S5 | CAS do risco, premissas e comparação; nenhuma alteração automática da avaliação vigente |
| P2-04 | Memória institucional apresenta casos semelhantes já tratados | Memória de casos semelhantes implementada e aprovada S5 | Critério de similaridade explícito e acesso governado; similaridade não determina decisão |
| P2-05 | Assistente conversacional com acesso governado aos dados | Consulta governada aprovada S6 em modos local e IA real | Fontes do caso, citações, abstenção, contexto versionado e arquivo auditado; sem ferramentas de decisão |
| P2-06 | Ampliação de casos de uso, dados e usuários | Backup/restauração local aprovado S6; escala externa pendente | Destinos novos e verificados, origem somente leitura; volume, disponibilidade e infraestrutura ainda não definidos |

## Plano original de sprints e critérios entre etapas

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

O checkpoint S1 foi consolidado no commit local `fb98394`. Os três hashes de revisão acima foram conferidos contra os arquivos desse commit. Build/E2E de S1 aprovados conforme registro do orquestrador; esse resultado não cobre automaticamente o novo fluxo de S2.

### Registro incremental S2, S3 e S4

S2: revisão DBA encontrou e confirmou correções de duas falhas: sinal adverso não reduz risco de Crítica para Alta; propostas legadas pendentes recebem versão do alvo antes da primeira mutação de catálogo, impedindo aprovação de contexto obsoleto. Também foram conferidas revisões de vínculos e rejeição de decisão sobre vínculo não visto. Uma prova concorrente independente obteve uma aprovação de encerramento e uma rejeição 409, com um único evento e trilha íntegra. A suíte executada durante a revisão passou 43 testes de backend. Ajuste posterior de retenção de controles arquivados foi revisto: vínculo antigo pode permanecer, mas não pode ser reintroduzido como nova associação.

S2 foi aprovado e consolidado em `4dfb5b5`, com submissão desktop/celular e IA real confirmadas pelo orquestrador. Uma execução E2E anterior retornou 502 por exigir ID literal na prosa mesmo quando a afirmação tinha fonte estruturada válida. O contrato v3 agora exige `claims[].source_ids` não vazio, composto somente por fontes recebidas; cada lista é mostrada junto à afirmação na interface. Repetir IDs na prosa é opcional. IDs desconhecidos mencionados no texto continuam rejeitados; nenhuma referência inválida é descartada ou inventada para aceitar a resposta. A mudança foi revisada independentemente, seis testes específicos passaram e a repetição E2E real passou. A associação estruturada não certifica que todas as afirmações sejam semanticamente sustentadas. A revisão humana permanece obrigatória.

Revisão DBA e revisão v3 conferidas contra o commit `4dfb5b5`: `backend/domain.py` = `d47431570f35391d539380ee02abf8239ad57560aaf5822eae506ef8da5f8856`; `backend/governance.py` = `94455acb4538a1cb52b70adceb286ae90a3c361e125d03a69f49f50486651cc3`; `backend/server.py` = `b38ff454e42f470691db1bdcc06f20bd23e029358afb73301ea37e6d8a881165`; `backend/dossier.py` = `4f4419ad5c05c6d73a46364a2d8a35b3f901563a299448e738b4d73af073337a`; `backend/on_device.swift` = `046b739184f38dcf2f8127e10b013048269443bd539de5fc9c060b1b1ca2a030`. São os mesmos snapshots revisados; alterações S3 posteriores requerem revisão própria.

S4: laboratório implementado sem acesso a `Store` ou ao banco manual, com versão e hash do fixture, denominadores explícitos, métricas nulas para amostra indefinida e resultados por contrato. Supervisão separa IA real/síntese local e usa heurística descritiva de cinco aceitações rápidas pelo mesmo responsável; não prova automação nem culpa. Exportação verifica consistência de hashes, sem alegar assinatura ou autoria externa.

Registro histórico anterior ao aceite S3: `backend/access.py`, `backend/tests/test_access.py` e `docs/access.md` implementados. Oito testes isolados passaram, incluindo limite concorrente de tentativas, expiração/logout, limites de memória, permissões, atribuição e revisor de impacto distinto do qualificador. A revisão do módulo pelo orquestrador não encontrou bloqueador no escopo local. A integração está em andamento e ainda precisa de aceite de autenticação por rota, ator sobrescrito pelo servidor e autorização dentro da mesma transação da mutação. Não foi criado arquivo de contas do projeto; testes usam configurações temporárias. Provedor corporativo permanece **a definir**.

### Checkpoints S3 a S6 · estado atualizado

S3 `7a86178`: autenticação local integrada com autorização dentro de `BEGIN IMMEDIATE`, ator canônico e metadados confiáveis de origem. Falhas de autorização não alteram estado ou auditoria. Histórico autodeclarado não é retroativamente autenticado. Revisão DBA conferida no commit; testes HTTP e jornada autenticada aprovados pelo orquestrador.

S4 `5c8958a`: anexos em BLOB com metadados/evento na mesma transação, imutabilidade e cobertura exata no snapshot/export; relatórios preservam decisões e fontes revisadas. Provas concorrentes independentes confirmaram limite de arquivos e uma única revisão de relatório. Pacote v2 verifica bytes, tamanho e hashes, mantendo exportações v1 sem anexos.

S5 `74e512e`: segunda tipologia, laboratório ampliado, vínculos/tendências, memória, cenários e conector sintético por pasta. Detecção por regra preserva snapshots anteriores; novo fornecedor pode gerar sinal em contrato antigo. Importação repetida é impedida transacionalmente. Comando de integração não é exposto por HTTP; execução é explicitamente local e nenhuma tarefa foi agendada. Revisão DBA conferida nos hashes do commit, sem bloqueador no escopo verificado.

S6 aprovado localmente: consulta por fontes selecionadas do caso, resposta local ou modelo real, abstenção e arquivo auditado; proíbe gravação de decisões pela IA. Backup/restauração exige origem/destino explícitos, verifica a cópia e publica somente em caminho novo. Testes usam bancos temporários. Seis testes específicos de backup passaram, incluindo escrita concorrente e corrida de publicação. Revisão independente e aceite final registrados pelo orquestrador: 116 testes backend, E2E local/real, autenticação, desktop/celular, persistência e recuperação verificados.

Próximo trabalho dependente de definição externa: piloto corporativo exige provedor, fonte e hospedagem definidos/autorizados, metodologia oficial e metas operacionais acordadas. A entrega local não substitui essas dependências nem comprova produto completo.
