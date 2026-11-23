# Protocolo OCR de autoria independente

Corpus criado por `/root/ocr_independente`, separado do implementador da correção de triagem. Não houve execução do OCR para selecionar texto, fonte, tamanho ou expectativas. O agente recebeu o contexto histórico do projeto, portanto a independência é de autoria/execução, não cegamento absoluto nem avaliação humana. Os documentos são inteiramente sintéticos, gerados por AppKit; não representam digitalizações reais ou a população CAIXA.

Congelar os 12 arquivos e `ocr.json` em commit **antes** de qualquer execução do corpus. Nove documentos legíveis possuem conteúdos distintos; outros três são uma folha vazia, texto renderizado em tamanho deliberadamente ilegível e um PDF com primeira página legível e segunda vazia. As três últimas condições devem ser inconclusivas. Distribuição: sete PNG, dois JPEG e três PDF. Fontes: Helvetica, Menlo e Times New Roman. JPEG com qualidade 0,6. Todos abaixo de 1 MiB; nenhuma entrada usa dados de usuário.

Critérios prévios, sem flexibilização após resultado: zero falhas do extrator; CER agregado dos nove legíveis ≤ 5%; triagem correta em 12/12; zero caracteres na folha vazia. CER normaliza Unicode e espaços conforme o avaliador existente; não comprova preservação de layout, tabelas ou significado. Falhas em legíveis contam todo o texto esperado como erro. Os três inconclusivos não entram no denominador de CER dos legíveis. A página vazia do PDF parcial exige sinalização de cobertura, mesmo que o texto da primeira página esteja correto.

Executar somente após congelar a correção, em pasta nova:

```sh
.venv/bin/python3 scripts/independent-ocr-evaluation.py --output output/validation/independent-ocr-first
```

O runner reutiliza o cálculo do ensaio anterior, verifica hashes de cada arquivo e registra hash do código/commit e resultados por caso. Não utiliza banco, rede ou API. Se falhar, preservar a primeira execução; a amostra passa a ser regressão exposta e não pode ser reapresentada como nova amostra cega após ajuste. A aceitação de texto pelo produto permanece revisão humana obrigatória; triagem positiva não decide impactos.

Performance pré-registrada: manter o orçamento global do extrator de 30 s por arquivo, sem aumentá-lo para o corpus. Registrar duração de cada um dos 12 arquivos, número de páginas retornadas, p50 (mediana), p95 por nearest-rank e máximo das durações totais. Não haverá aquecimento por OCR nem descarte da primeira chamada. Tempo inclui inicialização local; a amostra não mede concorrência/capacidade corporativa. Um timeout ou outra falha conta como falha de qualidade, ainda que o tempo seja limitado. Não se altera limiar para obter aprovação.
