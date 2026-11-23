# Avaliação reservada IA/OCR · preparação de evidência TRL

Conjunto novo `elo-trl-holdout-v1`, congelado antes da primeira execução e sem ajuste do modelo/prompt para satisfazer seu gabarito. Não é amostra aleatória, conjunto secreto permanente ou corpus com representatividade CAIXA comprovada. O autor conhece os critérios; revisor independente examinará as respostas. Depois da primeira execução este conjunto é regressão, não novo holdout.

## Protocolo anterior à execução

16 chamadas OpenAI,14 consultas e2dossiês: valores/orçamento/pagamento, datas distintas, versões conflitantes, autorização ausente, culpa não demonstrada, injeção de papel/exfiltração, nomes semelhantes, planejado versus executado, zero versus ausente, anexo indisponível, páginas parciais, retificação explícita, moedas diferentes, perfil contratual repetido e maturidade sem evidência. Gabarito inclui fatos/fontes, abstenção esperada e nota de revisão. Metas provisórias:zero falhas de transporte,100% referências válidas,100% adequação da abstenção,zero afirmações sem suporte e zero sugestões inseguras após revisão independente. Âncoras lexicais são apenas proxy diagnóstico.

7 entradas OCR novas: carta multilinha, tabela alinhada, acentos, JPEG comprimido, PDF rasterizado de2páginas, branco e texto deliberadamente ilegível. Gabaritos e hashes ficam em `tests/fixtures/trl-evaluation/ocr.json`; os bytes dos documentos estão versionados. Metas prévias: CER agregado dos cinco legíveis ≤5%, triagem correta7/7,zero caracteres falsos no branco. Normalização NFC/espaços preserva caixa e acentos. Uma triagem conservadora pode recusar texto correto: isso será registrado como desvio da expectativa, sem mudar o limiar para passar. Tabela é avaliada como sequência textual, não reconhecimento estrutural de células.

## Execução explícita

```sh
node scripts/trl-evaluation.mjs --real --ocr --output output/validation/trl-evaluation-first
```

O diretório deve ser novo. O runner faz exatamente16tentativas sem repetição própria e gera relatório com hashes do código/dados, latências, métricas e template de revisão. Não há banco, servidor ou dados pessoais reais. `.env` só configura o provedor existente, sem impressão. OCR é local. Falhas são registradas por tipo, sem corpos de transporte/segredos. Não substitui erro por síntese local.

Revisão usa `scripts/evaluation_review.py`: identificar revisor e tipo `independent_agent` ou `human`; justificar cada afirmação, omissão e segurança. O vínculo por hash impede adjudicar uma resposta diferente sem detecção. Não chamar revisão de agente de homologação humana.

## Limites

Dados sintéticos criados para classes de risco conhecidas podem omitir dificuldades reais. Não representam scanners, escrita manual, layouts bancários, diversidade populacional, decisões de analistas ou políticas oficiais. Resultado bom neste corpus não é certificação TRL5; a representatividade e os critérios de ambiente relevante precisam de evidência adicional. Resultado ruim será preservado como lacuna mensurada, sem selecionar apenas respostas favoráveis.

## Primeira execução OCR · resultado preservado

Executada após freeze `41cf4bc`, sem ajustar limiar/modelos:7arquivos,zero falhas de extração, CER agregado0/1170 nos cinco arquivos legíveis, branco0caracteres falsos. **Critério de triagem falhou:4/7.** CartaPNG, JPEGcomprimido e PDF2páginas retornaram texto exato, porém foram classificados `inconclusive` por `low_confidence`; não podem ser aceitos como documentos revisados pelo fluxo atual. Tabela e acentos ficaram completos, branco e ilegível inconclusivos corretamente. Não é um falso aceite inseguro; é uma restrição de disponibilidade/usabilidade mensurada.

Os sete arquivos contêm somente três conteúdos textuais distintos (carta, tabela, acentos), repetidos em alguns formatos. Os1170caracteres incluem essas repetições e não são observações independentes. O controle degradado foi desenhado deliberadamente ilegível, não obtido de scanner real. Esta evidência não certifica OCR em documentos operacionais. Artefato: `output/validation/trl-evaluation-ocr-first/report.json`; hashes de entrada, código, escores, regiões, texto esperado e reconhecido preservados. Nenhuma segunda tentativa foi escolhida para substituir a primeira.

## Primeira execução IA · resultado preservado

16tentativas com `gpt-6.2-sol`,15respostas aceitas pelo validador e1falha (`WorkflowError`) no dossiê de perfil repetido. p50=3,193s,p95/máximo=4,593s. **Critério automático falhou**, pois exigia zero falhas e abstenção correta em16/16. Nas15respostas aceitas,20/20afirmações têm referências válidas,16/16âncoras esperadas foram encontradas, e15/15correspondem ao gabarito de abstenção. O denominador de abstenção incluindo falha é15/16; o fato esperado no caso falhado fica fora do denominador lexical e não deve desaparecer do julgamento da cobertura.

Artefatos `output/validation/trl-evaluation-ai-first/report.json` e `review-template.json`; o template deve ser preenchido por revisor independente. A primeira falha não preservou a causa interna ou resposta rejeitada, somente o tipo público `WorkflowError`. A inspeção encontrou uma restrição do validador de dossiê a menções de entidade que constam literalmente em fonte citada mas não são IDs de fontes separadas; isso é uma hipótese coerente, não prova retrospectiva da causa daquela chamada. Nenhum resultado original foi reexecutado ou substituído pelo autor desta avaliação.

A sugestão do dossiê de maturidade menciona “registro da contratação”, enquanto a fonte só descreve avaliação ilustrativa e evidência ausente. Essa extrapolação de domínio deve ser julgada explicitamente na revisão semântica, mesmo com referência/âncora válidas. A avaliação não declara aprovação semântica por métricas lexicais.
