# Operação local e recuperação

Esta rotina atende o ambiente local com dados sintéticos. Não certifica capacidade, disponibilidade, retenção legal ou operação corporativa. Identidade corporativa, fontes autorizadas e hospedagem permanecem a definir.

O operador informa os dois caminhos explicitamente. Nenhum banco padrão é aberto pelo utilitário. A pasta de destino deve existir e o arquivo de destino deve ser novo. Execute a partir da raiz do projeto, substituindo os caminhos de exemplo por caminhos locais escolhidos:

```sh
python3 backend/backup.py backup --source /caminho/base-sintetica.sqlite3 --destination /caminho/backups/elo-001.sqlite3
python3 backend/backup.py restore --source /caminho/backups/elo-001.sqlite3 --destination /caminho/recuperacao/elo-novo.sqlite3
ELO_DB=/caminho/recuperacao/elo-novo.sqlite3 python3 backend/server.py
```

A cópia usa a API de backup SQLite e uma transação de leitura, incluindo o estado completo (relatórios e consultas arquivadas), eventos e BLOBs de evidências no mesmo snapshot. O banco de origem é aberto com `mode=ro`, nunca inicializado pelo utilitário. Arquivos ausentes, vazios, links simbólicos e bancos sem estrutura Elo são recusados. Um banco Elo válido ainda sem eventos é permitido.

Antes de publicar, a cópia temporária privada (permissão 0600) passa pela verificação de integridade SQLite, cadeia de auditoria, estado e cobertura/hash dos arquivos. Migrações de compatibilidade podem ocorrer somente na cópia. A publicação usa um hardlink atômico no mesmo diretório: um destino criado por outro processo também faz a operação falhar, sem sobrescrita. Temporários são removidos após sucesso ou erro. Use diretórios controlados pelo operador; o utilitário não oferece proteção contra administradores locais que adulterem bancos e diretórios.

O backup não contém configuração de usuários/senhas, sessões em memória, variáveis de ambiente, binário do modelo ou código da aplicação. Esses elementos exigem procedimentos separados. Sessões não sobrevivem a reinícios. O hash local detecta alteração inconsistente; não constitui assinatura externa nem prova contra reescrita administrativa completa.

Para recuperação, interrompa a instância anterior e execute a restauração para um caminho novo. Inicie o servidor com `ELO_DB` apontando explicitamente para esse arquivo e confirme os casos, eventos e anexos esperados antes de continuar. Preserve o banco anterior: esta ferramenta não o substitui e não faz troca automática do servidor. Guarde cópias em armazenamento protegido e teste periodicamente a recuperação com bancos sintéticos; frequência e retenção do piloto ainda precisam ser definidas.

A validação automatizada usa somente diretórios temporários: verifica bytes e data de modificação da origem, restauração equivalente, evidências, recusa de corrupção, ausência de sobrescrita mesmo com corrida de publicação e consistência durante escrita concorrente. Nenhum backup do banco manual foi executado para esses testes.


A trilha HTTP independente `access_audit` também integra a cópia SQLite e é verificada antes da publicação. Backups históricos sem essa tabela continuam aceitos, sem inventar eventos de acesso antigos. A exportação separada dessa trilha preserva seu próprio manifesto. Se o registro HTTP falhar depois de uma alteração de negócio já confirmada no banco, a API bloqueia a resposta com503 e orienta conferir o estado antes de repetir; não promete desfazer o commit anterior.
