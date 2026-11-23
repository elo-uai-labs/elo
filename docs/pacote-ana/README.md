# Elo · pacote de revisão para Ana

Preparado em 23/11/2026. Material local de revisão, não submissão nem proposta comercial fechada. Público: Pedro, Michael e responsáveis pela avaliação técnica e de negócio. Fonte de escopo: diagnóstico de Ana de 23/11/2026, com 12 blocos e trilhas A/B/C. As recomendações do diagnóstico são requisitos a avaliar, não autorizações para acessar fontes, publicar ou operar com dados reais.

O primeiro resultado verificável é importar uma base fictícia, reconhecer um sinal, abrir a evidência e registrar uma decisão humana justificada. O produto conecta esse trabalho a risco, maturidade ilustrativa, plano e auditoria. O objetivo do piloto futuro é medir se esse fluxo reduz esforço e retrabalho sem piorar a qualidade da análise; esse benefício ainda não foi medido com usuários reais.

## Ler nesta ordem

1. [Matriz de atendimento](matriz-atendimento.md): cada bloco, evidência e condição de conclusão.
2. [Pitch textual](pitch.md): narrativa atualizada para apresentação; o vídeo anterior não foi regravado.
3. [Roteiro de demonstração](roteiro-demo.md): ações, resultados esperados e evidências a guardar.
4. [Kit de piloto e atendimento](piloto-onboarding.md): fases, primeiro uso, métricas e passagem de fase.
5. [Contratos e decisões externas](contratos-externos.md): especificações preparatórias para dados, identidade, metodologia e infraestrutura.
6. [Preparação comercial](candidatura.md): preenchimento posterior dos anexos e do orçamento, sem inventar preços.

Planilhas CSV preenchíveis: [insumos comerciais](insumos-comerciais.csv), [registro do ensaio](registro-ensaio.csv) e [decisões externas](decisoes-externas.csv). Campos vazios significam pendência, não zero.

## Evidência e limites

O registro técnico vigente é [docs/entrega.md](../entrega.md). A rodada OpenAI anterior a este pacote aprovou o comando real de E2E com `gpt-6.2-sol`, dez casos sintéticos, 119 eventos íntegros e persistência idêntica após reinício. As consultas reais ao risco e ao documento revisado foram submetidas no desktop; celular cobriu navegação, dossiê e apresentação de histórico. A suíte backend anterior registrou 204 testes. Esses números pertencem àquela rodada, não antecipam o aceite de alterações paralelas.

O OCR é experimental local, com avaliações sintéticas. Citações válidas e uma jornada aprovada não demonstram precisão geral da IA. SSO/MFA, ambiente corporativo, fonte autorizada, metodologia oficial e aceite da CAIXA continuam pendentes. O design system oficial Porsche 4.10.1 foi mantido por instrução do projeto; direitos de circulação institucional e dependência do CDN precisam ser resolvidos.

## Evoluções paralelas validadas localmente

A terceira tipologia experimental de perfil contratual repetido e as restrições explícitas de execução local/autenticação foram implementadas nesta rodada; o aceite integrado local foi confirmado pelo orquestrador. O laboratório da nova tipologia possui seis cenários sintéticos (2 positivos/4 negativos). A avaliação ampliada executou oito respostas reais: revisão semântica por agente independente confirmou 9/9 afirmações sustentadas, 0/9 fatos omitidos e 0/8 limitações/sugestões inseguras. OCR: 0/198 erros nos caracteres das quatro fixtures legíveis e 6/6 estados de triagem; imagem degradada omitiu 48/48 caracteres e foi inconclusiva. São amostras sintéticas pequenas, não homologação humana/corporativa. A operação de equipes passou em teste próprio desktop/celular, com cinco testes novos de domínio; a suíte backend integrada registrou 218 testes aprovados e cinco testes offline da avaliação. E2E integrado, autenticação e operações aprovados; 14 casos e 120 eventos auditáveis após reinício. Sonda real GPT-6.2-sol da terceira tipologia aprovada com fontes CTR-R1/R2 e limites explícitos. Consulte as [definições e avaliação](../avaliacao-ia-ocr.md) e a [operação de equipes](../operacao-equipes.md).

## Integridade do pacote

O gerador `python3 docs/pacote-ana/empacotar.py` reúne uma lista explícita de documentos, dados sintéticos de demo e evidências não secretas selecionadas. Gera `output/pacote-ana/elo-revisao-ana.zip`, manifesto de hashes e resumo de disponibilidade. Não inclui `.env`, SQLite, configurações de contas, logs brutos, código do provedor ou credenciais. Não realiza upload ou envio.

O manifesto registra o commit base e hashes dos arquivos incluídos, além de hashes de código/testes selecionados para vincular evidências ao estado local. Se houver alterações não commitadas, o pacote declara isso; o SHA do commit sozinho não identifica o estado entregue. Documentos relativos à raiz do projeto são copiados mantendo os caminhos, para preservar os links internos.
