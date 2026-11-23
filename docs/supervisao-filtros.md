# Supervisão: investigação das decisões vigentes

Em Plano e auditoria, use **Atualizar indicadores de supervisão** e combine origem da síntese (IA real/local/desconhecida), revisão (aceitou/ajustou/rejeitou), autor, origem da identidade, período e busca por ID/justificativa. O recorte é somente de leitura e permanece na sessão da página; sair limpa os filtros. Alterações de negócio exigem atualizar os indicadores novamente.

As datas inicial/final são inclusivas em UTC, derivadas do evento da decisão correspondente ao caso/revisão do dossiê/autor/tipo de revisão. Registros sem evento correspondente não recebem data inventada; são excluídos quando há período. Eventos sem autenticação explícita continuam legados/autodeclarados. Ativar login não muda a identidade histórica.

As contagens e taxas **do recorte** são separadas por modo e condicionadas aos filtros; filtrar aceitações naturalmente muda o denominador, portanto não representa a taxa global de concordância. Sem registros, não há taxa. Até 100 registros são exibidos; refine o recorte para consultar os demais. A busca é literal sem diferenciar maiúsculas/minúsculas; não faz análise semântica.

Os indicadores gerais e a heurística de cinco aceitações rápidas mantêm o universo original. Filtrar rejeições ou datas não remove eventos da sequência usada para a heurística e não fabrica um alerta. Alertas continuam sendo sinais para análise humana, não prova de automatismo ou avaliação de desempenho do trabalhador. Identidade local não equivale a identidade corporativa.

O backend indexa eventos em uma passagem para associar a data/proveniência sem nova consulta SQL nem alteração de schema. O endpoint já existente conserva autorização e dados anteriores; acrescenta `records` de decisões vigentes. Banco manual e trilha de negócio não são alterados pela consulta.

Validação: `node tests/supervision.cjs` após `npm run build`, usando servidor e banco temporários, três decisões sintéticas e síntese local explícita. Cobre filtros combinados, busca sem distinção de caixa, resultado vazio, intervalo inclusivo, intervalo inválido, preservação de totais e dados, teclado, desktop/celular, CSS Porsche Next e glifos web. Evidências em `output/validation/supervision-e2e.json` e capturas `supervision-desktop.png`/`supervision-mobile.png`. Quatro testes unitários em `backend/tests/test_supervision.py` cobrem denominadores, sequência da heurística, identidade e revisão/data correspondente, além de trilha inválida. Nenhuma chamada de modelo é necessária.
