# Revisão geral independente · fechamento local

Revisor: agente `geral_closure`, não autor dos módulos examinados. Base `31d9b00`; commit funcional revisado `692bd54ed5bf2c4a02d0f148b00045953f391092` (inclui supervisão `8beeeb1`, consumo `f9a573c`, integração `49690c3` e correção do instrumento `692bd54`). Modo de revisão: leitura de código/contratos, testes focados isolados e inspeção visual das evidências existentes. Nenhum banco manual, segredo, publicação ou chamada de API usado pelo revisor.

## Resultado

**Aprovado no escopo funcional local examinado, sem achado bloqueador pendente.** Não antecipa o resultado da carga sustentada, da suíte canônica final ou da jornada OpenAI real. Capacidade tem revisão especializada própria; os harnesses de capacidade ainda não estavam commitados neste snapshot. A documentação de fechamento ainda estava em execução e deve refletir os resultados finais, sem declarar aprovação de capacidade se a meta falhar.

- Supervisão: filtros operam somente sobre as decisões vigentes; período inclusivo em UTC, registros sem data excluídos quando há período. Origem real/local e identidade autenticada/legada permanecem separadas. Denominadores do recorte são explicitamente condicionados aos filtros; totais gerais e sequência da heurística não são filtrados. Associação com eventos usa índice, sem consulta SQL adicional ou alteração do histórico. Texto variável é escapado. Não há nova autorização de mutação ou ferramenta de decisão.
- Interface/PDS: apenas componentes oficiais existentes (p-select, p-input-date/text, p-button, p-text, p-heading, p-text-list), sem novo CSS de componentes, substituição de fontes ou shadow DOM. Capturas `supervision-desktop.png` e `supervision-mobile.png` inspecionadas: controles legíveis, composição responsiva e ausência de corte horizontal. O resultado do E2E do autor registra teclado, Porsche Next computada e glifos web em ambos os tamanhos; o revisor inspecionou esse artefato e o teste, mas não reivindica nova execução de Playwright.
- Consumo: campos desconhecidos removidos; valores ausentes/inválidos não viram zero. Cache e raciocínio são subconjuntos, sem dupla soma. Tarifa explícita por modelo/moeda; ausência de tarifa não produz custo inventado. Relatório verifica pacote e contabiliza eventos, preservando gerações substituídas. Limites de respostas não persistidas/faturamento estão claros.
- Benefício: somente pares equivalentes agregados; pares incompletos identificados, piora preservada, baseline zero sem percentual e sintético separado de participação declarada. Nenhuma melhoria humana é inventada. Destino exclusivo impede sobrescrita.
- Integração: script canônico inclui supervisão após build; aceite real OpenAI exige metadados e tokens quando solicitado explicitamente por ambiente. Bancos de teste são temporários; testes de supervisão selecionam síntese local.

## Achado corrigido

O instrumento inicialmente calculava SHA-256 de uma leitura do CSV e fazia o cálculo usando uma segunda leitura. Uma edição concorrente poderia dissociar hash e conteúdo agregado. Informado ao autor e corrigido em `692bd54`: `io.StringIO` interpreta exatamente os bytes já usados pelo hash. Delta conferido. Sem mudança dos critérios ou resultados.

## Verificação executada pelo revisor

`PYTHONPATH=backend .venv/bin/python3 -m unittest backend.tests.test_ai_usage backend.tests.test_supervision backend.tests.test_benefit_measurement -v`: **11 testes passaram** em 0,024 s. Cobrem persistência/export/reabertura, subconjuntos de tokens, tarifas, ausência/invalidade, denominadores, heurística, identidade/data/revisão e pares inválidos/incompletos/negativos. A alteração posterior de leitura única foi conferida estaticamente; o autor reexecutou os três testes de benefício com sucesso.

## Hashes do snapshot

| Arquivo | SHA-256 |
| --- | --- |
| backend/supervision.py | d710da89a1672fb81f8f94758c09e99ac2bf3adeb100a6d4450bcb9f5c074f7d |
| backend/ai_usage.py | 2f92d818f16dc11f36fb9ea27763e4f502db9cc5b889d1a95332780e2f7d4aa0 |
| backend/dossier.py | 1cee216a878f32ce8e0159dd5f9741734992c0550356660c742249919bd95ecf |
| backend/consultation.py | c28cde0defc1a33fcd3924ccd942f512861b1075ea251f2f8d9d20c1aea00e4c |
| scripts/benefit_measurement.py | ea7f9b142adfeda2099018b92307de7820b2bfe206fdde78baffe5bd4d9c9b0f |
| scripts/test-e2e.mjs | 75765053d935c98be52ba4c9735864f49bcaf73fd00df5555906b3d2b4d97aed |
| src/main.js | f50dbb4d79f99744342264f3d0bf6f0715bcb1d6862a3c8e1b3b796c8a262c4f |
| tests/supervision.cjs | aef7e96bdaebe24b8c2216a9ca0d639e471cf260b0e1dfdef4c7b086a715d0ce |
| package.json | fc1b3cb00aec81480a01b68ec56787f3f70aa0ed4903c9a9468d1dcfaf16af1b |
