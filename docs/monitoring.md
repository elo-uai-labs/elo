# Conector de pasta sintética e monitoramento local

Esta capacidade prepara ingestão recorrente local com rastreabilidade. Não é uma integração corporativa, não acessa rede e não escolhe fonte real, provedor de identidade ou hospedagem do piloto: esses três itens continuam **a definir**. Nenhum processo, automação, serviço ou agendamento é criado automaticamente. O conector só roda mediante comando explícito.

## Entrada e execução

Cada arquivo regular `*.json` da pasta explicitamente escolhida contém exatamente o wrapper abaixo, com o mesmo schema validado pela importação manual:

```json
{
  "synthetic": true,
  "dataset": {
    "employees": [],
    "suppliers": [],
    "contracts": []
  }
}
```

O exemplo mostra o formato; um lote real de teste precisa conter ao menos um registro sintético válido. IDs já importados não podem ser substituídos. Contratos devem apontar para empregados/fornecedores existentes ou incluídos no lote. Não use dados pessoais ou corporativos reais.

Execução única, com banco de teste separado e explicitamente escolhido:

```sh
python3 backend/monitoring.py --inbox /caminho/entrada-sintetica --db /caminho/teste-conector.sqlite3 --source-id demo-local --once
```

Monitoramento enquanto o processo estiver aberto:

```sh
python3 backend/monitoring.py --inbox /caminho/entrada-sintetica --db /caminho/teste-conector.sqlite3 --source-id demo-local --interval 30
```

Os caminhos são exemplos e precisam ser escolhidos explicitamente. Não há banco padrão, nem uso implícito de `data/elo.sqlite3`. O intervalo mínimo é 10 segundos. `Ctrl+C` encerra o processo. Isso não instala cron, launchd ou serviço persistente e não reinicia automaticamente após desligamento.

## Repetição, erros e rastreabilidade

Cada lote guarda fonte, nome do arquivo, hash SHA-256 da representação JSON canônica do wrapper, horário, IDs importados, contratos analisados e novos casos detectados. O hash é calculado pelo conector a partir dos dados, sem confiar em hash enviado no arquivo. Variação de espaços ou ordem das chaves JSON não cria um lote diferente. A combinação `source_id` + hash é idempotente: o CLI evita novas chamadas para lotes já concluídos e a transação também recusa duplicatas concorrentes.

Importação e detecção formam uma única transação auditada de serviço. Não há decisão humana ou aprovação de impacto automatizada. O ator é `Conector sintético:<source_id>` e a origem é `local-service`, distinta de usuário autenticado. O comando interno `integration/import` não deve ser exposto na lista de rotas HTTP. Lotes apenas de empregados registram zero contratos analisados. Contratos novos acionam a regra de vínculo com aprovador e a de cadastro compartilhado entre fornecedores, quando houver contratos pendentes. Fornecedores novos também podem tornar um contrato antigo relevante para a segunda regra; sua análise é invalidada e repetida sem duplicar casos existentes. O lote registra a união de contratos analisados e novos casos, além das regras/versões executadas.

Falha de referência, validação ou detecção não publica cadastro parcial nem lote bem-sucedido. Um arquivo corrigido pode ser tentado novamente. Resultados e falhas aparecem como linhas JSON de status com metadados e contagens; nomes, códigos cadastrais e conteúdo do lote não são incluídos nos logs. Duplicatas bem-sucedidas ficam silenciosas no loop. Falhas aumentam o intervalo progressivamente até cinco minutos, preservando intervalos solicitados maiores; uma passagem sem falhas retorna ao intervalo original.

## Limites e aceite

Cada arquivo é limitado a 512 KiB; só arquivos regulares são aceitos, sem links simbólicos, caminhos no nome ou caracteres de controle. A pasta admite até 100 arquivos JSON por passagem e o estado até 2.000 lotes; também valem os limites de tabelas da importação existente. O conector não move nem apaga arquivos de entrada. Arquivos já processados podem ser arquivados manualmente quando necessário para respeitar o limite da pasta.

O módulo está integrado a `Store.apply`. Onze testes passaram, incluindo execução real do CLI com `--once` em pasta/banco temporários, repetição após reinício sem novos eventos, duas submissões concorrentes com um único lote aceito, falha atômica, intervalo/backoff simulado e substituição da pasta por symlink durante leitura. O processo mantém a pasta original ancorada por descritor e abre os arquivos filhos sem seguir symlinks. Não foi executado monitoramento sobre o banco manual nem instalado um agendamento persistente. Operação prolongada e fontes corporativas continuam fora desse aceite local. Integrações corporativas futuras exigem autorização, credenciais, contrato de dados, controles de acesso e ambiente homologado; essa base local não comprova aderência a esses requisitos.
