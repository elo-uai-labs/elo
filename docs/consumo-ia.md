# Consumo da IA · respostas persistidas

Dossiês e consultas OpenAI preservam `usage` recebido da Responses API, junto ao modelo e aos demais metadados já auditados. O assistente inclui o consumo no evento de registro; dossiês preservam cada geração na trilha, inclusive quando uma nova geração substitui a anterior na tela. Nenhuma migração ou recomposição retroativa de eventos é feita.

Campos: `provider=openai`, `status=complete|partial|missing|invalid`, `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_tokens`, `total_tokens`. Campos ausentes são `null`, nunca zero inventado. Contagens inválidas/inconsistentes são descartadas integralmente e marcadas `invalid`. Cache é subconjunto da entrada; raciocínio é subconjunto da saída: não são somados novamente ao total. Campos desconhecidos da resposta não são persistidos.

A medição cobre **somente respostas gravadas com sucesso**. Falhas de rede, respostas recusadas, contexto alterado, autorização revogada durante a chamada ou falha de persistência podem consumir tokens sem gerar um registro. O relatório não representa consumo total da conta nem reconciliação de fatura. Eventos históricos, Apple e síntese local não ganham contagens estimadas; ausência não comprova consumo zero.

## Relatório reproduzível

Exporte o pacote de auditoria pela aplicação e execute:

```sh
.venv/bin/python3 backend/ai_usage.py /caminho/elo-auditoria.json > /caminho/consumo.json
```

O comando verifica toda a integridade do pacote antes de calcular. Não abre o banco, não lê `.env`, não chama a API e não inclui perguntas, fontes, respostas ou autores na saída. Apresenta um registro por evento, somas dos valores conhecidos e denominadores medidos/não medidos por contador. Somas não representam o total quando houver dados ausentes.

Para estimar custos, forneça `--rates /caminho/tarifas.json`. O JSON deve mapear cada nome **exato de modelo retornado** a `currency` (três letras), `input_per_million`, `cached_input_per_million` e `output_per_million`. Não há tarifas padrão. Use valores verificados, registrando a data e a origem comercial junto ao arquivo. Os preços são strings decimais finitas não negativas, e moedas diferentes nunca são somadas.

Fórmula: `((entrada − cache) × preço_entrada + cache × preço_cache + saída × preço_saída) / 1.000.000`. Só é calculada quando os três contadores necessários e uma tarifa do modelo estão presentes. Sem tarifa/contadores, custo permanece `null`; relatório apresenta quantidade sem estimativa. Estimativa não inclui tributos, descontos, outras ferramentas ou chamadas não persistidas e não substitui faturamento do provedor.

## Evidência

`backend/tests/test_ai_usage.py` valida contadores parciais/inválidos/zero, ausência de campos arbitrários, cache e raciocínio sem dupla contagem, tarifas inválidas, histórico sem medição e persistência/reabertura de dossiês e consulta com API simulada. Nenhuma chave real nem banco manual são usados.
