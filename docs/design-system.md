# Inventário e aceite do Porsche Design System

Versão fixada: `@porsche-design-system/components-js@4.10.1`. Integração Vanilla JS + Vite conforme a documentação v4 indicada pelo usuário. O PDS é uma biblioteca de componentes Web Components e estilos; Vite compila a aplicação e Python executa a API.

| Área | Componentes oficiais utilizados |
| --- | --- |
| Identidade, navegação e acesso ao conteúdo | p-text, p-link-pure, p-tabs-bar, p-tag, p-divider |
| Títulos, descrições e indicadores | p-heading, p-text |
| Jornada, evidências, impactos e auditoria | p-text-list, p-text-list-item, p-tag |
| Ações e links de etapa | p-button, p-link, p-link-pure |
| Decisão, avaliações e planos | p-input-text, p-input-date, p-input-number, p-checkbox, p-select, p-select-option, p-textarea |
| Detalhamento e andamento | p-accordion com slot summary + p-heading |
| Estado de carregamento e resultado | p-spinner, p-inline-notification |

Grades e painéis são composição semântica com tokens `--p-*`, pois não são controles substitutos. As âncoras dentro de p-tabs-bar e inputs type=hidden seguem os contratos dos componentes/formulários. Não é necessário inserir componentes do catálogo que o produto não utiliza.

## Tipografia

A folha `@porsche-design-system/components-js/index.css` inclui os `@font-face` oficiais. O loader e os preloads vêm de `partials`. Nenhuma regra própria define font-family, font-size, font-weight ou line-height; propriedades do PDS selecionam as variantes. A CSP permite os arquivos de fonte do CDN oficial.

`tests/browser.cjs` compara família, escala, peso e entrelinha aos tokens; espera document.fonts.ready, confere a família e peso carregados e usa Chrome DevTools Protocol para verificar glifos de fonte web, rejeitando fallback local. Alguns arquivos oficiais retornam nome interno vazio via CDP; por isso são verificadas em conjunto a família CSS carregada e a origem web dos glifos.

Evidências: `output/validation/typography.jsonl` e capturas desktop/mobile. A verificação cobre títulos, texto corrido, indicadores e rótulos; o inventário de componentes é checado em todas as quatro telas.

Fontes oficiais: [Integração](https://designsystem.porsche.com/v4/developing/vanilla-js/getting-started/), [Font face](https://designsystem.porsche.com/v4/stylesheets/font-face/), [Componentes](https://designsystem.porsche.com/v4/components/introduction/).
