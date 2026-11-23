# Ambiente relevante proposto para o Elo

Data:23/11/2026. Base de partida `ebcc525`. Escopo da tecnologia: fluxo integrado de triagem de indícios, revisão humana, risco/maturidade ilustrativos, planos, documentos e rastreabilidade para uma equipe de controles. Esta proposta NÃO descreve nem certifica o ambiente da CAIXA. As restrições de execução local/sintética permanecem vigentes.

## Critério de maturidade

A referência [NASA/ESTO, TRL para software](https://esto.nasa.gov/trl/) descreve TRL5 como elementos ponta a ponta integrados a sistemas/simulações conformes ao ambiente-alvo, testados no ambiente relevante com desempenho previsto e requisitos de escala documentados. Simulação é permitida, mas a representatividade precisa ser justificada. O número de testes, a presença de IA real ou uma etiqueta de ambiente não comprovam esse requisito isoladamente. A classificação é autoavaliação, não certificação nem aceite do certame.

## Hipótese de uso e fronteiras

- Uma equipe de controles revisa documentos e registros de contratos, empregados e fornecedores, com papéis distintos de analista, revisor, executor e auditor.
- Uma fonte separada entrega lotes paginados com IDs estáveis, versão, origem e parâmetros de reconciliação. Erros de transporte/esquema não podem criar importação parcial. Repetição não pode duplicar casos/eventos de importação.
- O sistema apresenta indícios determinísticos e textos de IA com fontes. A pessoa decide; nenhuma entrada da fonte ou documento pode assumir papel de instrução de autorização.
- Solicitações simultâneas, sessões inválidas e interrupções de processo são condições a exercitar. Retomada deve preservar commits anteriores, arquivos e trilhas verificáveis.
- A capacidade delimitada continua local: até2.000registros por tabela, anexos até1MiB/20MiB total/200arquivos, até200consultas. Esses limites são guardas da implementação, não requisitos fornecidos por um comprador.

## Correspondência e distância para operação

| Dimensão | Representação executável | Justificativa | Distância conhecida |
| --- | --- | --- | --- |
| Fonte | Serviço HTTP separado em loopback, contrato versionado e paginação | Exercita transporte, autenticação de serviço, lote, erros e reconciliação | Contrato sintético; não foi comparado a uma fonte corporativa |
| Identidade | Contas temporárias nominativas por papel, sessões/negativas/segregação no backend | Exercita autorização por ator e ciclo de sessão | Não SSO/MFA, federação ou desligamento automático corporativo |
| Dados | Registros e documentos fictícios com casos positivos/negativos e exceções | Evita dados pessoais e permite expectativa explícita | Distribuição/frequência real, representatividade semântica e gabarito humano não demonstrados |
| IA/OCR | Provedor real em avaliação separada; OCR local; corpus novo congelado | Mede saída real com fonte e condições adversas | Não estima precisão populacional nem uso em todas as classes de documentos |
| Operação | API real, SQLite, processos separados, carga mista, interrupção e recuperação | Reproduz efeitos persistidos e limites de concorrência | Mesmo computador/loopback; sem rede externa, multizona ou disponibilidade prolongada |
| Interface | Jornada canônica desktop/celular com componentes oficiais | Exercita fluxo funcional, teclado e fontes | Não é observação de usuários nem estudo de usabilidade |
| Resultado | Relatórios e exportações vinculados a versões/hashes | Permite revisão reproduzível e identificação de lacunas | Hash local não é assinatura externa ou homologação independente de domínio |

## Critérios definidos antes das novas execuções

1. Integração: lote válido conciliado; repetição idempotente; erro de credencial, contrato, duplicação conflitante ou página interrompida não modifica o estado. Tentativas limitadas, sem seguir redirecionamentos nem acessar destinos externos.
2. Operação: zero erros inesperados; recusas/conflitos esperados contados separadamente; integridade e consistência de snapshot após reinício/restauração; tempos e denominadores explícitos. Metas por cenário no protocolo de operação, antes da carga.
3. IA/OCR: dataset/gabarito congelados antes da primeira resposta; modelo/prompt/hashes registrados. Referência válida não equivale a afirmação sustentada. Avaliação semântica identificada e independente do autor do conjunto; agente não substitui humano. Sem ajuste silencioso de gabarito/prompt após observar resultado.
4. Regressão: build e suíte canônica; testes reais somente explícitos com chave já autorizada; bancos temporários, nunca o banco manual.
5. Revisão: geral, segurança, DBA e performance independentes conforme gatilho. Achados e falhas preservados, sem afrouxar critérios para aprovar.

## Limite da conclusão

A aprovação dos protocolos demonstra comportamento no ambiente SIMULADO DESCRITO. Não demonstra por si só que ele representa suficientemente um ambiente operacional-alvo. O relatório deve separar: (a) comportamento observado, (b) premissas de representatividade, (c) condições não exercitadas. Enquanto faltarem evidências para validar as premissas críticas, a afirmação conservadora permanece TRL4 fortalecido, com evidências preparatórias para TRL5. Custos comerciais, submissão e metodologia CAIXA não são usados como substitutos dos critérios técnicos.
