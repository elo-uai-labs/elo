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

## Em desenvolvimento após S1

S2: catálogos de riscos/controles, dimensões e avaliação ilustrativa configurável, vínculos humanos por caso, edição de planos e encerramento sujeito a revisão distinta. Laboratório sintético independente e métricas de supervisão também estão em implementação. Não declarar esses itens aprovados antes da integração e da homologação.

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
