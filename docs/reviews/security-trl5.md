# Revisão independente de segurança · preparação TRL

Revisor: agente `trl_avaliacao`, diferente dos autores do adaptador (`trl_integracoes`), operação (`trl_operacao`) e correção de dossiê (orquestrador). **Sem bloqueador de segurança no escopo local examinado.** Não reivindico revisão independente dos meus próprios scripts/fixtures de avaliação IA/OCR nem homologação de representatividade/TRL5.

Snapshot HEAD `6edd25b8cd558082ac396be4f778eed511469275`; deltas `399a4c2` (fonte), `fc7b248` (operação) e `7ede206` (validação de menções citadas).

## Fonte sintética separada

Endpoint aceita somente HTTP em IPv4 literal127.0.0.1, porta explícita e caminho `/snapshot`; não admite credenciais na URL, query externa, fragmento, localhost/DNS ou outro destino. Proxy de ambiente é desativado e redirecionamento não é seguido. Bearer é restrito a formato/tamanho e não é persistido nos metadados de origem ou erros. Respostas remotas não são copiadas para logs de falha.

Coleta tem limites de páginas, bytes totais, tentativas e tempo; só503/transporte permitem repetição limitada. Contrato/versionamento, marcador sintético, snapshot estável, contagens, unicidade e reconciliação são conferidos. Todas as páginas são coletadas antes da gravação atômica no Store; validação de entidades/referências continua no domínio. Repetição/concorrência usam identidade de conteúdo e transação existente. Identidade de serviço é explicitamente local, não identidade corporativa. CLI rejeita o diretório manual `data/` antes de inicializar o banco.

Seis testes executados passaram em1,541s: coleta paginada, repetição após reabertura, concorrência, falhas sem gravação parcial,503/timeout limitados, destinos/redirect recusados, credencial ausente na trilha e proteção do banco manual. O serviço fornecido é apenas simulador descartável: não é endpoint público endurecido nem contrato de integração CAIXA.

## Operação autenticada e recuperação

Harness cria banco e contas em diretório temporário, senhas aleatórias não exportadas, processo em loopback e chave de IA explicitamente vazia; jornadas escolhem síntese local. Métricas guardam rota normalizada/status/tempo/papel, sem cookies/senhas/corpos. Exercita negação de leitura anônima, escrita por auditor, segregação de aprovação e autoria canônica apesar de ator forjado. Expiração usa relógio real com TTL acelerado apenas no launcher de teste; logout/restart invalidam sessões. Desativação da conta é conferida após restart, sem alegar revogação corporativa instantânea.

Backup/restauração comparam origem e destino novos, arquivos e ambas as trilhas. SIGKILL é aplicado após trabalho confirmado e quieto: não comprova durabilidade no meio de commit. Não há TLS/SSO/MFA/infraestrutura externa demonstrados. O teste automatizado de operação não substitui avaliação por usuários e não é reivindicado como executado independentemente por este revisor.

## Validador de dossiê

`7ede206` aplica aos dossiês Apple/OpenAI o contexto de fontes que a consulta já utilizava. Cada claim continua obrigado a citar somente IDs presentes em `ids`; uma menção textual a fornecedor/empregado/risco é aceita apenas se constar literalmente nas fontes **efetivamente citadas naquela afirmação**. A menção não cria entidade, fonte ou decisão. Referência a fonte nova, entidade inventada ou entidade presente somente em fonte não citada é recusada. Não há novo acesso a rede, dados, permissões ou ferramentas do modelo.

14testes de dossiê/consulta executados passaram em0,046s, incluindo aceitação literal e rejeições de menções não citadas/inventadas/novos sourceIDs em ambos os provedores. Respostas simuladas, sem chamadas pagas nesta revisão. Integridade referencial não demonstra sustentação semântica; a revisão humana continua necessária. A causa exata da falha da primeira rodada de avaliação não foi preservada e não é atribuída retrospectivamente por este parecer.

## Evidência e limites

`output/validation/security-trl5.json` identifica commits, contagens e hashes. Revisão defensiva local, sem pentest externo, certificação, dados reais ou aprovação corporativa. Segurança de infraestrutura/identidade/fonte produtiva continua dependente do ambiente-alvo.

## SHA-256 dos arquivos examinados

- `backend/synthetic_source.py`: `3c24fac96c80cd403efec59dc727bbdb4c1c75e5b46860e1e3a66df6e3b768e8`.
- `scripts/trl-source-server.py`: `430d1e17eb7633a00eb42585b4308c35c50856a965d10992deb8c2173da6a2a8`.
- `scripts/trl-source-acceptance.py`: `d937d546675392e4ee61b82d9c04fe438d2cbfd0f9d24a901440d02f3414904e`.
- `scripts/trl-operation.py`: `1257c0679efef0bc0d7535ff4b64c7ea6a9e53ba82019fe58fc25856e0443e95`.
- `scripts/trl-operation-server.py`: `3edf0c33f1eceb4d6f3826733fa10bd8578f6d02aaf0300d0896c21827e10187`.
- `backend/dossier.py`: `fb22cb6841ab44db0fd898592912875c20af1a30a25696864928d05f330efc59`.
- `backend/tests/test_dossier_cited_mentions.py`: `52ccfbd9cb713cec7afc86d8c59f36b2f62219876ba2f5efd7a1c0cd79cda8c6`.
