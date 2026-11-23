# Medição de benefício operacional

Instrumento local pronto; nenhuma medição com participantes realizada. O relatório não decide se o piloto deve avançar. O responsável confere fontes, resultados e critérios acordados antes dessa decisão.

Copie `docs/benefit-template.csv` para um arquivo de trabalho. Para cada par registre duas linhas, `baseline` (processo de referência descrito na evidência) e `elo`. Use o mesmo participante pseudonimizado, tarefa, conjunto de dados (SHA-256) e quantidade de fatos exigidos. `order` é 1 ou 2; alterne a ordem entre participantes quando possível e registre familiaridade/treinamento na evidência. Sem equivalência de complexidade, não trate a comparação como causal.

`human_minutes` é tempo humano ativo incluindo correções, sem duplicar o retrabalho. `wait_minutes` é espera separada; tarefas paralelas não devem duplicar tempo. `corrections` conta correções e `complete_facts` conta fatos corretos e completos após revisão, entre os `required_facts`. `evidence` referencia o registro conferível do ensaio. `synthetic=true` identifica simulação; `false` é declaração do operador sobre participação real, não certificação automática. Não inclua nomes ou dados pessoais desnecessários.

```sh
.venv/bin/python3 scripts/benefit_measurement.py /caminho/registros.csv --output /caminho/relatorio-novo.json
```

O destino deve ser novo. Não há banco, rede ou chave de IA envolvida. O relatório inclui hash do CSV, pares, diferenças de tempo e completude, correções, distribuição da ordem e mediana da diferença de tempo ativo. Redução percentual usa tempo baseline como denominador; baseline zero produz `null`. Resultado negativo é preservado. Pares sem as duas fases são listados e excluídos das métricas; incompatibilidades e medidas inválidas são recusadas. Resultados sintéticos e declarados de participantes nunca são agregados juntos.

A mediana descreve somente os pares registrados; não é estimativa populacional, economia financeira ou efeito comprovado do Elo. Ganho de tempo com perda de completude exige investigação. Metas, amostra, linha de base autorizada e aceite humano seguem pendentes. Os testes incluem piora de tempo/completude, ausência de dados, baseline zero, duplicatas e pares incompatíveis.
