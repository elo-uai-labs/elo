# Revisão geral independente · evolução paralela

Revisor: agente `/root/revisao_geral`, distinto dos autores. Base `ffe684e`; escopo exato `2a51b5fa3c07211a1dac64d6138468d8f68acecf` e correção `67d0c936a4dbaf260e9576e390beb1116e4da10d`. Código somente lido; este registro é o único arquivo escrito pelo revisor. Nenhuma chave lida, chamada real ou acesso ao banco manual.

## Achado corrigido

**P1 — teste da terceira regra herdava modo de IA real.** `tests/browser-repeated.cjs` gerava dossiê sem selecionar modo; a UI escolhe `real` quando a chave está configurada. Assim a suíte local poderia efetuar chamada paga e falhar ao exigir o texto determinístico/local. Comunicado ao orquestrador antes do passo de geração; o delta `67d0c93` seleciona explicitamente **Síntese local** antes do clique. Correção conferida no diff. O teste preserva o escopo determinístico da nova regra mesmo em máquinas com chave configurada. Resultado de execução da suíte deve ser registrado pelo orquestrador, pois estava em andamento durante esta revisão.

## Verificações

- Diff de UI: avisos, SLA e recorrência usam componentes PDS oficiais; valores de dados são escapados, links de caso usam encodeURIComponent; filtros são locais e não executam comandos de negócio.
- Metadados do pacote oficial PDS 4.10.1: varredura de propriedades enum literais em `src/main.js` sem valores inválidos, excluídos valores dinâmicos e descritores de tipos livres. `p-tag` warning/secondary e botões secondary são válidos. Não há alteração de CSS, tipografia ou shadow DOM neste diff.
- Inspecionadas capturas `operations-desktop.png` e `operations-mobile.png`: avisos, responsáveis, prazos, denominador de SLA e limites legíveis; não há recorte horizontal aparente. Capturas vistas são do teste próprio anterior à correção textual da janela; texto do código atual diz hoje e próximos sete dias. Validação de glifos/computados runtime pertence aos testes do autor/canônico; não foi novamente executada por este revisor.
- `scripts/evaluation_test.py`: **5 testes offline passaram** nesta revisão. Cobrem fonte incorreta, denominadores vazios/falhas, ficha pendente/adulterada e distância de caracteres.
- Scripts de avaliação diferenciam proxies lexicais de julgamento semântico e agente de humano. Resultados de falha não expõem mensagens do transporte. Somente fixtures sintéticas versionadas são usadas. Nenhuma avaliação real foi executada pelo revisor.
- Empacotador usa lista limitada de arquivos, recusa symlinks e padrão de segredo, preserva hashes, indica Git sujo e artefatos históricos. Não inclui banco, .env ou logs brutos. É pacote de revisão documental, não distribuição da aplicação nem auditoria criptográfica externa.
- Scripts de teste usam bancos temporários e variáveis explícitas de ambiente de teste. Nenhuma mudança observada apaga ou usa o banco manual.

## Parecer

Sem bloqueadores adicionais no escopo local/sintético após o delta `67d0c93`, condicionado à conclusão do E2E canônico em andamento. Não constitui homologação corporativa, precisão populacional, auditoria independente de infraestrutura ou licença de distribuição. Avisos não são envio em segundo plano; metodologia/SSO/fontes/custos externos permanecem documentados como pendentes.

## Delta de legibilidade · `13d5d8b3adcf5cc18923799404d30072cb84cda5`

Conferido o limite de 20 IDs por grupo de recorrência, mantendo o teto anterior de 20 grupos e informando explicitamente os IDs adicionais. O corte é somente de apresentação, preserva escaping e não modifica o endpoint ou os registros completos de auditoria. Nenhum novo componente/estilo ou variante introduzido. Documentação alinhada. Sem novo bloqueador neste delta; reconstrução e teste operacional a cargo do orquestrador, não executados novamente pelo revisor.
