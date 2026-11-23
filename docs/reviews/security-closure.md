# Revisão independente de segurança · fechamento local do Product Vision

Revisor: agente `capacidade_final`, que não implementou consumo de IA, filtros de supervisão, medição de benefício ou otimização de leitura. Seu próprio harness de capacidade não integra esta revisão independente; a revisão de performance é de outro agente.

Snapshot examinado: `64de64f1b64d09420d168c22e27b0d1f21aa50d5`, incluindo `f9a573c` (consumo), `8beeeb1` (supervisão) e `692bd54` (hash do arquivo de benefício). Escopo local/sintético; não certifica segurança corporativa nem fornecedor de IA.

## Verificações por análise de código

- Consumo vem exclusivamente de metadados normalizados do provedor. A lista fechada remove campos desconhecidos; aceita apenas inteiros limitados, rejeita booleanos/negativos e subconjuntos inconsistentes. Não copia payload completo, cabeçalhos, credenciais ou campos extras à auditoria. Falta de metadados permanece distinta de zero.
- O assistente rejeita estruturas de consumo inválidas ou consumo em modo local. O endpoint continua gerando a resposta no servidor, revalidando sessão/contexto na persistência; não passou a aceitar respostas ou tokens arbitrários do cliente HTTP. A alteração não adiciona ferramentas de decisão à IA.
- A CLI de consumo verifica o pacote de auditoria antes de ler eventos e não acessa banco, API ou `.env`. Estimativas exigem tarifas explícitas, finitas e não negativas; saída é JSON. O escopo exclui respostas falhas/rejeitadas e não afirma reconciliação de fatura.
- A supervisão continua no endpoint já protegido; filtros são locais sobre registros já autorizados. Autor, justificativa, data, consulta e identificadores dinâmicos são escapados na renderização; filtros não alteram permissões ou decisões. A lista visual é limitada a 100 decisões e indica essa limitação. Identidade autenticada permanece separada de nomes legados/autodeclarados.
- A medição de benefício é offline e não executa conteúdo CSV. As linhas analisadas vêm dos mesmos bytes cujo hash é registrado. Exige pares comparáveis e números finitos/não negativos; saída exige destino novo, impedindo sobrescrita acidental. Resultados declarados não se tornam prova de benefício real por passarem no validador.
- A otimização de leitura fecha a transação após obter o snapshot completo e verificar integridade, antes da projeção. O objeto é recém-decodificado e privado à leitura; eliminar sua cópia não compartilha objeto persistido ou cache entre pedidos. Outros chamadores de `presentation` preservam a cópia por padrão. As escritas e autorizações transacionais não foram alteradas. O índice com conjuntos usa identificadores existentes somente para contagem.

## Limites

Não houve teste ofensivo externo, acesso a dados reais nem inspeção de segredos. As cadeias locais preservam os limites já documentados perante administradores do banco. Filtros não constituem autorização por caso e consumo persistido não cobre todas as chamadas faturáveis. Aceite de capacidade é separado deste parecer.

## Verificação executada e resultado

No snapshot acima, 37 testes passaram: `test_ai_usage.py`, `test_supervision.py`, `test_benefit_measurement.py`, `test_access.py`, `test_consultation.py`, `test_dossier.py` e `test_read_projection.py`, executados pelo `unittest` com Python do `.venv` e `PYTHONPATH=backend:.`. São testes isolados; chamadas de provedor desta suíte são simuladas. Cobrem validação de metadados, remoção de extras, contexto/citações, permissões, filtros/datas/identidade, resultados negativos e projeção após fechamento da transação. O ensaio de capacidade é separado e preserva sua falha de latência no pico.

**Resultado: aprovado no escopo local revisado, sem achado de segurança bloqueador.** Não equivale a aceite de capacidade ou certificação corporativa. Alterações posteriores nos arquivos analisados exigem revisão do delta.
