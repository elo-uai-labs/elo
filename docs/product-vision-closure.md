# Fechamento local do Product Vision · 23/11/2026

Pedido: usar o orquestrador e concluir pendências locais identificadas, mantendo o desenvolvimento completo em escopo. Base `31d9b00`, branch `codex/product-vision`. Sem publicação, envio, banco manual ou alteração de credenciais.

| Frente | Aceite | Estado |
| --- | --- | --- |
| Supervisão P1-07 | Filtros, denominadores explícitos e heurística preservada; desktop/celular/PDS | Aprovado localmente; evidências abaixo |
| Consumo IA | Metadados fornecidos pela API preservados; desconhecido não vira zero; relatório reproduzível sem tarifa inventada | Aprovado localmente; evidências abaixo |
| Capacidade P2-06/S7 | HTTP sustentado, histórico crescente, concorrência, latência/erros/integridade com metas prévias | Aprovado localmente; evidências abaixo |
| Benefício operacional | CSV vazio e agregador de pares equivalentes, negativos/completude, simulação separada | Aprovado localmente; três testes + CLI sintético; revisão independente |
| Documentação | Matriz atualizada preservando checkpoints históricos e dependências | Aprovado localmente; evidências abaixo |

O instrumento de benefício pode ser preparado/testado autonomamente. Resultados humanos exigem participantes e observação; nenhum resultado será inventado. O ensaio de carga local não homologa ambiente/volume corporativo indefinido. Consumo de respostas arquivadas não equivale à fatura de todas as tentativas.

Revisões realizadas sobre commits exatos: geral independente, segurança para metadados/API e entradas offline; DBA para persistência auditada; performance independente da autoria do harness. Correções serão revalidadas. Build e suíte canônica após integração, mais jornada com modelo real configurado.

## Dependências que permanecem fora do fechamento local

- Participantes, tarefas reais autorizadas, critérios e aceite do experimento.
- Provedor de identidade/SSO/MFA, fonte corporativa, hospedagem e autorizações já informadas como a definir.
- Metodologia oficial e homologação de riscos/maturidade; classificação/retenção e controles do ambiente contratado.
- Preços, horas/equipe/prazo/orçamento comerciais e validação final dos modelos/condições de candidatura.
- Capacidade, disponibilidade, RPO/RTO e observabilidade externos conforme ambiente acordado.

Os contratos, minutas e instrumentos locais estão no pacote da Ana. Esses itens não são funcionalidades concluídas por simulação. O fechamento local não declara produto completo, benefício comprovado, certificação ou submissão.

## Correção guiada por carga

A primeira rodada com histórico maior falhou: erros HTTP em c4/c8 e p95 c8=3,250s. O perfil isolado apontou custo da projeção/cópia e da verificação da trilha. `64de64f` liberou a transação de leitura antes da projeção, evitou cópia de snapshot novo e substituiu busca repetida em listas por conjuntos locais. Erros cessaram, mas pico c8 ainda falhou em2,210s. `e72d5be` coordenou appends por instância, preservando BEGIN IMMEDIATE, checagem integral e rollback/commit. O mesmo protocolo passou:2508requisições/2508eventos,zeroerros,p95c4=.316s,p95c8=.792s,máximo c8=1.036s,SQLite/cadeias válidos e estado de negócio preservado.

As rodadas usam ciclo fechado: maior vazão muda a quantidade de logs acumulados. A comparação não é um benchmark de taxa fixa nem prova de ganho causal exato. Evidências falhas foram preservadas e os critérios não foram relaxados. Cenários sintéticos locais,120s de carga,sem IA/OCR/login corporativo/renderização máxima. Ver [protocolo e limites](capacidade-local.md).

## Revisões

[Geral](reviews/general-closure.md), [DBA](reviews/dba-closure.md), [segurança](reviews/security-closure.md) e [performance](reviews/performance-closure.md) registram autores independentes, commits e limites. A revisão geral corrigiu leitura dupla do CSV: hash e agregação agora usam os mesmos bytes (`692bd54`). DBA provou compatibilidade legada, recuperação e escrita concorrente durante a projeção; trilha concorrente testada com duas instâncias. Nenhuma alteração de schema ou reescrita de hashes legados.

## Aceite integrado

`npm run build` e `npm test` passaram após as correções:229testes backend,5testes de avaliação offline e jornadas completas, autenticadas, operacionais e de supervisão. Desktop/celular, PDS4.10.1/Porsche Next com glifos web, auditoria íntegra e persistência após reinício. A rodada local gerou14casos/120eventos em banco temporário. Logs: `output/validation/closure-build.log`, `closure-canonical.log`; resultados `result-local.json`, `result-auth.json`, `operations-e2e.json`, `supervision-e2e.json`. A rodada real possui aceite separado abaixo.

O instrumento de benefício foi exercitado por CLI com dados explicitamente sintéticos: preservou piora de tempo/completude e recusou sobrescrever relatório existente. Evidência `benefit-instrument.json`. Isso comprova cálculo e validação, não ganho operacional humano.

### OpenAI real e disponibilidade local

`ELO_AI_PROVIDER=openai ELO_MODEL=gpt-6.2-sol ELO_TEST_DOSSIER=real npm run test:e2e` passou.14casos/122eventos, fontes verificadas, desktop/celular e estado idêntico após reiniciar. Relatório `usage-report-real.json`:10registros de geração/consulta,quatro respostas OpenAI medidas com2440tokens de entrada/670saída,3110total; seis registros sem medição não foram tratados como zero. Tarifas não fornecidas: nenhum custo monetário inventado. Evidência funcional, não homologação semântica populacional. Logs em `closure-real.log` e resultado em `result-real.json`.

Servidor manual reiniciado com a versão atual; health8001 e frontend5173 responderam200. Nenhum teste usou seu banco. Commits locais, sem GitHub, exposição externa ou envio a terceiros. Pacote documental da Ana regenerado com revisão/evidências desta rodada, mantendo originais e rascunhos comerciais anteriores.

### Resultado e próxima retomada

Pendências locais identificadas nesta retomada concluídas. Para continuar o piloto, preencher as dependências externas listadas acima; aplicar contratos/identidade/metodologia no ambiente autorizado e executar medição com participantes. Não interpretar aceite local como aprovação de todos os itens P1/P2 corporativos. Se volume/histórico/concorrência/ambiente mudar, repetir capacidade com critérios acordados. Relatórios de consumo são CLI; não foi criado um painel de faturamento.
