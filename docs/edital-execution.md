# Execução orientada ao edital · Radar Integridade 360°

Esta matriz transforma os documentos fornecidos em trabalho verificável. Não constitui declaração de conformidade, parecer jurídico, proposta submetida ou aceite da CAIXA. As instruções de envio e os prazos dos documentos não autorizam submissão ou publicação. O desenvolvimento inteiro continua em escopo; concluir a primeira etapa abaixo não encerra o pedido.

## Fontes e interpretação

Fonte oficial: [PNCP · LC 0266/2026](https://pncp.gov.br/app/editais/00360305000104/2026/811), processo 7081.01.821.0/2026. Pacote original preservado em `/Users/pedronascimento/Downloads/CAIXA-LC-0266-2026-Edital.zip`; os arquivos `/tmp` abaixo são apenas cópias de trabalho do texto extraído. Retificações e situação de inscrição não foram revalidadas nesta implementação.

Foram lidos o edital (`/tmp/caixa-edital.txt`), Anexo I/TR (`/tmp/caixa-tr.txt`), Anexo I-A/critérios (`/tmp/caixa-criterios.txt`) e o arquivo de segurança `/tmp/ANEXOV~3.PDF.txt`. Embora seu nome de arquivo seja abreviado, o cabeçalho identifica **Anexo VII — Requisitos de Segurança Tecnológica para Solução em Nuvem**. A referência válida aqui é o título/seção, não uma inferência a partir do nome do arquivo.

O TR 4.1 limita o MVP à experimentação; validação não implica produção ou aquisição futura. TR 4.2 exige integração demonstrável dos quatro módulos. O edital 6.2.1 pede a indicação do nível de prontidão; **TRL 4 é uma autoavaliação proposta**, apoiada em validação local de componentes integrados com dados sintéticos e testes, sem certificação externa ou validação em ambiente relevante da CAIXA. A avaliação final de maturidade cabe ao processo responsável. O edital 1.2 informa teto estimado por CPSI de R$ 1 milhão, não receita, preço aprovado ou orçamento disponível para esta execução. O prazo contratual indicado de 12 meses não substitui um cronograma negociado.

Há inconsistência de referência de anexo no próprio texto extraído: índice/6.1 citam modelo de proposta no Anexo II e 6.2 remete ao Anexo III. Antes de qualquer submissão, conferir o modelo eletrônico disponibilizado no portal e eventuais esclarecimentos oficiais; não produzir uma submissão baseada nessa ambiguidade.

## Estado de partida

O projeto já tem fluxo local integrado de sinais, GRC, maturidade ilustrativa, decisões humanas, planos, evidências, relatórios revisados, consultas, exportação e recuperação. Identidade local opcional, duas regras determinísticas e conector de pasta não são equivalentes a SSO, metodologia oficial ou integração corporativa. Aprovações dos checkpoints anteriores são registradas em `entrega.md` e não antecipam aprovação das alterações desta execução.

Lacunas prioritárias: gestão explícita de trabalhos e demandas da 2ª Linha; cobertura de acessos/consultas/negações na auditoria; configuração versionada das regras; laboratório com gabarito para ambas as tipologias; processamento restrito de conteúdo não estruturado; plano mensurável de experimentação e composição de custos. Essas lacunas podem avançar localmente e não devem ser rotuladas como dependências externas.

## Matriz operacional

| ID / referência | Lacuna e trabalho | Aceite observável | Estado / dependência |
| --- | --- | --- | --- |
| E01 · TR 4.1.1 módulo 4; critério 1 | Entidade de trabalho/demanda: objetivo, escopo, prioridade fundamentada, responsável, prazo, status e vínculos com casos/planos | Criar demanda, vincular caso existente, registrar análise, acompanhar pendência e concluir com justificativa; métricas derivadas dos registros e persistência após reinício | Backend integrado e revisado; testes de ciclo/CAS passaram; jornada UI desktop/celular e autenticada aprovada localmente |
| E02 · TR 4.2 | Demonstrar compartilhamento entre quatro módulos, inclusive trabalho da 2ª Linha | Uma jornada reutiliza IDs/evidências da detecção no trabalho, decisão, risco, maturidade, recomendação e relatório; nenhuma recópia manual necessária | Backend estendido; compartilhamento UI da nova jornada aprovado localmente |
| E03 · critério 6; Anexo VII 1.23–1.24 e 6.1–6.2 | Trilha independente de acessos HTTP, login/logout, consulta, download, exportação, negação e alterações | Eventos canônicos com autor/modo, horário UTC, ação, recurso, resultado e IP de socket; ausência de senha/token/body/query; adulteração impede append/export; concorrência preserva cadeia | Integrado no HTTP; seis testes do módulo e dois HTTP passaram; jornada UI desktop/celular e autenticada aprovada localmente |
| E04 · critério 6, continuidade | Incluir nova trilha em backup/restauração e exportação separada | Cópia preserva eventos; origem adulterada não publica destino; pacote separado valida cadeia e manifesto; estado bruto de negócio e hashes legados inalterados | Backup integrado e sete testes passaram; exportação HTTP verificada; UI de exportação aprovada localmente |
| E05 · critério 2, configurabilidade | Parâmetros de detecção explícitos, validados e versionados | Alterar configuração com justificativa/CAS, executar ambas as regras, observar versão/valores no sinal e auditoria; casos antigos preservam configuração original | Backend configurável integrado; testes puros/runtime passaram; metodologia sintética explícita; UI desktop/celular aprovada localmente |
| E06 · critério 2, padrões e desempenho | Laboratório independente para as duas regras | Gabarito manual com positivos e negativos, código vazio, não aprovador, fornecedores distintos e códigos diferentes; TP/FP/FN/TN, precisão/recall, denominadores; alterar saída artificialmente deve produzir FP/FN | Duas fixtures independentes implementadas e seis testes do laboratório passaram; resultado não estima acerto real |
| E07 · critério 2, não estruturados | Extrair e relacionar conteúdo textual local restrito | Formatos declarados, limite de bytes/caracteres e codificação; rejeitar binário/arquivo inválido; origem, hash e trecho citável preservados; conteúdo é dado, nunca instrução; revisão humana antes de reutilização | TXT UTF-8 até 32 KiB implementado, revisão humana e integração de fontes aceitas; dois testes passaram; PDF/OCR não implementados |
| E08 · TR 3.1/4.1.1 módulo 2 | Aplicar metodologia de maturidade oficial | Versionar instrumento/pesos/regras; reproduzir cálculo com amostra fornecida e aceite do responsável | Motor ilustrativo existente; metodologia e homologação CAIXA são dependência externa |
| E09 · TR 3.1, integrações | Conectar fonte real autorizada | Contrato de dados, finalidade, periodicidade, volume, IDs/origem, rejeição e reconciliação; repetição não duplica eventos/casos | Conector sintético existente; fonte, credenciais, classificação e autorização são externas, a definir |
| E10 · Anexo VII 1.1–1.22/3.1–3.5 | Identidade corporativa, MFA, ciclo de acesso e segregação administrativa | Integração com provedor definido, testes de desligamento/revogação, menor privilégio e evidência de revisão periódica | RBAC local existente; integração e modelo corporativo a definir, não homologados |
| E11 · TR 5.2; critério 3 | Plano de experimentação comparável e executável | Instrumento abaixo preenchido com amostra, linha de base, meta, responsável, método e evidência; aprovação antes do piloto | Minuta local pronta; metas e aceite conjunto externos |
| E12 · critérios 4/5 | Custos diretos/indiretos e benefício com premissas transparentes | Planilha calculável com horas/quantidades/preços, cenários de volume e limites de cobrança; nenhum benefício percentual sem medição | Estrutura abaixo pronta; valores comerciais e cotações ainda não definidos |
| E13 · Anexo VII 2/5/7/8/9/11 | Implantação segura, chaves, TLS, certificações e continuidade em nuvem | Evidências específicas do provedor e arquitetura escolhidos, testes de failover/recuperação, gestão de chaves e documentação exigida | Trabalho de arquitetura/inventário pode iniciar localmente; ambiente, provedor e documentos externos a definir |
| E14 · critério 6; Anexo VII 10/12 | Incidentes, retenção, exportação, migração e descarte | Procedimentos com responsáveis/canais, ensaio de incidente, inventário de dados, retenção acordada e teste de saída; exclusão apenas com autorização | Backup local existente; políticas organizacionais por elaborar, SLA/retenção/aceite externos a definir |
| E15 · critérios 2/3 e TR 5.1 | Desempenho, usabilidade e confiabilidade do escopo ampliado | Casos desktop/celular/teclado, negativas de acesso, estado após reinício; medir p50/p95/erros com carga declarada e dados temporários | Revalidar a cada etapa; nenhuma certificação de escala atual |

## Etapas de implementação e passagem

1. **Trabalhos da 2ª Linha e auditoria de acessos.** Entregar E01–E04 integrados, revisão DBA independente, negativas HTTP e jornada UI desktop/celular. Um log de requisição não substitui o evento transacional da decisão. Eventos de acesso e negócio têm cadeias separadas; falhas de resposta não devem ser narradas como reversão de uma decisão já persistida.
2. **Detecção configurável e laboratório.** Entregar E05–E06 para ambas as tipologias, com configurações históricas preservadas e avaliação independente. Evidenciar zero resultados, reexecução e mudança de parâmetro; não calibrar gabarito usando o mesmo algoritmo avaliado.
3. **Conteúdo não estruturado restrito.** Entregar E07 em escopo explícito e local, com testes de entrada adversa, fonte citável e nenhuma decisão automática. Não alegar leitura de PDF/OCR se somente texto é suportado.
4. **Experimentação, custos e aceite operacional.** Consolidar E11–E15 com evidências das etapas anteriores, executar testes canônicos e E2E real quando configurado. Fechar pendências de código local; separar itens externos por responsável/artefato necessário. Não parar o pedido integral ao concluir a etapa 1.
5. **Piloto autorizado.** Somente após definição de E08–E10 e ambiente autorizado, executar plano aprovado com usuários/dados/fontes delimitados. A aprovação do protótipo local não é aprovação de implantação.

## Minuta do plano de experimentação

Unidade de comparação: a mesma tarefa e conjunto de evidências, primeiro no processo de referência documentado, depois no Elo. Registrar quantidade de registros, complexidade, perfil do participante, versão do software/regras/modelo e erros; alternar a ordem quando possível para reduzir efeito de aprendizagem. Não usar tempo de modelo isolado como tempo total do trabalho humano.

| Indicador do TR 5.2 | Método / denominador | Evidência e aceite a pactuar |
| --- | --- | --- |
| Horas de esforço manual | Soma do tempo humano ativo por tarefa; separar espera/tempo de máquina; comparar tarefas equivalentes | Registro de início/fim/interrupções e retrabalho; linha de base e meta CAIXA a definir |
| Consolidação gerencial | Tempo entre solicitação e relatório revisado, incluindo correções | Eventos, versão do relatório e revisão humana; meta a definir |
| Informações consolidadas automaticamente | Campos elegíveis preenchidos por integração/reuso ÷ campos elegíveis totais; classificar intervenção manual | Amostra conferida e dicionário de elegibilidade; meta a definir |
| Rotinas manuais reduzidas | Inventário antes/depois com responsável e frequência, sem contar a mesma rotina duas vezes | Evidência de substituição efetiva; quantidade a definir |
| Rastreabilidade | Registros exigidos com autor/horário/origem/histórico completos ÷ registros exigidos da amostra | Reconciliação dos eventos de negócio e acesso, exportações verificadas; cobertura esperada a pactuar |
| Disponibilidade/atualização de painéis | Sondas bem-sucedidas ÷ tentativas e atraso entre evento e painel | Janela e frequência documentadas; não extrapolar disponibilidade produtiva de teste local |
| Tratamento de demandas | Tempo da entrada à conclusão por demanda, segmentado por tipo/prioridade; abertas relatadas separadamente | Histórico de trabalhos e distribuição/mediana, não só média; meta a definir |
| Recomendações e planos | Contagem de IDs únicos por status, prazo e vínculo; sem confundir volume com efetividade | Reconciliação do painel com exportação |
| Requisitos aceitos | Requisitos obrigatórios aceitos ÷ requisitos aplicáveis por módulo, mais teste de integração | Matriz assinada pelo responsável do piloto; autoavaliação não conta como aceite externo |

Casos sintéticos mínimos: sinal verdadeiro plantado; negativo; falso positivo plausível para revisão; regra reconfigurada; decisão discordante; responsável sem permissão; evidência adulterada; importação repetida; contexto obsoleto; recuperação de backup; demanda com pendência e encerramento. Para cada caso registrar resultado esperado independente, observado, defeitos e evidência. Tamanho de amostra e duração do piloto dependem de acordo; não foram inventados resultados de participantes.

## Custos e hipóteses

Modelo calculável: **implantação = Σ(horas por função × custo/hora) + serviços/licenças iniciais**; **operação mensal = infraestrutura + armazenamento/backup + observabilidade + modelo + suporte/manutenção + licenças + tributos/indiretos explicitados**. Custo total do experimento soma implantação, meses de operação e contingência identificada. Evitar dupla contagem de salários no custo/hora e despesas indiretas.

| Grupo | Quantidade/premissa a registrar | Estado |
| --- | --- | --- |
| Desenvolvimento, integração e parametrização | Horas por etapa/perfil, quantidade de conectores e regras, metodologia importada, retrabalho previsto | A estimar; sem taxa ou esforço comercial aprovado |
| Infraestrutura/continuidade | Usuários simultâneos, eventos/dia, retenção, GiB de anexos e crescimento, zonas/backup, RPO/RTO | Ambiente e volume a definir; SQLite local não serve como preço de nuvem |
| IA | Consultas/dossiês por mês, tokens médios de entrada/saída, tentativas, modelo local ou API, limites | Medir consumo; não presumir uso gratuito ou custo zero do hardware local |
| Suporte e capacitação | Pessoas/horas, janelas de atendimento, treinamentos, resposta a incidentes e manutenção | SLA e equipe a definir |
| Segurança e licenças | Provedor identidade, gestão de chaves, auditoria/pentest, certificações e direitos de uso/distribuição | Inventariar e cotar antes de precificar; dependência de terceiros não deve ficar oculta |
| Desmobilização | Exportação, migração, retenção transitória, descarte e evidências | Procedimento/volume a acordar |

Construir cenários baixo/base/alto variando volumes explicitamente, mantendo preços de referência e data da cotação. Benefício monetário, se usado: horas evitadas **medidas** × custo/hora validado, descontando operação incremental. Prevenção de fraude/perdas é hipótese de valor e não receita/benefício comprovado pelo fixture. Teto do edital não deve ser usado para preencher artificialmente custos.

## Limites da evidência de segurança

A nova trilha local amplia rastreabilidade de operações da aplicação. Não monitora acesso direto de administradores ao SQLite nem substitui a solução independente exigida pelo Anexo VII 1.25/1.27. Cadeia de hashes detecta adulteração inconsistente, mas não impede reescrita completa por administrador, remoção da cauda com recomposição do pacote ou exclusão do banco. Retenção corporativa, centralização externa, proteção de chaves, TLS/mTLS, MFA, segregação de ambientes, testes independentes, SOC2/FIPS e disponibilidade multizona não estão certificados.

O Anexo VII contém requisitos de logs, residência/backup, certificações, incidentes e encerramento que exigem arquitetura e evidências específicas do ambiente contratado. Não tratá-los como automaticamente atendidos pela execução em loopback ou por testes unitários. Quadros gráficos que não aparecem no texto extraído precisam de inspeção do PDF original antes de definir SLAs e certificações finais.

No módulo de acesso, a API aceita apenas metadados limitados; login recusado usa ator anônimo, não o nome digitado. IP deriva do socket, sem confiar em cabeçalho encaminhado pelo cliente. A exportação possui cadeia/manifesto independentes e não modifica o hash de negócio. Verificação integral da cadeia em cada append tem custo crescente; o comportamento foi testado em escopo local, e a capacidade com histórico prolongado ainda deve ser medida. Não há descarte silencioso de logs.

## Evidência incremental desta execução

Revisão DBA independente do runtime de trabalhos, regras e integração HTTP/documentos: sem bloqueador no escopo local examinado. O autor do módulo de trilha e backup não reivindica revisão independente de seus próprios módulos; estes foram examinados pelo orquestrador. Testes específicos executados: trabalhos5, parâmetros3, laboratório6, auditoriaHTTP2, documentos2, backup7 e trilha6. A cobertura não substitui aceite da interface ou avaliação corporativa.

Provas em bancos temporários: três conclusões simultâneas do mesmo trabalho produziram uma aprovação e duas rejeições409, sem mudar outro trabalho; ledger previamente corrompido impediu POST com 503 e estado de negócio idêntico. Quando a escrita da trilha falhou **depois** do commit de negócio, a resposta 503 orientou conferir o estado; o evento de negócio já persistido permaneceu íntegro. Não existe atomicidade conjunta entre recibo HTTP e decisão de negócio. O evento de sucesso registra processamento antes do envio, não comprova recebimento pelo cliente.

Sonda HTTP solicitada, executada pelo revisor DBA, **não revisão especializada independente de performance**: 100 GET de `/api/state`, concorrência 4, banco temporário com1 caso,20 trabalhos e22 eventos de negócio; trilha de acesso cresceu de0 para100. Zero erros; p50=0,00580s, p95=0,02664s, máximo=0,20552s. Snapshot de negócio antes/depois idêntico e cadeia de acesso válida. Atende apenas à meta provisória p95<2s nessa amostra; não mede histórico longo, operação sustentada, produção ou limites de capacidade.

Snapshots SHA-256 da revisão final de integração: `backend/domain.py`=`d0e9114ddc63c256fccab0268852a622cd5e67d522d67d4e5f3a144456b3df13`; `backend/server.py`=`556328954d7dd25738388e3e098e02195a441e43f8540ab90d4d959c74397f81`; `backend/consultation.py`=`bb488f0ea062e5aec93444b6c47464979dbd6e537392605c9dca2eac37aa3cec`; `backend/document_analysis.py`=`28d3cbfea66ff950913d623f02f6ab1ccba2b3b40d0000bcd910e8c6696dfa1d`; `backend/dossier.py`=`cc7b1d58390e22428bb78fe14d4eb2c6f39717a0d3c5a7e1f651046b1cf8af4a`. Mudanças posteriores requerem revisão do delta.

Validação final local: build e rodada canônica aprovados com 152 testes backend, jornadas desktop/celular e perfis autenticados. Após ajuste de apresentação do TXT pendente, a jornada completa com Apple Foundation Models real aprovou também consulta do documento revisado, citação EVD-0001 e menção FOR-042; 53 eventos íntegros, cinco casos e persistência após reinício. Fontes Porsche Next verificadas e capturas inspecionadas. Revisões corrigiram logs de requisições malformadas e validação de menções literais nas fontes citadas. Plano residual: homologação por usuários; definir premissas/cotações, políticas operacionais e desenho do experimento com responsáveis; PDF/OCR e editor arbitrário de regras continuam fora desta entrega local. Permanecem externos metodologia CAIXA, identidade corporativa, fonte e hospedagem autorizadas, metas de piloto e evidências de segurança do ambiente. Nenhum desses itens é declarado concluído por esta sonda.

Delta posterior de `backend/server.py` revisado: corrupção estrutural da trilha recebe 503 e log de requisição remove query/sanitiza rota. Dois testes de auditoria HTTP e quatro testes HTTP de documentos passaram. SHA-256 atualizado: `620a6bb3f570c0477e278700c24d98f8e07768b1ccb80d2713ca4d728417839a`.
