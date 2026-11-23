# Ensaio de operação mista autenticada

Protocolo local sintético definido antes da execução prolongada. Contribui para investigar a hipótese de ambiente relevante em `trl5/ambiente-relevante.md`; não certifica TRL5 nem representatividade da CAIXA. Sem alteração da interface, do servidor de uso manual ou do banco manual.

```sh
.venv/bin/python3 scripts/trl-operation.py
```

Saída `output/validation/trl-operation.json`. O harness provisiona cinco contas com senhas aleatórias exclusivamente em pasta temporária, inicia o servidor Elo real em processo separado ligado a127.0.0.1 e remove os arquivos/processos no final. Não lê `.env`, não imprime credenciais/cookies e força chave de modelo vazia. `--duration 1 --output output/validation/trl-operation-smoke.json` verifica o percurso, mas é explicitamente smoke, sem aceite de carga. Duração padrão60s, permitida até120s.

## Critérios prévios

- Zero erros inesperados em toda a jornada; negativas401/403 e conflitos409 esperados registrados separadamente.
- p95 das leituras HTTP durante carga abaixo de2s, meta provisória local herdada, sem alegação de SLA contratual.
- Autoria canônica, segregação e versões verificadas por respostas/estado; IA local não executa decisões.
- Estado de negócio reconhecido antes de interrupção preservado após reinício; sessões anteriores revogadas.
- Backup/restauração para destinos novos preserva estado, anexos e trilhas; origem não alterada pela cópia, exportações verificadas, SQLite íntegro.

## Jornada e carga

Antes da carga: recusa anônima; login de analista/revisor/executor/auditor/admin; negativa de escrita ao auditor; importação de30contratos sintéticos; detecção; dossiê em modo local explícito; decisão atribuída ao ator autenticado apesar de campo forjado; tentativa indevida de impacto recusada; impactos aprovados por revisor distinto; plano atribuído, anexoTXT, extração literal e revisão; repetição da revisão recusada409; encerramento separado; relatório com autoaprovação recusada e revisão independente; consulta local.

Carga60s: três clientes de leitura autenticados alternam `/api/state`, `/api/work/summary` e `/api/supervision`, com200ms entre chamadas. Um cliente de execução cria/inicia/conclui trabalhos e provoca exatamente um conflito de versão antigo por ciclo. A cada cinco ciclos também anexa/extrai/revisa um TXT e faz consulta local. A cada dez ciclos importa mais um contrato sintético novo, detecta seu sinal e gera dossiê local desse novo caso, preservando decisões anteriores. Pausa500ms após ciclo. Operações de diferentes papéis usam sessões distintas; a sequência de escrita é serializada pelo cliente para corresponder ao fluxo de trabalho, enquanto leituras competem com ela. Quantidade de chamadas/ciclos depende dos tempos; ciclo fechado, não taxa fixa nem saturação máxima.

Reconciliação final exige um evento de acesso por resposta API, contagem exata de trabalhos concluídos e plano/relatório aprovados. Relatório inclui metadados de cada requisição (rota, papel, fase, duração, status/expectativa), percentis de leitura e escrita, quantidade de negativas/conflitos, erros inesperados, estado final e hashes do código. Nenhum corpo de resposta, senha ou cookie entra no relatório.

## Recuperação e sessões

Após a carga, com os clientes encerrados e commits reconhecidos, o processo recebe SIGKILL. O reinício deve preservar o snapshot de negócio e rejeitar a sessão antiga. Isto NÃO simula corte no meio de uma transação nem perda elétrica/falha de disco. Nova autenticação permite conferir a aplicação.

Servidor parado: backup e restauração para caminhos novos são verificados, com comparação exata de estado/anexos e da trilha HTTP; hash do banco origem deve permanecer idêntico. O servidor passa a usar a cópia restaurada. O launcher de teste usa TTL real de1s para exercitar expiração; após aguardar1,1s, a sessão deve receber401. Logout revoga outra sessão. Desativação de conta no arquivo, com servidor parado, é aplicada após reinício e nega novo login. Isso corresponde à implementação local, não a revogação federada imediata. Exportações finais de negócio e acesso são verificadas.

## Limites

A base pequena e os60s ampliam a cobertura de concorrência funcional; não substituem a sondagem de2.000contratos nem sustentação em dias. Neste ensaio não entram navegador/renderização, usuários humanos, SSO/MFA, TLS, nuvem, rede externa, IA real ou OCR. Documentos são TXT e a síntese é local. IA/OCR reais têm avaliação separada e seus tempos não são atribuídos a esta carga. Backup não inclui configuração de contas/segredos. Sem metodologia oficial ou distribuição real conhecida, a representatividade de domínio permanece hipótese.
