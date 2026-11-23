# Complemento autenticado com OCR e OpenAI durante leituras

Protocolo definido antes da rodada real. Ensaio sintético curto, não repetição de60s de carga nem homologação de ambiente relevante. Três clientes autenticados leem `/api/state` enquanto uma jornada executa OCR local, revisão de fixture, um dossiê e uma consulta. IA real não toma decisões. O relatório separa tempos de OCR, dossiê, consulta e leituras.

## Execução explícita

```sh
node scripts/trl-real-operation.mjs --smoke
node scripts/trl-real-operation.mjs --real --allow-paid
```

O primeiro comando não carrega `.env`, esvazia a chave no processo e usa síntese local; OCR continua real e local. O segundo exige os dois flags antes de carregar `.env`, sem imprimir valores, e limita o cliente a **duas tentativas de chamadas reais**:um dossiê e uma consulta. Não há retry automático; falha não dispara mais chamadas. O Python também exige os flags/chave/modelo. Sem argumentos, encerra antes de chamar API. A execução real deve ser solicitada explicitamente, nunca adicionada ao `npm test` padrão.

`--output` escolhe somente o relatório. Banco e contas são criados em TemporaryDirectory, serviço é loopback e encerrado no final. O harness reutiliza `Exercise` com subclasse de inicialização; o comportamento original sem chamadas pagas permanece inalterado. A chave fica somente no ambiente do processo de teste/backend e é usada pelo provedor configurado; não há alteração de `.env` ou do servidor/banco manual.

## Critérios prévios e procedimento

1. Zero erros inesperados, negativas403 ao auditor registradas separadamente; até duas tentativas OpenAI e sem retry.
2. Fixture `table.png` do corpus já congelado conferida por SHA-256. OCR precisa ser completo; textos dos segmentos normalizados em NFC/espaços devem corresponder ao gabarito congelado. Marcadores de região não são caracteres do documento e não entram nessa comparação. A primeira tentativa smoke comparava também os marcadores e falhou; foi corrigido o comparador, sem alterar o corpus, engine ou limiares; registro inicial preservado.
3. Conta de revisor sintético registra aceitação após comparação automática. A justificativa explicita fixture automatizada, não revisão humana real. Auditor não pode revisar documento.
4. Dossiê usa modo real explicitamente na rodada paga. As fontes de todas as afirmações devem pertencer às evidências do caso. Consulta pergunta pelo total registrado e deve citar o documento OCR revisado com330,00; estado protegido de casos/riscos/dimensões/ações/trabalhos/relatórios deve permanecer idêntico antes/depois da consulta.
5. Ambas as respostas OpenAI devem persistir provider/usage e tokens informados. Relatório de consumo gerado a partir do pacote verificado. Fontes/claims/modelo/prompt preservados no relatório para revisão, sem chave ou cookies.
6. Após encerrar os leitores, reiniciar deve preservar snapshot de negócio. SQLite, pacote de negócio, cadeia de acesso e contagem exata de eventos por resposta API devem conferir.
7. Meta provisória somente das leituras:p95<2s. Não há meta2s para IA/OCR nem percentil inferido de uma única geração. Clientes esperam150ms entre leituras; duração corresponde à jornada observada.

## Limites

O documento é conhecido/exposto da avaliação anterior, não um novo holdout. A checagem do total e das referências é um aceite funcional limitado, não avaliação semântica populacional. A conta de revisão é operada pelo teste, não por especialista humano. Não representa distribuição de documentos, identidade corporativa, TLS, rede externa, multizona ou escala máxima. O HTTP cliente tem timeout15s e o provedor30s; erro encerra o ensaio sem retry e pode haver consumo sem resposta persistida. A chamada paga não é iniciada se a etapa de OCR falhar.

Saídas padrão: `output/validation/trl5/real-operation-smoke.json` e `real-operation.json`. A falha inicial do comparador está em `real-operation-smoke-initial.json`.

## Resultado observado · 23/11/2026

Execução do commit `96c0e59`, **aprovada no protocolo curto**. Exatamente duas tentativas OpenAI, ambas com resposta persistida `gpt-6.2-sol`; nenhum retry. A janela concorrente durou7,801s:144leituras,48por cliente,p95=.01360s,máximo=.01791s,zero erros inesperados e duas recusas403 esperadas ao auditor.

Tempos individuais:OCR=.329s,dossiê=4.334s,consulta=3.129s. Não são percentis de IA/OCR nem promessa de latência futura. A consulta respondeu que o total registrado é330,00 e citouEVD-0001, cujo texto OCR foi aceito após comparação com o gabarito congelado. Estado protegido permaneceu inalterado. Uso auditado:1333tokens de entrada+306saída=1639total,duas respostas medidas; nenhum custo monetário calculado.

Reinício preservou o snapshot;6eventos de negócio e157respostas API/157eventos de acesso, exportações verificadas eSQLiteok. `real-operation.json` contém hashes, metadados, fontes/claims sintéticos e resultados; `real-operation-smoke.json` comprova o mesmo percurso sem chamadas OpenAI. Não foram executadas chamadas reais adicionais para repetir ou melhorar a resposta.
