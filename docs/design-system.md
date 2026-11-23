# Inventário e aceite do Porsche Design System

Versão fixada: `@porsche-design-system/components-js@4.10.1`. Integração Vanilla JS + Vite conforme a documentação v4 indicada pelo usuário. O PDS é uma biblioteca de componentes Web Components e estilos; Vite compila a aplicação e Python executa a API.

| Área | Componentes oficiais utilizados |
| --- | --- |
| Identidade, navegação e acesso ao conteúdo | p-text, p-link-pure, p-tabs-bar, p-tag, p-divider |
| Títulos, descrições e indicadores | p-heading, p-text |
| Jornada, evidências, impactos e auditoria | p-text-list, p-text-list-item, p-tag |
| Ações e links de etapa | p-button, p-link, p-link-pure |
| Evolução mensal | p-table, p-table-head, p-table-head-row, p-table-head-cell, p-table-body, p-table-row, p-table-cell |
| Login local | p-input-text, p-input-password, p-button, p-inline-notification |
| Decisão, avaliações e planos | p-input-text, p-input-date, p-input-number, p-checkbox, p-select, p-select-option, p-textarea |
| Detalhamento e andamento | p-accordion com slot summary + p-heading |
| Estado de carregamento e resultado | p-spinner, p-inline-notification |

Grades e painéis são composição semântica com tokens `--p-*`, pois não são controles substitutos. As âncoras dentro de p-tabs-bar e inputs type=hidden seguem os contratos dos componentes/formulários. Não é necessário inserir componentes do catálogo que o produto não utiliza.

## Tipografia

A folha `@porsche-design-system/components-js/index.css` inclui os `@font-face` oficiais. O loader e os preloads vêm de `partials`. Nenhuma regra própria define font-family, font-size, font-weight ou line-height; propriedades do PDS selecionam as variantes. A CSP permite os arquivos de fonte do CDN oficial.

`tests/browser.cjs` compara família, escala, peso e entrelinha aos tokens; espera document.fonts.ready, confere a família e peso carregados e usa Chrome DevTools Protocol para verificar glifos de fonte web, rejeitando fallback local. Alguns arquivos oficiais retornam nome interno vazio via CDP; por isso são verificadas em conjunto a família CSS carregada e a origem web dos glifos.

Evidências: `output/validation/typography.jsonl` e capturas desktop/mobile. A verificação cobre títulos, texto corrido, indicadores e rótulos; o inventário de componentes é checado em todas as quatro telas.

Fontes oficiais: [Integração](https://designsystem.porsche.com/v4/developing/vanilla-js/getting-started/), [Font face](https://designsystem.porsche.com/v4/stylesheets/font-face/), [Componentes](https://designsystem.porsche.com/v4/components/introduction/).

## Seleção de arquivos

O catálogo `componentMeta` da versão 4.10.1 não oferece componente de arquivo/upload. A interface usa `p-button` oficial para abrir um `input type="file" hidden data-native-file-picker`, limitado ao seletor nativo da plataforma; nome, descrição, confirmação sintética e feedback usam componentes PDS. Não há controle nativo visível ou réplica CSS. O teste de controles permite somente esse seletor oculto, com os três atributos exatos, e valida abertura por teclado.

## Importação e documentos · 23/11/2026

Prévia CSV/XLSX usa p-select/p-select-option para tabela, aba e mapeamento; p-checkbox para confirmação sintética; p-button para seleção/validação/gravação; p-tag e p-text-list para erros e contagens. Leitura de documentos usa p-accordion, p-text e p-inline-notification, preservando página/célula e revisão humana. Correlação usa os mesmos componentes oficiais. Nenhuma alteração na tipografia, folha completa, partials ou internos dos componentes. Seletores de arquivo permanecem ocultos, acionados por p-button.

## Reconhecimento OCR

Ação explícita por `p-button` oficial, estado por `p-tag`/`p-inline-notification`, metadados e regiões por `p-text`/`p-text-list`, e conferência adicional por `p-checkbox`. A aceitação exige confirmação específica no servidor. As coordenadas percentuais ajudam a localizar o trecho na página/imagem original. A tipografia e as variantes oficiais permanecem inalteradas.
