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

O executável é compilado do código versionável `backend/on_device.swift` para `.local/elo-on-device`, detectado automaticamente ao iniciar. No dossiê, selecione **IA real**. A disponibilidade do modelo é verificada na geração; falhas aparecem na interface e não são substituídas silenciosamente pela síntese local.

Alternativamente, configure `OPENAI_API_KEY` e `ELO_MODEL` no ambiente ou em `.env` (ignorado pelo Git). Somente o backend usa as credenciais. A integração Apple tem preferência quando o executável local existe; para selecionar explicitamente OpenAI, execute sem esse binário. A opção **Síntese local** é determinística e identificada como tal, sem chamada a um modelo.

## Jornada disponível

1. **Visão geral:** indicadores calculados do estado persistido e navegação entre etapas.
2. **Inteligência:** executar a regra na base sintética, consultar as evidências do caso, gerar o dossiê e registrar decisão e justificativa humana.
3. **Risco e maturidade:** aprovar ou recusar separadamente os impactos propostos por uma fragilidade qualificada.
4. **Plano e auditoria:** criar plano com responsável e prazo, atualizar andamento e evidência textual, consultar eventos e verificar a integridade da trilha.

A base inicial contém o caso sintético **ELO-1042**. É possível importar novos registros fictícios, executar a detecção incremental e selecionar casos independentes. A importação acrescenta dados sem substituir registros ou decisões anteriores. O desenvolvimento completo está organizado na [matriz do Product Vision](docs/product-vision.md), com prioridade para um piloto com usuários reais e integrações autorizadas. Até definir identidade, fonte autorizada e hospedagem, a execução continua local e sintética. Nomes de responsáveis são autodeclarados.

## Testes

```sh
npx playwright install chromium
npm test
```

`npm test` executa testes Python, gera o build, inicia um servidor isolado com banco temporário, percorre a jornada no Playwright em desktop e celular e reinicia o processo para comparar a persistência. Nunca reseta o banco usado manualmente. Evidências ficam em `output/validation/`.

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

O verificador recalcula hashes, sequência, encadeamento e estado final. Isso comprova consistência interna; não substitui assinatura digital ou prova independente de autoria. O pacote contém todos os registros sintéticos, decisões, fontes, versões e planos persistidos.
