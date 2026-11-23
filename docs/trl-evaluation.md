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
