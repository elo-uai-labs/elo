# Elo · Radar de Integridade

Aplicação executável com frontend Vite, componentes oficiais **Porsche Design System 4.10.1**, API Python e persistência SQLite. A interface usa a fonte Porsche Next carregada pela folha oficial, sem substituições de tipografia em CSS.

## Iniciar o projeto

Requisitos: Node.js 24 (`.nvmrc`), Python 3.11+ e acesso ao CDN oficial `cdn.ui.porsche.com` para componentes, fontes e ícones.

```sh
nvm use
npm ci
npm run dev
```

Abra **http://127.0.0.1:5173/**. O comando inicia juntos frontend e API (porta 8001). `Ctrl+C` encerra ambos. Os dados ficam em `data/elo.sqlite3` e permanecem após reiniciar. Se uma porta estiver ocupada, o comando informa o conflito; use `ELO_WEB_PORT` e `ELO_API_PORT` para escolher outras. A execução não depende da pasta antiga do Elo nem de um vídeo.

Para executar o build compilado:

```sh
npm run build
npm start
```

Abra **http://127.0.0.1:8001/**. `npm start` serve o build e a API na mesma origem. Encerre `npm run dev` antes ou selecione outra porta para a API.

## IA real

No Mac com Apple Intelligence disponível e SDK Foundation Models:

```sh
npm run setup:ai
npm run dev
```

O executável é compilado do código versionável `backend/on_device.swift` para `.local/elo-on-device`, detectado automaticamente ao iniciar. Ao atualizar uma instalação anterior, execute novamente `npm run setup:ai`: o contrato `elo-dossier-v4` usa afirmações com fontes individuais, limitações e sugestão separadas. No dossiê, selecione **IA real**. A disponibilidade do modelo é verificada na geração; falhas aparecem na interface e não são substituídas silenciosamente pela síntese local.

Para OpenAI, use no `.env` local (ignorado pelo Git):

```dotenv
ELO_AI_PROVIDER=openai
OPENAI_API_KEY=
ELO_MODEL=gpt-6.2-sol
```

Preencha a chave do projeto Elo e reinicie `npm run dev` (ou `npm start`). Somente o backend usa a chave; não a coloque no frontend nem em mensagens. Variáveis já definidas no ambiente têm precedência sobre `.env`. O modelo inicial é configurável e oferece Responses API e respostas estruturadas conforme a [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-6.2-sol); acesso e qualidade serão validados após inserir a chave.

`ELO_AI_PROVIDER=openai` seleciona OpenAI mesmo com o binário Apple instalado. `apple` seleciona exclusivamente Apple; `auto` (padrão quando omitido) preserva a detecção antiga, com prioridade Apple. Configuração ausente ou falha não troca de provedor nem gera síntese local silenciosamente. A opção **Síntese local** continua determinística e disponível sem chave. A indicação de configuração não comprova conexão ou saldo na API.

As chamadas enviam as fontes textuais do caso selecionado e, no assistente, a pergunta e trechos revisados. OCR permanece local. A API recebe `store: false`, JSON estruturado e limite de 8.192 tokens de saída (incluindo raciocínio); respostas incompletas ou referências inválidas são recusadas. Esse parâmetro não equivale a uma garantia de retenção zero. O escopo permanece sintético, com decisões humanas. Não há chamada paga na inicialização.

Depois de configurar a chave, a validação real pode ser executada explicitamente com `ELO_TEST_DOSSIER=real npm run test:e2e`; essa rodada faz chamadas à API.

## Jornada disponível

1. **Visão geral:** indicadores calculados, trabalhos da 2ª Linha com prioridade justificada, responsáveis, prazos e acompanhamento independente dos casos.
2. **Inteligência:** configurar e executar três regras sintéticas (uma experimental), medi-las no laboratório, consultar fontes/anexos, revisar textos TXT, PDF digital e planilhas, gerar dossiês, decidir e consultar o assistente.
3. **Risco e maturidade:** gerenciar riscos, controles, avaliações e lacunas; aprovar impactos separadamente e simular cenários sem alterar o risco vigente.
4. **Plano e auditoria:** atribuir planos, anexar execução, solicitar encerramento para revisão independente, revisar relatórios citados e exportar auditoria com arquivos.

A base inicial contém o caso sintético **ELO-1042**. É possível importar novos registros fictícios, executar a detecção incremental e selecionar casos independentes. A importação acrescenta dados sem substituir registros ou decisões anteriores. O desenvolvimento completo está organizado na [matriz do Product Vision](docs/product-vision.md), com prioridade para um piloto com usuários reais e integrações autorizadas. Até definir identidade, fonte autorizada e hospedagem, a execução continua local e sintética. Sem autenticação configurada, nomes são autodeclarados; o modo opcional com contas locais aplica permissões e segregação no backend. Consulte [acesso local](docs/access.md).

## Testes

```sh
npx playwright install chromium
npm test
```

`npm test` executa testes Python, gera o build, inicia um servidor isolado com banco temporário, percorre a jornada no Playwright em desktop e celular e reinicia o processo para comparar a persistência. Inclui também a jornada autenticada com contas e senhas sintéticas temporárias. Nunca reseta o banco usado manualmente. Evidências ficam em `output/validation/`.

Para repetir a jornada com modelo real configurado:

```sh
ELO_TEST_DOSSIER=real npm run test:e2e
```

O teste também verifica componentes hidratados, tipografia computada, webfont efetivamente desenhada, ausência de controles nativos substituindo componentes PDS, navegação por teclado e ausência de rolagem horizontal. Consulte o [inventário do PDS](docs/design-system.md).

## Estrutura

O [pitch de apresentação](media/pitch/README.md) inclui vídeo de três minutos, narração, roteiro e projeto HyperFrames editável, usando capturas reais com dados sintéticos.

- `src/main.js` — telas e integração com a API.
- `src/styles.css` — import oficial e composição de layout com tokens.
- `vite.config.js` — loader, preloads oficiais e proxy local.
- `backend/` — API, regras, SQLite, auditoria e provedores de IA.
- `scripts/` — inicialização, compilação Apple e teste isolado.
- `tests/` e `backend/tests/` — verificações da jornada e backend.

[Integração oficial PDS v4](https://designsystem.porsche.com/v4/developing/vanilla-js/getting-started/) · [Fonte oficial](https://designsystem.porsche.com/v4/stylesheets/font-face/). O pacote, fontes e demais ativos continuam sujeitos aos termos de seus titulares; a integração técnica não concede direitos de marca ou licença de distribuição.

## Importação e auditoria portátil

Na Central de inteligência, abra **Importar base sintética**. O JSON segue as tabelas e campos de `backend/fixture.json`: `employees`, `suppliers`, `contracts`. Use IDs novos com prefixos `EMP-`, `FOR-`, `CTR-`; contratos podem referenciar empregados e fornecedores existentes ou do próprio lote. Limites locais: 500 registros por tabela em cada lote, 2.000 por tabela no total e 512 KiB por pedido de importação. Campos desconhecidos, IDs repetidos e referências inexistentes rejeitam o lote inteiro. Confirme a origem sintética e informe o responsável. Execute a análise para processar os novos contratos; um lote sem coincidências é um resultado válido auditado.

Em Plano e auditoria, **Exportar pacote de auditoria** baixa o estado completo e a cadeia de eventos. Para conferir o arquivo fora da aplicação:

```sh
python3 backend/audit_export.py /caminho/elo-auditoria.json
```

O verificador recalcula hashes, sequência, encadeamento e estado final. Isso comprova consistência interna; não substitui assinatura digital ou prova independente de autoria. O pacote v2 contém registros, decisões, fontes, versões, planos e bytes dos anexos persistidos; o verificador também confere cobertura e hash de cada arquivo. Pacotes históricos v1 sem anexos continuam aceitos.

## Catálogos, avaliação e supervisão

Em **Risco e maturidade**, crie e edite riscos e controles; arquive registros preservando seus vínculos históricos. Configure perguntas, pesos e pontuações máximas das dimensões ilustrativas. A avaliação humana exige evidência por resposta e justificativa; registra a versão das perguntas, a pontuação ponderada e as lacunas. Alterar o questionário sinaliza a necessidade de reavaliação, preservando avaliações anteriores.

Na Inteligência, um analista pode revisar o risco e a dimensão associados antes de decidir. Alterações concorrentes de vínculos, controles ou avaliações impedem aprovar uma versão desatualizada. No plano, edite responsável e prazo com justificativa; a execução solicita encerramento e uma pessoa distinta aprova ou recusa. Sem autenticação configurada, os nomes continuam autodeclarados.

O painel de supervisão separa concordância com IA real de concordância com síntese local e apresenta os motivos de discordância. Uma heurística explícita sinaliza cinco aceitações consecutivas em menos de dez segundos cada; o alerta exige análise humana e não demonstra aprovação automática.

O laboratório sintético tem gabarito independente e versionado. Execute pela Central de inteligência ou com `npm run lab`. Resultados incluem TP/FP/FN/TN, precisão e recall com denominadores. A execução não cria casos nem altera a base do ambiente; desempenho no gabarito não estima resultados em dados reais.

## Análises, assistência e operação

A Central de inteligência apresenta relações entre registros, tendências mensais e até cinco casos decididos semelhantes, com critérios explícitos. As regras determinísticas tratam coincidência cadastral entre fornecedor/aprovador, contato compartilhado entre fornecedores distintos e, experimentalmente, perfil contratual repetido. Os sinais não comprovam irregularidade. O laboratório possui gabaritos manuais independentes para as três regras. Configurações versionadas permitem ativação e filtro do título; as duas regras de contato também aplicam comprimento mínimo do código e exclusões. Sinais anteriores preservam a configuração aplicada.

O assistente responde perguntas sobre o **caso selecionado**, registra pergunta/resposta/fontes e pode se abster. O modo local é uma busca textual determinística; IA real usa o provedor configurado e o contrato `elo-assistant-v1`. O contexto é limitado e pode ser parcial; não inclui bytes binários nem outros casos. Pode incluir até três textos de documentos aceitos por revisão humana, com trechos de até 700 caracteres e indicação de contexto parcial. Citações verificam referência, não comprovam por si só a sustentação semântica. Nenhuma resposta executa decisões ou altera riscos. Consultas são auditadas e acessíveis aos perfis autenticados deste ambiente.

Relatórios compilam afirmações de dossiês já revisados, com suas fontes preservadas e decisões humanas separadas, sem nova chamada de IA. A revisão exige pessoa distinta do autor quando o login está ativo. Evidências sintéticas TXT/CSV/XLSX/PDF/PNG/JPEG ficam imutáveis no SQLite, com limites de 1 MiB por arquivo, 20 MiB no total e 200 arquivos; TXT, PDF digital e planilhas podem passar por extração literal local com página/linha/célula e revisão humana. O texto extraído tem limite de 32 KiB. Resultados inconclusivos não podem ser aceitos. PNG/JPEG e PDFs digitalizados podem usar o OCR local opcional descrito abaixo, com revisão específica e preservação da região de origem. PDF requer o ambiente isolado descrito abaixo.

[Monitoramento sintético](docs/monitoring.md) descreve a ingestão recorrente opcional de uma pasta controlada, sem conectar fontes reais. [Operação e recuperação](docs/operations.md) descreve backup/restauração verificados para caminhos novos, sem sobrescrever a origem. Nenhum monitor, conta ou backup manual foi criado automaticamente.

A base local não conclui o piloto corporativo: faltam provedor de identidade, fonte autorizada, hospedagem, metodologia oficial e metas de capacidade/homologação. Consulte o [registro de entrega](docs/entrega.md) para evidências e limites.


## Evolução orientada ao edital

Trabalhos da 2ª Linha têm ciclo planejado → em andamento → concluído ou cancelado, controle de versão e justificativas; tempos reportados são corridos, não horas trabalhadas. A trilha HTTP separada registra acessos, login/logout, exportações, downloads, recusas e alterações, com identidade/modo e IP do socket. Não guarda senhas, tokens, corpos ou query arbitrária. Sua exportação é restrita a auditor/revisor/administrador no modo autenticado e verifica cadeia/manifesto independentes; backup também verifica essa trilha. Falha no registro HTTP após commit não desfaz uma alteração de negócio: a resposta orienta conferir o estado antes de repetir.

Os resultados históricos e a validação de cada evolução estão no registro de entrega; a implementação do diagnóstico de 23/11 tem critérios e evidências próprios. Consulte a [matriz do edital](docs/edital-execution.md), [plano experimental](docs/pilot-experiment.md), [prontidão de segurança](docs/security-readiness.md) e [modelo de custos](docs/cost-model.csv). O CSV contém fórmulas e valores **A DEFINIR**, não orçamento calculado ou proposta comercial. Não há declaração de conformidade CAIXA ou produção.

## Evolução do diagnóstico da Ana · 23/11/2026

A interface oferece importação assistida CSV/XLSX com mapeamento e prévia sem escrita; a confirmação revalida e importa atomicamente. Empregados e fornecedores devem ser importados antes dos contratos. Sinais do mesmo contrato aparecem juntos, com trabalhos vinculados e prioridade humana explicada, preservando decisões separadas. O painel de capacidades distingue funcionalidades locais, experimentos e dependências corporativas.

Para extrair PDF digital, prepare o leitor no ambiente isolado:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-documents.txt
```

A inicialização e os testes backend preferem esse Python quando presente; `PYTHON` permite seleção explícita. CSV/XLSX não exigem bibliotecas adicionais. Consulte o [roteiro reproduzível, limites e pendências](docs/diagnostico-ana-2026-11-23.md) e os [dados sintéticos da demo](docs/demo/). Homologação de OCR em documentos autorizados, identidade/infraestrutura corporativa, metodologia oficial e orçamento aprovado permanecem pendentes.

## OCR local opcional

No macOS com Swift/SDK, execute `npm run setup:ocr`. Em Plano e auditoria, anexe PNG, JPEG ou PDF sintético e escolha **Reconhecer texto**. A execução é local, separada da extração literal. Página, região, escores internos e versão ficam preservados; baixa confiança ou ausência de texto bloqueia aceitação. O revisor precisa conferir cada trecho no original. Consulte [preparação, limites e avaliação do OCR](docs/ocr.md).

## Ampliação local após o diagnóstico

A terceira [tipologia experimental de perfil contratual repetido](docs/tipologia-perfil-repetido.md) compara contratos distintos por fornecedor, aprovador e título normalizado, sem inferir duplicidade financeira. Os sinais e decisões permanecem separados. O [bloqueio explícito de ambientes não suportados e exigência opcional de login](docs/runtime-local.md) evita inicialização em produção declarada ou em demo quando autenticação foi exigida; não representa prontidão corporativa.

O [painel operacional](docs/operacao-equipes.md) oferece avisos in-app, filtros, SLA e recorrência. A [avaliação IA/OCR](docs/avaliacao-ia-ocr.md) distingue métricas automáticas de revisão semântica; `npm run test:evaluation` é offline, enquanto `npm run evaluate -- --help` descreve a execução explícita. O [pacote atualizado para a Ana](docs/pacote-ana/README.md) reúne matriz de atendimento, pitch, roteiro e insumos da candidatura.
