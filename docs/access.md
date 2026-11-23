# Identidades locais opcionais

Este módulo é uma base de teste para autorização no backend com dados sintéticos e servidor em loopback. O usuário definiu provedor de identidade, fonte de dados real e hospedagem do piloto como **a definir**. Estas identidades locais não escolhem o provedor corporativo, não implementam SSO/MFA e não autorizam uso de dados reais, exposição externa ou alegação de prontidão de produção.

Sem `ELO_AUTH_USERS_FILE`, a aplicação permanece no modo local anterior, com responsáveis autodeclarados. Com essa variável, falha na leitura/validação impede ativação; não deve haver fallback silencioso para acesso sem autenticação. Não há conta, senha ou configuração padrão.

## Provisionamento explícito

Com o servidor parado, crie a pasta local se necessário e execute o provisionador. A pasta `.local/` é ignorada pelo Git. Não escreva senha em argumento de shell ou variável de ambiente.

```sh
mkdir -p .local
python3 backend/access.py provision --file .local/users.json --id analista.teste --name "Analista sintético" --roles analyst
```

O comando pede a senha duas vezes com `getpass`, exige 12–1024 caracteres, não imprime senha/hash e recusa substituir ID existente. O arquivo é gravado atomicamente com modo `0600`. Repetir o comando permite adicionar outras identidades explicitamente. IDs usam letras minúsculas, números, ponto, hífen e sublinhado. Não há contas criadas automaticamente por esta entrega.

Ative após configurar as pessoas desejadas:

```sh
ELO_AUTH_USERS_FILE="$PWD/.local/users.json" npm run dev
```

Configuração é carregada no início. Para desativar uma conta (`active: false`) ou mudar perfis, pare o servidor, edite a configuração local e reinicie. Reiniciar revoga todas as sessões existentes. Mudanças no arquivo enquanto o servidor roda não alteram as identidades já carregadas. Faça alterações administrativas de forma serial, com o servidor parado.

## Perfis e atribuição

| Perfil | Operações |
| --- | --- |
| `analyst` | Importar, detectar, gerar dossiê, decidir, vincular caso, criar plano/rascunho de relatório e anexar ao caso; executar/anexar aos planos atribuídos a seu ID |
| `reviewer` | Catálogos, avaliações, impactos, editar plano, revisar encerramento/relatório e anexar ao caso |
| `operator` | Registrar execução, anexar evidências e solicitar encerramento somente de planos atribuídos a seu ID |
| `auditor` | Leitura e consultas auditadas ao assistente, sem alteração de registros de negócio |
| `admin` | União das operações; continua sujeito a responsável atribuído e revisor distinto para impactos, encerramento e relatório |

Analistas, revisores e administradores também podem registrar cenários ilustrativos sem alterar o risco vigente. Todos os perfis podem consultar o assistente: a sessão é validada antes da geração e novamente na transação de registro; o cliente não pode enviar uma resposta pronta. Fontes alteradas durante a geração exigem nova consulta. O endpoint interno de registro não é acessível por HTTP.

Todos os perfis autenticados podem consultar os dados sintéticos deste ambiente e o diretório não secreto de pessoas (`id`, `name`, `roles`). O responsável de um novo plano ou edição deve ser um ID ativo com perfil `operator`, `analyst` ou `admin`. Registros históricos com nomes autodeclarados não são convertidos automaticamente em contas: um revisor deve atribuir um ID válido antes de o operador atualizar a execução. O servidor deve substituir o campo `actor` recebido pelo ID autenticado e nunca aceitar papéis enviados pelo cliente.

No modo autenticado, qualquer aprovação ou recusa de impacto exige um revisor diferente de quem qualificou o caso, inclusive para administradores. Essa verificação usa o caso selecionado e sua decisão persistida. Encerramento também exige pessoa diferente de quem solicitou o fechamento. Essas regras devem ser avaliadas dentro da transação de gravação, junto ao estado atual e às validações do domínio.

Relatórios só podem ser aprovados ou recusados por revisor diferente do criador do rascunho. Anexos vinculados a plano exigem o executor atribuído, correspondência do caso e plano ainda aberto/em andamento; não é permitido acrescentar arquivos durante revisão do encerramento ou após conclusão. Todos os perfis autenticados podem baixar evidências deste ambiente sintético, pois ainda não existe isolamento por organização/caso.

Eventos novos registram a origem da identidade: `local-auth` com ID autenticado fornecido pelo servidor, ou `local-demo`. Eventos históricos sem esse campo permanecem históricos; ativar login não os autentica retroativamente. A supervisão conta as duas origens separadamente e não mistura nomes autodeclarados com IDs autenticados ao aplicar sua heurística. O metadado integra o hash do evento, sem alterar a revisão do conteúdo do dossiê.

## Contrato de integração

- `AccessService.from_environment()` retorna serviço ou `None` quando desativado.
- `login(username, password)` retorna token e usuário público; `session(token)` consulta a sessão; `logout(token)` revoga.
- `authorize(user, command, state, data)` verifica permissões e, para execução/encerramento, o plano presente no estado. Exige revisão distinta até para administradores. O domínio mantém validações de versão e de encerramento na transação.
- `validate_owner(owner_id)` verifica atribuição; `people()` expõe apenas IDs, nomes e perfis ativos.
- O servidor controla cookies, identificação da sessão em todas as rotas `/api`, restrição Host/Origin e substituição de ator. Usar cookie `HttpOnly`, `SameSite=Strict`, caminho `/` e expiração compatível; HTTPS/SSO corporativo permanecem fora do ambiente local. Conferir testes de integração antes de declarar o modo operacional.

## Controles e limites

Senhas usam PBKDF2-HMAC-SHA256 com 600.000 iterações e salt aleatório de 32 bytes; comparações usam `hmac.compare_digest`. Tokens de sessão usam 32 bytes aleatórios e só seus hashes são mantidos em memória; sessões expiram em uma hora, sem renovação implícita. Há no máximo 1.024 sessões. Cinco falhas de credencial por ID em uma janela de 60 segundos bloqueiam novas tentativas até a janela liberar; registros de falha também são limitados a 1.024 e não são expulsos para permitir contornar bloqueio por inundação de IDs. Operações de sessão e tentativas concorrentes usam trava. Reinício limpa sessões e limites; portanto esse controle local não equivale a proteção distribuída contra abuso.

O arquivo de configuração é sensível mesmo contendo hashes. Não versionar, exportar com auditoria ou retornar seus campos privados pela API. Todos os usuários do ambiente têm acesso de leitura aos mesmos dados sintéticos: não há isolamento por organização nem controle granular de acesso por caso. Não há TLS no servidor local, recuperação de senha, rotação online, MFA ou integração com diretório corporativo. Esses itens precisam de definição e homologação antes do piloto real.

## Evidências e relatórios · integração S4

Backend e interface integrados, com testes HTTP e jornadas desktop/celular aprovados no checkpoint S4. Arquivos sintéticos TXT/PDF/PNG/JPEG usam limites de 1 MiB por arquivo, 20 MiB no total e 200 arquivos. Metadados e bytes são persistidos na mesma transação, com hash/contagem conferidos ao consultar ou exportar. Download é forçado como anexo, com nome gerado pelo sistema; o servidor não executa, renderiza, extrai texto ou envia esses bytes ao modelo. Verificar assinatura básica do formato não equivale a varredura antimalware.

Relatórios são compilações identificadas de dossiês já revisados e decisões humanas, sem nova chamada de IA. Afirmações preservam fontes e suas cópias de origem, modelo/prompt, limitações e sugestão originais; quando a sugestão foi rejeitada, suas afirmações e sugestão ficam excluídas e a decisão humana permanece. Rascunhos exigem revisão explícita com justificativa e versão; uma vez aprovados ou recusados, não podem ser alterados.

Pacotes de auditoria v2 incluem bytes e metadados exatos dos anexos, além de estado/eventos/manifesto. O verificador recusa omissões, duplicatas, arquivos extras, conteúdo alterado e limite excedido. Pacotes históricos v1 sem anexos continuam verificáveis. Hashes atestam consistência do pacote, não identidade de assinante nem existência de checkpoint externo confiável.

Referências primárias consultadas para as primitivas: [Python hashlib, derivação de chave](https://docs.python.org/3/library/hashlib.html#key-derivation) e [Python secrets](https://docs.python.org/3/library/secrets.html). Parâmetros, papéis e limites acima descrevem esta implementação, sem declarar certificação de segurança.
