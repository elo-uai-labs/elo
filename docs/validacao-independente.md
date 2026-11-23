# Correção OCR e validação independente · 23/11/2026

## Escopo e protocolo registrado antes das novas execuções

Base: `fb1c1af`, branch `codex/product-vision`. Pedido: corrigir a triagem excessivamente conservadora do OCR e validar IA com uma amostra independente, usando o orquestrador pessoal em paralelo. Execução local, dados sintéticos, bancos temporários, sem publicação.

Três autores separados: `ocr_correcao` implementa a correção usando somente os conjuntos anteriores; `ocr_independente` produz um conjunto novo sem ajustar o conteúdo aos erros do extrator; `ia_independente` produz casos novos sem alterar runtime/prompts. Manifestos, gabaritos e critérios são congelados em commit antes da primeira execução. O orquestrador revisa semanticamente as respostas da IA, separado do autor do conjunto e do código de geração. Essa separação é de autoria técnica; não constitui validação humana, independência institucional ou representatividade comprovada.

Critérios da correção: reproduzir e resolver os falsos inconclusivos do conjunto anterior sem aceitar texto vazio/ilegível, retirar revisão humana ou enfraquecer limites de arquivos, páginas, tempo e localização. Nova rodada anterior é regressão exposta, preservando a avaliação inicial. Critérios numéricos de cada conjunto independente constam no manifesto congelado. Falhas da primeira execução serão mantidas, sem seleção posterior de casos ou repetição até aprovação.

IA: até 20 chamadas reais explícitas ao modelo configurado, sem repetição automática, com fontes e respostas preservadas e hashes. Além de referências e abstenção, revisão de sustentação de cada afirmação, omissões e segurança de limitações/sugestões. Resultados com erro permanecem no denominador operacional, separados do denominador semântico. Aprovação completa exige nenhuma falha, afirmação não sustentada ou omissão esperada e abstenção adequada em todos os casos. Âncoras lexicais são indicadores auxiliares, nunca prova semântica.

Revisões previstas: geral, segurança (entrada documental não confiável) e performance (processamento OCR), com revisores distintos do implementador e entre as especialidades. DBA não se aplica se não houver mudança de persistência, SQL ou transações. Verificações canônicas: `npm run build`, `npm test`, além das avaliações e regressões específicas. Nenhuma alteração visual prevista; suíte existente verifica desktop/celular/PDS.

## Resultados

Correção `52bf46c`: segunda leitura de layout nas páginas de baixa confiança, dentro do mesmo orçamento. Texto principal, escores e aviso de dúvida preservados; texto só vira fonte após revisão OCR explícita. Tokens devem coincidir integralmente; leitura secundária deve atingir o limiar, com exceção provisória e estreita do hífen separador descrita em [OCR](ocr.md). Sem mudanças de SQL, schema ou interface.

| Critério | Resultado | Evidência e limite |
| --- | --- | --- |
| Três falsos inconclusivos conhecidos | Corrigidos; triagem7/7, CER0/1170 | Regressão exposta, não conjunto independente |
| Novo OCR congelado em e3a1691 | Aprovado:12/12triagens, CER1/1299 (0,077%), branco0 | Nove legíveis distintos; erro de acento em JPEG preservado |
| Segunda leitura | Testes e regressão exposta aprovados | Nenhum arquivo do novo corpus acionou essa ramificação |
| IA congelada em b399d05 | 18/18 respostas, abstenção18/18, referências32/32 | 12assistentes+6dossiês, gpt-6.2-sol,18chamadas sem retry |
| Sustentação semântica IA | 32/32 afirmações sustentadas; nenhuma sugestão insegura em18 | Revisão por agente distinto do runtime e autor do conjunto |
| Completude IA | Critério estrito não aprovado:1/28 fato omitido | Pergunta literal mais estreita que o gabarito; sem alterar retrospectivamente critérios |

[Protocolo OCR](ocr-independent-protocol.md), [avaliação IA e omissão](independent-ai-evaluation.md). OCR novo:p50=.3511s,p95/máxima=.7882s. Regressão OCR medida por outro revisor:p50=.3952s,p95/máxima=1.1529s,3arquivos com segunda leitura. IA:p50=3.4409s,p95/máxima=4.4602s,8.273tokens medidos. Tempos locais descritivos, sem estimar capacidade corporativa.

Revisões independentes: [geral](reviews/general-independent.md) (`8ad3f46`), [segurança](reviews/security-independent.md) (`201f790`), [performance](reviews/performance-independent.md) (`2f834bc`). Sem bloqueadores novos no escopo local; DBA não acionado porque não houve mudança de SQL/persistência. Teste de workflow adicional cobre metadados, revisão, exportação e backup em banco temporário.

Relatórios preservados em `output/validation/independent-ocr-first/`, `independent-ai-first/` e `ocr-performance-regression/`. Primeiras avaliações históricas e ZIP anterior mantidos, com hashes registrados em `independent-closure/prior-artifact-hashes.json`. Amostras são sintéticas e produzidas por agentes separados; contexto herdado impede alegar cegamento absoluto. Duas leituras da mesma engine também não são verificações estatisticamente independentes.

## Verificação final e pendências

`npm run build` e `npm test` aprovados: **244 testes backend +5 testes offline**, jornadas integrada, autenticada, operações e supervisão, desktop/celular/PDS4.10.1/Porsche Next. Logs em `output/validation/independent-closure/`. Servidor local reiniciado com o código corrigido; API e frontend responderam200. Banco manual não usado pelos testes. Não há mudança do prompt de IA nesta rodada, nem chamada paga no teste padrão. A rodada de IA avaliou o gerador com as instruções reais; integração HTTP/UI possui verificação canônica separada.

Mantém-se pendente comprovar representatividade do ambiente/documentos e validar benefício/uso humano. A avaliação estrita IA não recebeu aprovação integral por causa da omissão descrita; uma nova avaliação deve alinhar pergunta e gabarito antes de congelar outro conjunto, sem reclassificar este resultado. Erros OCR continuam possíveis mesmo com escore alto; conferência humana permanece necessária. A nova evidência não declara TRL5.

Pacote desta rodada: `output/independent-validation/elo-validacao-independente.zip`, com manifestos, gabaritos, relatórios, revisões, logs e arquivos de implementação selecionados. Segredos e bancos excluídos; ZIP histórico não foi sobrescrito.
