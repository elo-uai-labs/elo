# Restrições explícitas de execução

`ELO_ENV` aceita somente `local` (padrão) ou `test`. Valores como `production` ou `staging` interrompem a inicialização antes de criar o banco no CLI. O servidor permanece em loopback; esta configuração não é um mecanismo para implantar o Elo corporativamente.

`ELO_REQUIRE_AUTH=1` exige contas locais válidas em `ELO_AUTH_USERS_FILE`. Sem contas, o servidor recusa iniciar; `0` mantém a demo autodeclarada existente. O teste autentica os mesmos perfis locais; não há SSO/MFA implementado nem aprovação institucional.

Essas verificações evitam iniciar por engano em um modo declarado incompatível ou ignorar a exigência de login. Não detectam automaticamente onde o processo foi hospedado nem impedem que um administrador altere o código ou a configuração. Controles de implantação, identidade e rede precisam ser aprovados externamente.

Teste em banco temporário: rejeição de produção não cria arquivo de banco; autenticação obrigatória sem contas e configurações inválidas falham. Os segredos continuam fora do pacote e do Git. A chave da OpenAI do Elo tem validade própria e deve ser renovada pelo responsável antes de expirar.
