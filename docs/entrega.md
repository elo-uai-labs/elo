# OCR local · 23/11/2026

OCR experimental implementado para PNG, JPEG e PDF digitalizado, usando Tesseract 5.5.4 e rasterização PDFKit/ImageIO local. Modelos oficiais português/inglês fixados por commit e SHA-256. Página, região, escores internos, versão e original preservados; texto sem revisão não entra no assistente. Baixa confiança/ausência de texto bloqueiam aceitação. Uma leitura literal inconclusiva pode ser seguida de OCR sem apagar o histórico, com uma única fonte aceita por arquivo.

Commit `d3bdc7e`, sem publicação. **197 testes backend, build e suíte canônica com IA real passaram**. Desktop/celular cobriram oito jornadas OCR, confirmação humana adicional, download íntegro, branco inconclusivo e preservação de análise literal; pacote final verificado, 119 eventos íntegros, dez casos, estado idêntico após reinício. Rodada local também aprovada, com 117 eventos. PDS4.10.1 e glifos Porsche Next verificados; capturas inspecionadas.

Avaliação sintética: zero erros nos textos legíveis (48 caracteres PNG/JPEG/PDF, 54 com acentos); vazio/degradado abstêm. Doze extrações sequenciais tiveram p95/máximo0,406s contra meta provisória5s. Amostras pequenas não estimam precisão ou capacidade corporativa. Revisões independentes de segurança, DBA, geral e performance aprovadas no escopo local, detalhadas em [OCR: preparação, critérios e evidências](ocr.md). Banco manual não usado nos testes; serviço local reiniciado sem resetar os dados.

---

# Diagnóstico da Ana · 23/11/2026

Implementação local do diagnóstico recebido: importador assistido CSV/XLSX com prévia/mapeamento e confirmação atômica; PDF digital e planilhas com página/célula, revisão humana e inconclusivos bloqueados; correlação explicável dos sinais do mesmo contrato e transparência das capacidades na UI. PDS **4.10.1** preservado, com correção de variantes/ícones não suportados. Checkpoints locais `17be831`, `6863c41` e `427c513`; nenhum push ou publicação.

Build e 181 testes backend aprovados. E2E completo em desktop/celular, local e Apple Foundation Models real, incluindo novos importadores/documentos, exportação verificável e reinício com estado idêntico. Na rodada real: 93 eventos íntegros, dez casos; Porsche Next efetivamente renderizada. Rodada autenticada final aprovada, com cinco perfis, autoria canônica, segregação, atribuição e revogação de acesso. Revisões independentes de segurança, DBA, geral e performance registradas no [relatório da execução](diagnostico-ana-2026-11-23.md), que inclui roteiro reproduzível e limites. Evidências em `output/validation/`.

Usuário confirmou que ainda não tem custos, prazo/orçamento do piloto e modelos dos Anexos II/II-A. Esses entregáveis permanecem pendentes de dados; não foram inventados preços ou aprovações. SSO/MFA, fontes/hospedagem, ancoragem externa, metodologia oficial e OCR validado continuam dependências/backlog explícitos. O banco manual não foi usado nos testes. Servidor manual reiniciado em loopback para carregar a versão atual, com os registros preservados.

---

# Evolução do Product Vision · 22/11/2026

Pedido atual: continuar o desenvolvimento completo pelo orquestrador pessoal, com prioridade para piloto com usuários reais e integrações autorizadas. O usuário confirmou **login, primeira fonte e hospedagem a definir**. A execução permanece local e sintética; não houve publicação nem uso do banco manual nos testes.

A [matriz completa](product-vision.md) preserva P0/P1/P2 e as dependências externas. Os registros abaixo de “Entrega anterior” descrevem a migração precedente e não constituem o estado final da evolução atual.

## S1 · checkpoint local `fb98394`

Implementado e validado: importação incremental com validação atômica e limites; múltiplos casos com seleção explícita; detecção incremental sem duplicação; lote sem novos indícios como resultado válido; consulta de registros originais e regra versionada; indicadores agregados; exportação verificável do estado e da trilha. Fontes existentes não são substituídas. O estado legado é verificado antes de qualquer normalização e a migração é persistida somente dentro de uma nova transação auditada.

- Backend: 24 testes aprovados.
- Build e Playwright ampliado em Node 24: desktop/celular, recuperação de importação inválida, isolamento de três casos, persistência da seleção, resultado negativo, exportação baixada e verificada por processo Python independente, reinício com estado idêntico.
- PDS 4.10.1: componentes oficiais, estilos computados e glifos Porsche Next de webfont verificados; capturas inspecionadas.
- Revisão DBA independente: aprovada sobre hashes correspondentes ao commit `fb98394`; transações, migração, integridade, importação e isolamento.
- Revisão de segurança independente: sem bloqueadores no escopo local/sintético; nenhuma certificação para dados reais. Identidades continuam autodeclaradas.
- Revisão geral independente de frontend: corrigida restauração de botões originalmente desabilitados após erro. E2E também encontrou e corrigiu conflito entre o campo `dataset` e `HTMLFormElement.dataset`.
- Medição local pelo orquestrador, sem revisão especializada independente disponível: 2.000 contratos, 1.999 casos, 40 leituras com concorrência 4, detecção 0,062 s, p95 0,237 s, máximo 0,254 s; limite provisório 2 s. Não certifica capacidade do piloto nem carga sustentada.

Evidências regeneráveis em `output/validation/`: `result.json`, `typography.jsonl`, capturas, pacote de auditoria e `performance.json`. O checkpoint reúne também a aplicação preexistente, pois o repositório ainda não possuía commits. Branch local `codex/product-vision`, sem remoto/publicação.

## Checkpoints S2 a S5 aprovados

- **S2 · `4dfb5b5`:** catálogos versionados de riscos e controles, vínculos por caso, dimensões/perguntas/pesos ilustrativos, avaliações com evidências e lacunas; edição de planos e encerramento com revisão separada. Controle de concorrência impede decidir sobre versões antigas. Laboratório com gabarito manual independente (8 contratos, TP2/FP0/FN0/TN6 para a regra primária) e supervisão distinguindo modelo real/síntese local.
- **S3 · `7a86178`:** login local opcional, permissões no servidor, identidade canônica na auditoria e segregação entre qualificador/revisor e executor/aprovador. Sessões expiram/revogam; usuários/senhas só foram provisionados em ambientes temporários de teste. Sem configuração, o modo demonstração permanece autodeclarado. Não implementa SSO corporativo.
- **S4 · `5c8958a`:** anexos sintéticos imutáveis em BLOBs SQLite com cobertura/hash verificados; pacote de auditoria v2 completo e compatibilidade v1 sem anexos; relatórios compilados de afirmações já revisadas com fontes preservadas e aprovação por pessoa distinta. Nenhuma nova chamada ao modelo para compilar relatórios.
- **S5 · `74e512e`:** segunda regra (contato compartilhado entre fornecedores), relações navegáveis, tendências mensais, casos semelhantes e cenários ilustrativos sem alterar avaliação vigente; ingestão sintética recorrente opcional por pasta, com origem, idempotência, validação atômica e falhas explícitas. Nenhum monitor foi instalado nem fonte real conectada.

Esses checkpoints passaram pelos comandos canônicos, testes de persistência, jornadas desktop/celular e revisões independentes dos trechos relevantes. IA Apple real validada com afirmações/fonte estruturadas, inclusive para ambas as regras em S5, contrato `elo-dossier-v4`. Validação de referências não prova a sustentação semântica; análise humana continua necessária. A numeração de checkpoints não declara realizada a sprint de piloto externo.

## S6 · aprovado no escopo local

Consulta ao assistente sobre o caso selecionado: pergunta e fontes são dados, modelo sem ferramentas de decisão, citações por afirmação, abstenção explícita, histórico auditado e fontes preservadas. Modo local é busca por palavras identificada; modo real usa provedor configurado. Sessão é verificada antes da chamada e na gravação, fontes alteradas exigem nova consulta, respostas prontas enviadas pelo cliente não são aceitas. Limites: até três planos/trechos de 700 caracteres, 200 consultas no ambiente, arquivos não enviados ao modelo.

Backup e restauração locais verificam uma cópia privada, com origem somente leitura e destino novo publicado atomicamente, sem sobrescrita. Testes confirmam origem preservada, recuperação exata de anexos/relatórios/consultas, corrupção recusada e consistência com escrita concorrente. Configuração de contas e sessões não faz parte do banco. Procedimentos em [operations.md](operations.md).

Revisões independentes: backend/segurança, contratos de IA e DBA confirmaram autorização transacional, controle de versão, fontes e operação de cópia sem bloqueadores no escopo local. O orquestrador conferiu a implementação de backup e a mudança de guia Swift que permite abstenção; o binário Apple foi recompilado. Revisão de interface confirmou componentes PDS, fontes e jornadas reais em desktop/celular. Não constitui certificação de produção.

Verificação final de backend: **116 testes aprovados**. A rodada canônica também aprovou build, E2E desktop/celular e autenticação; o teste adicional posterior confirmou recuperação de relatórios e consultas. Rodada final com **Apple Foundation Models real aprovada**: dossiês das duas regras e assistente com fonte RSK-001; 40 eventos com cadeia íntegra, persistência idêntica após reinício e registros de negócio inalterados pelas consultas. PDS 4.10.1 e Porsche Next efetivamente renderizada verificados em desktop/celular. Evidências: `result-local.json`, `result-real.json`, `result-auth.json`, `typography.jsonl` e capturas, incluindo `mobile-assistant.png`.

Medição S6 em banco temporário: 2.000 contratos, 1.999 casos, 40 leituras com concorrência 4; detecção primária 0,100 s e secundária 0,129 s, leitura p95 0,463 s e máximo 0,484 s. Zero erros, trilha íntegra e snapshot inalterado pelas leituras. Escopo de domínio/SQLite, sem IA, anexos, HTTP ou renderização; limite provisório de 2 s atendido. Não mede carga sustentada nem certifica capacidade do piloto. Evidência com hashes do código em `performance-current.json`. Evidências em `output/validation/`, regeneradas por testes isolados. O banco manual não foi usado para testes. A aplicação de uso manual é reiniciada ao concluir para carregar o código atualizado, sem resetar seus registros.

## Evolução orientada ao edital · validação local aprovada

Implementados após S6: trabalhos da 2ª Linha com prioridade justificada, vínculos, responsáveis, prazos, ciclo humano e métricas de tempo corrido; parâmetros versionados das duas regras e laboratório com gabaritos independentes; extração literal TXT UTF-8 até 32 KiB, revisão CAS e uso apenas de trechos aceitos nas fontes do assistente. PDF/imagens continuam sem OCR e nenhum texto executa instruções de negócio.

A trilha HTTP independente registra consulta/login/logout/export/download/negações/alterações com autor canônico, modo, horário e IP de socket, sem segredos de requisição. Exportação separada verifica cadeia/manifesto, e backup verifica/preserva a tabela. A cadeia de negócio permanece compatível com snapshots legados. Pré-verificação impede POST com trilha já corrompida; falha de registro HTTP após commit produz503 e aviso para conferir o estado, sem alegar desfazimento do negócio.

**152 testes backend e a rodada canônica completa passaram** (`npm run build`, `npm test`, Node 24). Jornadas locais desktop/celular e perfis autenticados verificaram trabalhos, configuração/laboratório das duas regras, TXT e exportação de acesso. Ajuste visual posterior exibe o texto pendente sem recolhimento e passou pela jornada completa com **Apple Foundation Models real**: dossiês das duas regras, consulta de risco e consulta de TXT revisado citando EVD-0001, inclusive menção FOR-042 fora das fontes originais do caso. Resultado: 53 eventos de negócio íntegros, cinco casos, desktop/celular e persistência idêntica após reinício. PDS 4.10.1 e glifos Porsche Next realmente renderizados verificados. Capturas desktop/celular inspecionadas; texto literal legível, sem execução de marcação. Evidências locais: `output/validation/result-local.json`, `result-real.json`, `result-auth.json`, `typography.jsonl`, `desktop-document-review.png`, `mobile-document-review.png`. Revisão DBA independente confirmou concorrência/CAS de trabalhos e integração HTTP/documentos; segurança revisou negativas HTTP e contexto. O autor de trilha/backup não reivindica revisão independente desses módulos; o orquestrador os revisou. Delta posterior do servidor normaliza corrupção estrutural para 503 e sanitiza logs inclusive de requisições malformadas. A consulta permite menções literais somente nas fontes efetivamente citadas; identificadores inventados e referências de fontes não citadas são rejeitados. Essa validação não comprova a veracidade semântica de uma afirmação.

Sonda temporária: 100 GET concorrência 4,1 caso/20 trabalhos/22 eventos de negócio,100 eventos de acesso; zero erros, p95=0,02664s, máximo=0,20552s. Snapshot business idêntico antes/depois e cadeia válida. Medição executada pelo revisor DBA, não avaliação especializada independente de performance; amostra não certifica produção ou carga sustentada. Detalhes/hashes em [edital-execution.md](edital-execution.md).

Entregues [plano experimental](pilot-experiment.md), [modelo de custos](cost-model.csv) e [matriz de segurança](security-readiness.md). Valores comerciais permanecem A DEFINIR; fórmulas não constituem orçamento calculado. TRL 4 é autoavaliação proposta. Pendentes: homologação por usuários, premissas/cotações, responsáveis/metas do experimento e dependências corporativas abaixo. O escopo não inclui PDF/OCR, editor arbitrário de regras ou certificação de capacidade/segurança corporativa. Não houve submissão, publicação externa ou uso do banco manual em testes.

Revisão final do commit de implementação `968e91a`: hashes de domínio, servidor, consulta/modelo, documentos, trabalhos, parâmetros e laboratório conferidos pelo revisor independente contra os snapshots aprovados. Nenhum bloqueador de código; correções posteriores apenas sincronizam dois registros documentais que ainda indicavam validação pendente.

## Dependências para o piloto real

O usuário confirmou **provedor de login, primeira fonte autorizada e hospedagem a definir**. Também faltam metodologia oficial de maturidade, metas de volume/concorrência/disponibilidade e homologação no ambiente escolhido. O desenvolvimento local preserva todo o backlog; não certifica produto corporativo completo, conformidade, carga sustentada ou integração real. Não houve GitHub, publicação externa, contas reais ou envio a terceiros.

---

# Entrega anterior

# Entrega e retomada

## Escopo

Reunir o Elo funcional nesta pasta e substituir a página de exemplo pela aplicação completa do P0, usando a integração oficial Porsche Design System v4.10.1. O pedido atual é uma migração de aplicação e design system; os requisitos adicionais da Ana permanecem registrados abaixo, sem serem declarados implementados.

## Critérios e evidências

| Critério | Estado | Evidência |
| --- | --- | --- |
| Código executável local, independente da pasta antiga | Aprovado | Vite build, API/SQLite em backend/, scripts de inicialização |
| Componentes e tipografia oficiais | Aprovado | Inventário, Playwright, CDP e screenshots em output/validation/ |
| Quatro telas conectadas | Aprovado | Jornada E2E em desktop e navegação em 390px |
| Decisão humana obrigatória e impactos independentes | Aprovado | Testes de domínio e jornada com aprovação de risco/recusa de maturidade |
| Plano, evidência textual e auditoria | Aprovado | Jornada com criação, atualização e conclusão; hash válido |
| Persistência após reiniciar processo | Aprovado | Comparação integral do estado antes/depois em test-e2e.mjs |
| Segurança local da integração | Aprovado no escopo local | 5 testes HTTP, revisão independente, Host/Origin, CSP, traversal |
| IA real Apple | Aprovado nesta execução | Jornada completa E2E real aprovada com Apple Foundation Models e prompt elo-dossier-v2 |
| GitHub/PR/CI remoto | Adiado pelo usuário | Workflow preparado localmente, sem publicação |

14 testes Python passaram. Playwright com síntese local e com IA real passou, incluindo falha transitória simulada, nova tentativa explícita e persistência após reiniciar. Os testes usam bancos temporários próprios e não modificam o banco antigo nem o banco manual. A integração de desenvolvimento Vite→API foi verificada, incluindo bloqueio de origem externa e encerramento dos processos. Dependências npm auditadas sem vulnerabilidades conhecidas na execução desta entrega.

## Revisões independentes

- Frontend/PDS: conferência com componentMeta 4.10.1, tokens, props e runtime nas quatro telas. Atualizada API de accordion para slot summary. Ajustado estado das etapas para casos não qualificados.
- Segurança: sem bloqueadores no escopo local/sintético; validações de Host/Origin, caminhos de arquivos, CSP por hash e escape de texto conferidas.
- DBA: estrutura e transações de domínio preservadas da implementação anterior; migração não altera schema. Regressões de persistência e concorrência executadas.
- IA Apple: revisão incremental independente confirmou validação de referências nas duas tentativas, limite total de 45 segundos e ausência de fallback silencioso.
- Capacidade para altas cargas/produção: não certificada por esta migração.

## Backlog solicitado por Ana

Prioridade imediata para ampliar o P0 (ainda não implementado nesta entrega):

1. Importar novas bases de empregados, fornecedores e contratos; múltiplos casos; jornada sem indício.
2. Abrir os registros de origem e a regra aplicada; associação verificável de cada conclusão factual da IA a uma fonte.
3. Ampliar persistência e vínculos para múltiplos casos. A persistência do caso atual já está validada.
4. Agregar os indicadores de múltiplos casos e validar todas as transições. Indicadores do caso único estão conectados e testados.

Planejamento do MVP contratual:

5. CRUD de riscos/controles, avaliações, tratamento e revisões; questionário de maturidade, evidências e cálculo de lacunas.
6. Editar responsável/prazo, anexar arquivos de execução e aprovação humana separada para encerramento.
7. Autenticação, permissões no backend e exportação da trilha. Versões de regra/modelo/prompt já fazem parte dos registros existentes.

O P0 não valida aderência contratual completa à CAIXA. Não expor publicamente nem inserir dados reais nesta configuração.

## Estado final da execução

Aplicação iniciada nesta pasta em http://127.0.0.1:5173/ com API em 8001 e banco manual novo, pronto para uso. O banco original foi preservado. Log local em `.local/dev.log`. Resultado automatizado mais recente: `output/validation/result.json`.
