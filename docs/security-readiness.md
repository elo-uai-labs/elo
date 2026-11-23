# Prontidão de segurança · Anexo VII

Autoavaliação técnica do protótipo local, não declaração de conformidade. Fonte: Anexo VII do conjunto documental fornecido, inclusive o texto extraído em `/tmp/ANEXOV~3.PDF.txt`. Responsáveis abaixo são funções **propostas**, não pessoas formalmente designadas. Aplicabilidade e evidências precisam de validação no ambiente escolhido. Quadros gráficos não extraídos exigem conferência no PDF original.

| Referência | Controle atual / lacuna | Responsável proposto | Evidência necessária |
| --- | --- | --- | --- |
| 1.1–1.2, 1.15–1.18 | RBAC local; processos de admissão/afastamento/revisão periódica não implantados | Gestão de acessos + CAIXA | Política, fluxos aprovados, revisão e revogação registradas |
| 1.3–1.10, 3.1–3.4 | ID local canônico e autorização backend; SSO/MFA corporativo não implementados | Identidade + segurança CAIXA | Provedor escolhido, integração e testes de identidade/revogação/MFA |
| 1.11–1.14 | Sem contas padrão; serviço sintético rotulado; aprovação de contas não pessoais e recuperação corporativa ausentes | Gestão de acessos | Inventário, dono/finalidade, aprovações e canais de provisionamento |
| 1.19–1.22, 3.5 | Separação autor/revisor local; administração infra e VPN/MFA não homologadas | Infraestrutura + segurança | Papéis administrativos separados, logs de privilégio e teste de acesso remoto |
| 1.23–1.24, 6.1–6.2 | Trilha de negócio e nova trilha HTTP independente; integração HTTP e exportação pela UI testadas localmente, com perfis autenticados; homologação corporativa pendente | Engenharia + auditoria | Cobertura de rotas/eventos, teste de negação, cadeia íntegra, exportações e ausência de segredos |
| 1.25–1.27 | Não há monitor independente do banco ou resposta privilegiada em tempo real | Segurança operacional | Ferramenta externa e alertas ensaiados; tabela no mesmo SQLite não satisfaz independência |
| 1.26, 1.28–1.30 | Ambiente local sintético; segregação produção/não produção e acesso remoto corporativo não implantados | Infraestrutura | Arquitetura, inventário de redes/ambientes e política de dispositivos |
| 2.1–2.5, 2.9–2.17, 5.1–5.8 | Hashes e credenciais derivadas locais; criptografia do banco/chaves corporativas não implementadas | Criptografia + provedor | Gestão do ciclo de chaves, proteção em repouso, titularidade CAIXA, FIPS aplicável e testes |
| 2.6–2.8, 2.18–2.22, 7.1–7.5 | Loopback HTTP; TLS/mTLS, certificados, cifras e proteção de tráfego não homologados | Infraestrutura + provedor | Configuração/testes do ambiente aprovado e certificado, sem expor localmente para simular aceite |
| 3.3, 4.1–4.11 | Não há tenant corporativo ou garantias contratuais de acesso/região/continuidade | Jurídico contratual + provedor | Contratos, isolamento, localização, permissões de acesso CAIXA/BACEN e acordos aplicáveis |
| 5.9–5.12 | Somente sintéticos no desenvolvimento; governança de confidencialidade externa não formalizada | Governança de dados | Classificação, finalidade, autorizações, termos e inventário de terceiros |
| 6.3–6.4 | Exportação local; centralização e retenção de logs do provedor não implantadas | Segurança operacional | Coleta externa, retenção prescrita/aplicável, acesso e teste de recuperação |
| 7.6–7.7 | Hospedagem real a definir; não alegar residência produtiva pela localização do laptop | Arquitetura + CAIXA | Região aprovada e localização de réplicas/backups, validação das condições aplicáveis |
| 8.1–8.3 | Backup/restauração local verificados; multizona, balanceamento e failover ausentes | SRE/infraestrutura | RPO/RTO e disponibilidade pactuados, desenho e ensaios de falhas |
| 9.1 | Sem infraestrutura de hypervisor corporativa | Provedor | Recursos/logs e compatibilidade das VMs conforme ambiente contratado |
| 10.1–10.4 | Testes e revisões de código locais; pentest externo anual/varredura de infraestrutura não contratados | Segurança + terceiro independente | Escopo aprovado, relatório independente e plano de correções |
| 10.5–10.19 | Procedimento corporativo de incidentes, 24x7/SOC e SLAs ainda não implantados | Resposta a incidentes + CAIXA | Runbook, responsáveis/canais, ensaio, preservação de evidências e lições aprendidas |
| 11.1–11.4, 13 | Nenhuma certificação SOC2/FIPS ou diligência corporativa reivindicada | Provedor + gestão contratual | Documentos válidos, periodicidade e comprovação de atendimento; conferir quadros originais |
| 12.1–12.5 | Exportação e recuperação para novo caminho; descarte certificado/migração contratual não implementados | Governança de dados + operações | Política aprovada, validação da migração, retenção transitória e evidência de sanitização/destruição |

## Passagem para piloto

Fechar primeiro lacunas implementáveis localmente: cobertura HTTP da trilha, verificação em backup, negativas de autorização, integridade, instrumentação de ensaios e documentação de falhas. Provedor de identidade, fonte e hospedagem permanecem **a definir**; isso não impede concluir testes sintéticos. A operação com dados reais exige autorização e requisitos aplicáveis aprovados.

Hashes locais não são assinatura externa, não resistem a reescrita completa por administrador e não certificam retenção. O registro da aplicação não cobre comandos diretos no banco ou acesso ao sistema operacional. Configuração de segredos não é incluída no backup de negócio. Não há processo de exclusão automática executado por este trabalho.
