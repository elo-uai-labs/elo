# Preparação da candidatura e do orçamento

Minuta para revisão. Os modelos dos Anexos II/II-A foram localizados no ZIP disponível em Downloads; cópias de trabalho têm campos técnicos factuais e pendências explícitas. Ver `fontes-oficiais.md`. Valores comerciais, vigência dos modelos e prazo atual seguem não confirmados. O material não constitui proposta assinada. A fonte do escopo é o diagnóstico recebido, não a reprodução integral do edital vigente.

## Mapa de conteúdo para os anexos

| Conteúdo preparado | Local | Complemento obrigatório antes de transcrever |
| --- | --- | --- |
| Problema, público, proposta e benefício como hipótese | `README.md`, `pitch.md` | Terminologia e campo do modelo oficial |
| Funcionalidades, limites e matriz de atendimento | `matriz-atendimento.md` | Requisitos finais aplicáveis e critérios da instituição |
| Arquitetura, dados, identidade e metodologia | `contratos-externos.md` | Decisões/autorizações e desenho aprovado |
| Fases, experimentação, onboarding e atendimento | `piloto-onboarding.md` | Prazo, equipe, responsabilidades e metas pactuadas |
| Roteiro, dados sintéticos e resultados técnicos | `roteiro-demo.md`, registro de entrega e manifesto | Evidência referente à versão anexada e comprovantes exigidos |
| Custos, preço e cenários | `insumos-comerciais.csv`, `docs/cost-model.csv` | Quantidades, taxas/cotações datadas, tributos e aprovação financeira |

## Formação de preço sem números inventados

1. Definir escopo/fases e duração antes de estimar esforço. Separar desenvolvimento, integração, preparação, avaliação independente, operação, suporte, capacitação e saída.
2. Preencher quantidade e valor por unidade com fonte e data. Horas por perfil devem estar alocadas a uma fase; infraestrutura e retenção devem cobrir o mesmo período do cronograma.
3. Modelar baixo/base/alto por premissas de usuários, consultas, tamanho dos documentos, tokens, repetição, armazenamento e retenção. Estes cenários são hipóteses a aprovar, não previsão observada.
4. IA: considerar entrada, saída/raciocínio, tentativas cobradas inclusive recusadas e câmbio quando cotado em moeda estrangeira. Não deduzir custo pela assinatura do ChatGPT nem assumir OCR/hardware local como gratuitos.
5. Calcular subtotal `quantidade × preço unitário`; despesas em outra moeda exigem taxa/fonte/data. Indiretos e contingência usam bases explícitas, evitando duplicação com valor-hora.
6. Conciliar soma por fase = soma por categoria = total do cenário; comparar preço proposto, custo e condições comerciais em campos separados. Teto de edital não é preço.
7. Registrar quem validou cada premissa, versão e validade da cotação. Qualquer campo ausente mantém o total como “pendente”, nunca zero.

O CSV é uma ficha de insumos, não uma planilha que calcula automaticamente nem uma cotação. Nenhuma margem, alíquota ou valor-hora foi escolhido por inferência. Não há promessa de ganho financeiro: benefício pode ser monetizado somente após medir tempo humano evitado e validar o custo aplicável, descontando custo operacional incremental.

## Cronograma preenchível

Para cada fase P0–P4, preencher início, fim, dependência, responsável, horas por perfil, entregável, critério de aceite e pagamento associado se aplicável. Não associar pagamento a marco que depende de autorização ainda inexistente sem explicitar a condição. O piloto não tem duração contratada neste pacote.

## Checklist antes de protocolar

- Confirmar a vigência dos modelos localizados, versão integral das regras aplicáveis e publicação oficial do prazo; registrar URLs/documentos/data de consulta.
- Mapear todos os campos obrigatórios, assinaturas, limites e comprovantes aos arquivos finais; conferir os originais, não apenas texto extraído.
- Atualizar pitch/vídeo para a versão apresentada e confirmar direitos dos ativos/licenças e uso da identidade visual.
- Conferir preço, cronograma, equipe, disponibilidade, termos e escopo com os responsáveis; distinguir proposta de custo interno.
- Vincular hashes das evidências à versão exata e preservar as limitações técnicas/corporativas.
- Revisar arquivos contra segredos/dados reais e obter a autorização específica de submissão.
- Só então protocolar no canal oficial e guardar comprovante. Nenhuma dessas ações externas foi executada por este pacote.
