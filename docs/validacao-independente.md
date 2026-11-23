# Correção OCR e validação independente · 23/11/2026

## Escopo e protocolo registrado antes das novas execuções

Base: `fb1c1af`, branch `codex/product-vision`. Pedido: corrigir a triagem excessivamente conservadora do OCR e validar IA com uma amostra independente, usando o orquestrador pessoal em paralelo. Execução local, dados sintéticos, bancos temporários, sem publicação.

Três autores separados: `ocr_correcao` implementa a correção usando somente os conjuntos anteriores; `ocr_independente` produz um conjunto novo sem ajustar o conteúdo aos erros do extrator; `ia_independente` produz casos novos sem alterar runtime/prompts. Manifestos, gabaritos e critérios são congelados em commit antes da primeira execução. O orquestrador revisa semanticamente as respostas da IA, separado do autor do conjunto e do código de geração. Essa separação é de autoria técnica; não constitui validação humana, independência institucional ou representatividade comprovada.

Critérios da correção: reproduzir e resolver os falsos inconclusivos do conjunto anterior sem aceitar texto vazio/ilegível, retirar revisão humana ou enfraquecer limites de arquivos, páginas, tempo e localização. Nova rodada anterior é regressão exposta, preservando a avaliação inicial. Critérios numéricos de cada conjunto independente constam no manifesto congelado. Falhas da primeira execução serão mantidas, sem seleção posterior de casos ou repetição até aprovação.

IA: até 20 chamadas reais explícitas ao modelo configurado, sem repetição automática, com fontes e respostas preservadas e hashes. Além de referências e abstenção, revisão de sustentação de cada afirmação, omissões e segurança de limitações/sugestões. Resultados com erro permanecem no denominador operacional, separados do denominador semântico. Aprovação completa exige nenhuma falha, afirmação não sustentada ou omissão esperada e abstenção adequada em todos os casos. Âncoras lexicais são indicadores auxiliares, nunca prova semântica.

Revisões previstas: geral, segurança (entrada documental não confiável) e performance (processamento OCR), com revisores distintos do implementador e entre as especialidades. DBA não se aplica se não houver mudança de persistência, SQL ou transações. Verificações canônicas: `npm run build`, `npm test`, além das avaliações e regressões específicas. Nenhuma alteração visual prevista; suíte existente verifica desktop/celular/PDS.

## Estado

Em execução. Resultados, commits e pendências serão registrados após os testes; nenhum aceite antecipado.
