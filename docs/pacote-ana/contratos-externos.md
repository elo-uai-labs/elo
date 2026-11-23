# Contratos preparatórios e arquitetura do piloto

São especificações de aceite a preencher, não conectores corporativos implementados. As decisões de provedor, fonte e metodologia continuam externas. Nenhum endpoint ou credencial real é solicitado neste pacote.

## Arquitetura observada e fronteiras

Hoje: navegador com Vite/JavaScript e PDS 4.10.1 → API HTTP Python em loopback → SQLite local. O navegador carrega ativos oficiais Porsche por CDN. O backend consulta OpenAI quando IA real é escolhida; OCR rasteriza e reconhece texto localmente. Arquivos originais ficam no SQLite e apenas fontes textuais selecionadas/revisadas são enviadas à IA. Contas locais opcionais não equivalem a SSO. A restrição de execução `ELO_ENV=local|test` e a exigência opcional de contas por `ELO_REQUIRE_AUTH=1` foram acrescentadas nesta rodada; não detectam ambiente corporativo nem substituem os controles de implantação. Trilhas internas não têm âncora independente.

Desenho-alvo proposto: navegador em origem aprovada → TLS/gateway → aplicação com autenticação corporativa validada no servidor → persistência/arquivos e chaves em serviços aprovados. Eventos enviados a destino de auditoria externo independente. Fonte corporativa chega por adaptador autorizado com reconciliação. IA fica atrás de configuração de provedor e política de dados aprovada. Este desenho não escolhe nuvem, banco, região ou produto e não é configuração de implantação pronta.

## Ficha de fonte autorizada

Preencher: dono da fonte; finalidade; autorização/documento; classificação; tabelas/campos permitidos; cobertura temporal; identificadores estáveis; relações; esquema e versão; semântica de nulos; codificação; fuso; formato/transporte; lote/volume/frequência; limites; política de atualização/exclusão; retenção; conta de serviço e segregação; procedimento de incidente.

Contrato mínimo de ingestão proposto: `source_id`, `schema_version`, `batch_id`, `generated_at`, `record_count`, registros e comprovante de integridade. Esses campos pertencem ao contrato futuro, não ao JSON aceito atualmente. O importador atual usa `employees`, `suppliers`, `contracts`; valores literais, IDs únicos e referências existentes são exigidos. Não alterar silenciosamente registros existentes. Campos adicionais exigem evolução explícita do modelo.

Aceite: lote positivo/negativo, duplicata, referência inexistente, schema incompatível, alteração retroativa, dado atrasado e interrupção ensaiados. Reconciliação conta origem/recebidos/aceitos/recusados com motivos e IDs; nenhuma perda ou atualização parcial. Retentativa/idempotência e quarentena precisam de evidência. Responsáveis aprovam minimização e uso antes de qualquer ingestão real.

## Ficha de identidade e autorização

Preencher: IdP/protocolo suportado, emissores/audiências, fluxos aprovados, MFA e comprovação, grupos→papéis, escopo de acesso aos casos, admissão/movimentação/desligamento, sessões, revogação, administração, conta de emergência e serviço, revisão periódica, retenção de logs.

Não confiar em identidade/grupo informados pelo cliente sem validação servidor. Mapear papéis a `analyst`, `reviewer`, `operator`, `auditor`, `admin` somente após aprovação. Hoje todos os perfis autenticados leem os dados sintéticos do ambiente; não há promessa de isolamento por área/tenant. Aceite corporativo exige testar essa matriz aprovada, expiração/revogação, adulteração de token, grupo ausente e segregação autor/revisor. Modo demo não pode ser habilitado em produção.

## Ficha de metodologia

Preencher: proprietário, versão, vigência, texto aprovado, dimensões/perguntas, pesos, escala, tratamento de não aplicável/ausência, agregações, arredondamento, limiares, evidência obrigatória, papéis, revisão, eficácia dos controles e recomendações permitidas. Receber exemplos com resultado esperado calculado independentemente.

Aceite: reproduzir exemplos e fronteiras de limiar; recusar configurações inválidas; preservar versão antiga, reavaliação e comparação; nenhuma recalibração retroativa silenciosa. Recomendações e impactos exigem a revisão humana definida. A metodologia ilustrativa atual não pode ser renomeada como oficial.

## Ficha de infraestrutura, auditoria e IA

Preencher ambiente/região, disponibilidade, usuários/concorrência, volume/crescimento/retensão, rede/origens, TLS, banco/arquivos, gestão/rotação de chaves, política IA/dados, modelo/prompt e limites de consumo, fontes/fontes web licenciadas, responsabilidades de patch e incidente, backups, RPO/RTO e saída.

Para auditoria independente, definir destino e controlador fora das credenciais administrativas da aplicação, formato de evento, assinatura/âncora, frequência, atraso admissível, retenção, bloqueio/alerta em falha, acesso e verificador. Demonstrar alteração e remoção de histórico local detectáveis pelo destinatário independente. Apenas copiar hashes para outra tabela no mesmo banco não satisfaz o critério.

Aceite de infraestrutura: restauração de snapshot isolado, perda dentro do RPO e tempo dentro do RTO pactuados; carga com volume/concorrência/duração aprovados; p50/p95/p99/erros e saturação registrados; testes de acesso, logs sem segredos e alertas; parecer técnico/segurança. A política `store: false` da aplicação não deve ser apresentada como garantia contratual de retenção zero.

## Decisão de início

P0 sintética pode continuar localmente. Para P2/P3 reais, cada ficha precisa de responsável, evidência de autorização e aceite. Os itens ficam rastreados em `decisoes-externas.csv`. Ausência de resposta não é aprovação.
