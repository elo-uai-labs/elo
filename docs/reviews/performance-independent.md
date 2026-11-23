# Revisão independente de performance · OCR

Revisor: `/root/revisao_ocr_performance`, separado do implementador OCR e dos revisores de segurança e geral. Escopo: custo da leitura adicional, limites de recursos e latência local; sem alteração do runtime, chamadas à API ou banco manual.

## Protocolo anterior à medição

Comparar `fb1c1af` com a correção congelada a informar. Verificar orçamento compartilhado de 30 s por arquivo, no máximo cinco páginas, 12 milhões de pixels por página, entrada de 1 MiB, texto de 32 KiB e limites de segmentos. A segunda leitura não deve renovar o orçamento nem repetir indefinidamente; sua execução deve depender de dúvida da primeira. Metadados de ambas as leituras exigem tamanho limitado.

Repetir uma vez o conjunto anterior de sete arquivos, agora regressão exposta, em pasta nova `output/validation/ocr-performance-regression`, sem substituir o ensaio inicial. Registrar tempos individuais, mediana, p95/máximo e total, confrontando com o relatório original apenas descritivamente: ambiente, cache e carga podem diferir. Comparar hashes de todas as entradas. A primeira rodada de 12 arquivos independentes será executada por outro agente e sua latência será analisada, sem aquecimento ou repetição deste revisor.

Aceite provisório: nenhum timeout/falha, todos os arquivos abaixo do orçamento de 30 s, nenhuma ampliação dos limites e custo adicional no máximo uma segunda leitura por página. Não há meta corporativa de throughput, concorrência ou p95 estabelecida; esta revisão não fornece garantia de capacidade sob carga.

## Resultado

**Aprovado no escopo local delimitado**, sem bloqueador de performance identificado. Commit revisado: `52bf46c80dd888a576a13e8cec19f95de71ea55d`; SHA256 de `backend/ocr.py`: `0508437069decfab5762999fcbe4a62a947e965414ec5611fcd6d85ff5bdaae5`.

O código executa PSM11 somente quando uma página tem escore abaixo de 0,8, uma vez por página, no máximo dez reconhecimentos Tesseract por arquivo de cinco páginas. Preserva `OMP_THREAD_LIMIT=1`. O helper de subprocesso calcula tempo restante desde o início, sem renovar os 30 s na segunda leitura. O teste `test_second_pass_timeout_uses_remaining_budget_and_discards_output` verifica orçamento20→10s e descarte/limpeza no timeout. Esta revisão inspecionou esse teste; sua execução integra a suíte canônica coordenada pelo orquestrador.

Entrada1MiB, páginas5, pixels12MP, texto32KiB, TSV300.000bytes por leitura e segmentos500 por conjunto permanecem limitados. A validação recursiva aplica os limites de texto e estrutura também à leitura secundária, sem recursão ilimitada. Os metadados adicionais são listas limitadas pelos tamanhos de texto/TSV/segmentos; não há cap separado de bytes JSON, nem medição de RSS nesta revisão. O deadline é aplicado aos subprocessos: hashing, parsing e serialização Python não são interrompidos à força exatamente aos30s. Essa limitação do orçamento já existia e não deve ser apresentada como hard deadline de parede.

### Regressão exposta medida pelo revisor

Comando: `.venv/bin/python3 scripts/trl-evaluation.py --ocr --output output/validation/ocr-performance-regression`, saída0. Sete hashes de entrada conferem com o primeiro ensaio. Triagem7/7, CER0/1170, nenhum timeout ou falha, folha vazia0caracteres. Mediana0,3952s, p95/máximo1,1529s, total3,6555s. Relatório original preservado.

| Arquivo | Histórico (s) | Correção (s) | Página corroborada |
| --- | ---: | ---: | --- |
| compressed.jpg | 0,4421 | 0,6880 | 1 |
| letter.png | 0,3550 | 0,6545 | 1 |
| two-pages.pdf | 0,7385 | 1,1529 | 2 |

A segunda leitura acrescenta trabalho; o comparativo mostra esse custo nos três casos corrigidos, mas não é A/B controlado. O degradado histórico levou6,8131s e agora0,3952s; a diferença não pode ser creditada à correção. Maior JSON de segmentos+qualidade observado:9.712bytes no PDF, sem estimar o máximo possível.

Evidências: `output/validation/ocr-performance-regression/report.json` (SHA256 `def9c2e09082eb6d11ec76044530c934fb97d485da526ab87eb6dbab7792afba`) e `performance-review.json` no mesmo diretório.

### Primeira amostra independente

Relatório `output/validation/independent-ocr-first/report.json`:12arquivos, zero falhas, mediana0,3511s, p95/máximo0,7882s, todos abaixo30s. Triagem12/12 e CER1/1299. Nenhuma página dessa amostra acionou a segunda leitura; portanto ela sustenta ausência de regressão observada nos casos novos, **não valida independentemente o ramo novo de corroboração**. Esse ramo foi exercitado pela regressão antiga e testes de fronteira. Não houve segunda execução do corpus independente por este revisor.

Medições foram sequenciais e terminadas antes da suíte canônica; não medem concorrência sustentada, documentos reais, throughput corporativo ou benefício humano. A aprovação deste parecer é de limites e latência local, não de precisão populacional.

Nota de ambiente registrada pelo orquestrador: o host não estava reservado exclusivamente ao ensaio; revisões e testes locais de segurança ocorreram durante esta etapa. Não há garantia de ausência de sobreposição de processos. A medição terminou antes de iniciar a suíte canônica, mas não é um benchmark em máquina isolada.
