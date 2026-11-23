# Operação local de equipes · 23/11/2026

Esta entrega amplia a operação sintética existente com avisos dentro do Elo, filtros dos trabalhos, cumprimento de prazo e recorrência de sinais. Não altera prioridades, impactos, responsáveis, decisões ou dados ao calcular indicadores. A leitura usa `/api/work/summary`, com a autorização já aplicada pelo servidor e exigência de trilha íntegra. Não há nova tabela ou migração.

## Jornada

1. Em Plano e auditoria, planeje trabalhos com responsável, prazo e prioridade justificada. Os formulários e permissões anteriores continuam vigentes.
2. Abra **Avisos e acompanhamento operacional** na Visão geral ou em Plano e auditoria. Prazos vencidos, prazos de hoje e dos próximos sete dias corridos aparecem com ID e responsável. Planos aguardando revisão de encerramento também aparecem, independentemente da proximidade do prazo.
3. Use **Atualizar avisos e indicadores** para recalcular pela data do servidor. São avisos calculados ao carregar/atualizar, sem email, push, processamento em segundo plano ou comprovação de entrega/leitura. O horário de referência fica visível. A interface apresenta até os 50 avisos de maior precedência: atrasados, revisão pendente, hoje e próximos dias. O endpoint preserva a lista completa.
4. Na lista de trabalhos, combine situação, prioridade, responsável, pendentes atrasados/com prazo hoje e texto de título/descrição/ID. Filtros afetam apenas a lista, não o universo dos indicadores e avisos. Para limpar, selecione todas as opções e esvazie a busca. Os filtros são temporários da sessão da página e não são gravados no banco.
5. Conclua o trabalho com resultado e justificativa. O aviso de prazo deixa de aparecer. Planos continuam exigindo outro responsável para aprovar encerramento; o aviso de revisão só desaparece quando a pendência é resolvida.

## Definições reproduzíveis

- **Prazo:** dia civil em `America/Sao_Paulo`, até o fim do dia. Hoje não conta como atraso. Janela de aviso: hoje e os próximos 7 dias corridos (hoje até hoje + 7 dias, inclusivos); atrasados também são incluídos.
- **SLA local dos trabalhos:** concluídos até o prazo vigente / concluídos com timestamp válido e fuso. Cancelados e pendentes não entram no denominador. Datas ausentes/inválidas são apresentadas separadamente; denominador zero exibe sem amostra. O prazo vigente pode ter sido replanejado com justificativa, portanto não é medida de cumprimento do prazo original. Não mede horas trabalhadas nem SLA oficial da CAIXA.
- **Recorrência:** mesmo fornecedor e mesma regra em pelo menos dois contratos distintos ao longo do histórico local. O ID do contrato precisa estar nas evidências do caso. Sinais repetidos do mesmo contrato contam uma vez; regras diferentes não são somadas. Exibição limitada aos 20 grupos com mais contratos. Não conclui reincidência de irregularidade ou causa comum.

## Validação

- `python3 -m unittest discover -s backend/tests -p test_operations.py -v`: cinco testes aprovados. Cobrem meia-noite em São Paulo, janela de sete dias, remoção de avisos resolvidos, revisão independente de prazo, denominadores/exclusões, recorrência sem contagem dupla, ausência de mutação e bloqueio por trilha inválida.
- `npm run build`: aprovado.
- `node tests/operations.cjs`: aprovado em Node 24. Cria seu próprio SQLite temporário e servidor em porta dinâmica; verifica filtros combinados, resultado vazio, atualização de avisos, resolução de trabalho e SLA tardio. Desktop e celular sem rolagem horizontal, PDS hidratado via controles reais e glifos de fonte web efetivamente renderizados. Evidências: `output/validation/operations-e2e.json`, `operations-desktop.png`, `operations-mobile.png`.
- Nenhum teste usa `data/elo.sqlite3`. Não foram enviados avisos externos nem alteradas contas reais.

## Dependências preservadas

Metas e responsáveis por SLA corporativo, fonte oficial de calendário/feriados, notificações externas e comprovantes de entrega, capacidade sustentada e validação multiusuário no ambiente da CAIXA continuam dependentes de definição e autorização. A lógica atual não promete alertas com a aplicação fechada. Papéis, revisão independente e controle de concorrência existentes devem continuar sendo verificados na suíte canônica do projeto.

Para manter a leitura utilizável, a recorrência mostra até 20 grupos e até 20 IDs por grupo, com a quantidade adicional explicitada. Os registros completos continuam no pacote de auditoria.
