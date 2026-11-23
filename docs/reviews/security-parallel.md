# Revisão independente de segurança · evolução paralela

Revisor: agente `/root/avaliacao_ia`, distinto dos autores das mudanças de domínio, runtime, operação e UI abaixo. Base `ffe684e`; implementação revisada `9e4d31834ad6013ef096b2512c4446ab1e511e45`; delta final conferido `d68f8f6fb52a714093a7b74dbfe6cc3fac32afe4`.

**Resultado: aprovado no escopo local/sintético, sem achados bloqueadores introduzidos pelo diff revisado.** Não é teste de invasão nem certificação para implantação corporativa.

## Escopo e evidências

- Provedor OpenAI: seleção explícita não cai em Apple ou síntese determinística quando faltam credenciais ou há erro; endpoint HTTPS fixo, chave só em cabeçalho, resposta incompleta rejeitada e mensagens públicas sem segredo. A seleção `auto` conserva a compatibilidade legada. A revisão não leu `.env`, não acessou chave nem fez chamadas reais.
- Runtime: `ELO_ENV` aceita apenas local/test; valor production/staging é recusado antes de criar SQLite. `ELO_REQUIRE_AUTH=1` recusa ausência do serviço de autenticação; a construção do serviço valida arquivo/configuração antes do bind. O endereço de escuta permanece loopback. Essa guarda evita configuração indevida; um operador que altera variáveis ou código não é uma fronteira de confiança protegida.
- Operação: avisos, SLA e recorrência são cálculos somente leitura sobre snapshot cuja auditoria deve ser válida. A rota já existente `/api/work/summary` passa pelo controle comum de sessão/leitura. Não há envio externo, alteração de papéis ou nova rota de escrita. Filtros do navegador não mudam permissões no servidor.
- UI: títulos, responsáveis, IDs, definição e consulta de filtro são escapados para texto/atributo pelo helper existente. IDs em links usam `encodeURIComponent`, e os menus escapam valores e rótulos. Contagens interpoladas vêm de cálculos inteiros controlados; nomes de categorias vêm de enum interno. Não identifiquei novo caminho de HTML arbitrário ou execução de conteúdo importado.
- Tipologia: entradas continuam pelo validador de esquema/limites, IDs e referências; o agrupamento usa identificadores exatos e título normalizado, preserva originais e indica caráter experimental. Não usa `eval`, consulta SQL dinâmica ou efeitos externos. Importação/incremental não muda autorização ou aprovação humana.
- Delta `d68f8f6`: `SIG-REP` é incluído no reconhecimento de identificadores do assistente. Isso faz referências inventadas à nova família passarem pela mesma verificação contra fontes citadas; o teste positivo/negativo cobre o caso.

## Verificação executada

32 testes distintos passaram: runtime (3), provedor com transporte mockado (7), tipologia incluindo delta final (6), operações (5), autenticação HTTP (11). A tipologia foi repetida após o delta. Os testes HTTP utilizaram bancos/contas temporários; nenhum teste usou o banco manual. Revisados os negativos de configuração/provedor, falta de chave, fonte inválida, resposta incompleta, erro de rede, trilha corrompida, acesso sem sessão, papéis e segregação. Log HTTP temporário em `/tmp/elo-security-review-auth.log`.

Não foi executado teste dinâmico XSS novo nesta revisão; a conclusão de escaping foi por leitura do diff e dos helpers. Playwright/capturas/fontes são responsabilidade da validação funcional coordenada pelo orquestrador. Capacidade, retenção externa, SSO/MFA e hospedagem real permanecem fora deste aceite.

## Independência

Não reivindico revisão independente de `scripts/evaluation*`, fixtures de avaliação ou `docs/avaliacao-ia-ocr.md`, que implementei. Tampouco ampliei este parecer para o empacotador comercial, que não integra o escopo solicitado. Nenhuma alteração de código foi feita durante a revisão.
