# Plano de experimentação · minuta executável

Versão de trabalho sintética, sujeita a aprovação da CAIXA antes do piloto (TR 4.1/5.2). Não declara produção, homologação, ganho econômico observado ou integração real. O escopo técnico completo está em `edital-execution.md`.

## Preparação

Registrar em uma ficha: responsável pelo ensaio, data, commit, sistema operacional, versão do modelo/prompt/regras, hash do conjunto sintético, quantidade de registros, perfis e ambiente. Selecionar explicitamente banco temporário; nunca usar `data/elo.sqlite3`. Identidade corporativa, hospedagem e fonte real: **a definir**. No ensaio usar contas sintéticas nominativas para analista, revisor, executor e auditor; separar autor/aprovador. Nenhuma pessoa real precisa ser provisionada para testar o fluxo.

A equipe de experimentação propõe escopo e instrumentos; a CAIXA define com a proponente amostra, metas, usuários, dados, integrações e critérios de aceite. A quantidade de participantes e a duração não foram acordadas. Preparar uma tabela por execução com: caso, resultado esperado, observado, horário inicial/final, tempo humano ativo, espera, correções, evidência exportada, responsável, aceite e defeito.

## Sequência de casos

| Caso | Módulo / ação | Resultado esperado e artefato |
| --- | --- | --- |
| C01 | Detectar fornecedor/aprovador e cadastro compartilhado entre fornecedores | Positivos e negativos de gabaritos independentes; regra e configuração preservadas, sem atribuição de culpa; resultado do laboratório |
| C02 | Criar demanda da 2ª Linha e vincular sinal | Trabalho com prioridade justificada, responsável, prazo e pendências; caso reutilizado por ID, sem duplicar evidência |
| C03 | Analisar dossiê e discordar | Fontes/claims/modelo/prompt exibidos; decisão humana e razão; sugestão rejeitada não vira fato em relatório |
| C04 | GRC: qualificar, avaliar impacto e revisar controle | Proposta sem efeito automático; revisor distinto aprova/recusa; versão obsoleta recusada; histórico mantém estado anterior |
| C05 | Maturidade ilustrativa: avaliar dimensão | Respostas/evidências/pesos/lacunas reproduzíveis; cálculo marcado ilustrativo; metodologia oficial testada apenas quando fornecida |
| C06 | Criar plano, anexar execução e solicitar encerramento | Responsável correto, prazo/status, bytes/hash, encerramento por pessoa distinta; anexos não podem ser trocados silenciosamente |
| C07 | Painel e relatório gerencial | Totais reconciliados com IDs e eventos; rascunho separado de aprovado; revisão documentada |
| C08 | Negativas e auditoria | Usuário sem papel recebe recusa; login falho anônimo; leituras/exportações/downloads registram autor/IP/resultado sem segredos; pacote de acesso e de negócio verificados |
| C09 | Parâmetros e repetição | Alteração versionada e justificada; repetição não duplica casos; sinais anteriores preservam configuração/evidência |
| C10 | Texto não estruturado restrito | Apenas formatos/limites implementados; origem e trecho citável; conteúdo malicioso é tratado como dado; arquivo inválido recusado |
| C11 | Consulta e contexto obsoleto | Fontes do caso e abstenção quando insuficientes; nenhuma decisão automática; mudança relevante durante geração impede arquivar contexto como atual |
| C12 | Recuperação e integridade | Backup para caminho novo, restauração equivalente de negócio/anexos/consultas/relatórios/acessos; corrupção impede publicação; origem intacta |

C02, C09 e C10 têm jornadas locais aprovadas, incluindo desktop/celular; C10 inclui TXT, PDF digital, CSV/XLSX e OCR experimental revisado. Isso não substitui o ensaio com participantes. Executar somente funcionalidades existentes; registrar “não executado” para lacunas, nunca atribuir resultado de aceite a um roteiro.

## Baseline e métricas

Para cada tarefa elegível, documentar primeiro o processo de referência (planilha/documentos ou processo fornecido) e o resultado correto esperado; repetir no Elo com a mesma complexidade. Separar tempo humano, máquina, espera e retrabalho. Não comparar uma tarefa já conhecida com outra nova sem registrar o viés de aprendizagem.

| Métrica | Medida | Meta proposta para discussão, não resultado observado |
| --- | --- | --- |
| Esforço manual | Minutos humanos por tarefa; soma e dispersão | Menor que baseline equivalente, sem piorar completude; limiar quantitativo a definir |
| Relatório | Tempo total até versão revisada e número de correções | Redução frente à baseline; limiar a definir |
| Consolidação | Campos elegíveis reutilizados automaticamente / campos elegíveis | Aumento frente à baseline, sem associação incorreta; elegibilidade acordada |
| Rotinas substituídas | Inventário único antes/depois, com evidência de desativação/redução | Quantidade a definir; protótipo não implica rotina real substituída |
| Rastreabilidade | Registros com autor/horário/origem/histórico / registros exigidos | Todos os registros obrigatórios do ensaio rastreáveis; aprovação externa pendente |
| Painéis | Sucessos/sondas e atraso evento→painel | Limites de latência e janela a definir; medir p50/p95 e erros |
| Demandas | Tempo entrada→conclusão por tipo/prioridade, abertas separadas | Redução relativa a baseline comparável; limiar a definir |
| Planos | IDs únicos por status, atraso e responsável | Reconciliação exata entre painel e exportação, sem medir eficácia só por volume |
| Cobertura funcional | Requisitos aceitos/aplicáveis por módulo + integração | Sem requisito obrigatório omitido; validação final pelo responsável CAIXA |
| Recuperação | Tempo de restauração e estado recuperado | Nenhuma perda no snapshot verificado; RPO/RTO do piloto a pactuar |

## Execução e decisão de passagem

Executar build/testes canônicos e E2E real configurado antes do ensaio. Registrar falhas e repetir os casos afetados após correção; manter evidências anteriores. O relatório do ensaio reúne ficha, baseline, resultados, limitações, custo calculado e pendências. A passagem de fase exige decisão do responsável, não conclusão do modelo.

Interromper um caso ao detectar corrupção, vazamento de dados ou autorização indevida, preservar evidências em local restrito e registrar incidente/defeito. Não enviar automaticamente mensagens a terceiros nem executar descarte. Canais, responsáveis e SLA corporativos precisam ser acordados. Backup local não substitui continuidade multizona nem política corporativa de retenção.

## Instrumento de coleta disponível

Use o [instrumento de benefício](benefit-measurement.md) e o [CSV vazio](benefit-template.csv) para registrar pares baseline/Elo. O agregador valida comparabilidade e separa simulações de registros de participantes. Não há resultados humanos preenchidos automaticamente.
