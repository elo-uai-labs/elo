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

Alternativamente, configure `OPENAI_API_KEY` e `ELO_MODEL` no ambiente ou em `.env` (ignorado pelo Git). Somente o backend usa as credenciais. A integração Apple tem preferência quando o executável local existe; para selecionar explicitamente OpenAI, execute sem esse binário. A opção **Síntese local** é determinística e identificada como tal, sem chamada a um modelo.

## Jornada disponível

1. **Visão geral:** indicadores calculados do estado persistido e navegação entre etapas.
2. **Inteligência:** executar duas regras na base sintética, consultar fontes e anexos, gerar dossiês, registrar decisões humanas e consultar o assistente com fontes do caso.
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

A Central de inteligência apresenta relações entre registros, tendências mensais e até cinco casos decididos semelhantes, com critérios explícitos. Duas regras determinísticas tratam coincidência cadastral entre fornecedor/aprovador e contato compartilhado entre fornecedores distintos. Os sinais não comprovam irregularidade. O laboratório v1 mede somente a primeira regra; a segunda possui testes positivos e negativos próprios.

O assistente responde perguntas sobre o **caso selecionado**, registra pergunta/resposta/fontes e pode se abster. O modo local é uma busca textual determinística; IA real usa o provedor configurado e o contrato `elo-assistant-v1`. O contexto é limitado e pode ser parcial; não inclui bytes de anexos nem outros casos. Citações verificam referência, não comprovam por si só a sustentação semântica. Nenhuma resposta executa decisões ou altera riscos. Consultas são auditadas e acessíveis aos perfis autenticados deste ambiente.

Relatórios compilam afirmações de dossiês já revisados, com suas fontes preservadas e decisões humanas separadas, sem nova chamada de IA. A revisão exige pessoa distinta do autor quando o login está ativo. Evidências sintéticas TXT/PDF/PNG/JPEG ficam imutáveis no SQLite, com limites de 1 MiB por arquivo, 20 MiB no total e 200 arquivos; não são interpretadas pelo modelo.

[Monitoramento sintético](docs/monitoring.md) descreve a ingestão recorrente opcional de uma pasta controlada, sem conectar fontes reais. [Operação e recuperação](docs/operations.md) descreve backup/restauração verificados para caminhos novos, sem sobrescrever a origem. Nenhum monitor, conta ou backup manual foi criado automaticamente.

A base local não conclui o piloto corporativo: faltam provedor de identidade, fonte autorizada, hospedagem, metodologia oficial e metas de capacidade/homologação. Consulte o [registro de entrega](docs/entrega.md) para evidências e limites.
