# Anexos localizados e proveniência

Consulta em 23/11/2026. **Modelos LOCALIZADOS; versão/vigência e eventual novo prazo NÃO CONFIRMADOS.** Nenhum envio, assinatura ou acesso autenticado foi feito.

O registro local `docs/edital-execution.md` relaciona a LC 0266/2026, processo 7081.01.821.0/2026, ao [registro PNCP](https://pncp.gov.br/app/editais/00360305000104/2026/811). A consulta pública nesta rodada não trouxe conteúdo verificável (resposta vazia/502); o [portal de licitações CAIXA](https://www.licitacoes.caixa.gov.br) apresentou loop de redirecionamento. Assim, não há confirmação de retificação ou prazo atual. Notícias e agregadores não foram usados para afirmar prazo.

## Originais e cópias de trabalho

O arquivo já disponível `/Users/pedronascimento/Downloads/CAIXA-LC-0266-2026-Edital.zip` contém `ANEXOI~1.ZIP`, que contém os dois modelos XLSX. A existência do pacote local não prova que seja a última versão publicada. Originais extraídos sem alteração em `output/pacote-ana/modelos-originais/`; cópias em `output/pacote-ana/anexos-trabalho/`. Hashes e mapa de cada célula preenchida estão em `output/pacote-ana/anexos-validacao.json`.

- **Anexo II:** campos técnicos da aba Inscrição preenchidos com escopo local, evidências e limites. Identificação empresarial, responsável, contatos, receitas, clientes, preço, cronograma financeiro, equipe, link público do pitch e validade permanecem A DEFINIR. Não inferimos dados societários pelo nome do usuário.
- **Anexo II-A:** arquitetura atual, tecnologias, auditoria e limites preenchidos. Comercialização, licenciamento, dimensionamento e esforço permanecem A DEFINIR. Não marcamos SSO, MFA, proteção DDoS ou hospedagem como implementados.
- São **rascunhos não prontos para submissão**. A DEFINIR pode não atender às listas de validação do formulário: substituir por valor confirmado/opção válida antes de submeter. Custos ausentes não são zero. O texto padronizado do modelo sobre envio não foi executado.

## Preservação e verificação

A edição alterou apenas células de entrada por XML, pois o leitor openpyxl alerta que salvar pelo próprio leitor removeria extensões de validação. Preservamos fórmulas, estilos, mesclagens, opções e validações; originais permanecem byte a byte. As fórmulas simples do Anexo II (referências à Inscrição e cabeçalhos IF) tiveram caches recalculados por avaliador restrito, com leitura posterior de fórmulas e valores. Nenhuma expressão foi substituída por constante.

A tentativa de recálculo completo por LibreOffice em cópia temporária excedeu o tempo disponível; não é certificado de recálculo no Excel. O Anexo II-A original contém em G3 a fórmula matricial `+G2:H3`, que referencia seu próprio intervalo e tem cache original zero. Ela foi preservada, sem alteração de seus precedentes. Esse ponto deve ser conferido no modelo vigente/Excel antes do envio; não retificamos silenciosamente o modelo. Não foram introduzidos erros de fórmula em cache.

A aba Inscrição também menciona “Anexo VI — Requisitos de Segurança”, enquanto o ZIP tem um arquivo chamado “Anexo VI - Termo de Compromisso de Combate à Corrupção.pdf”. A correspondência documental precisa ser confirmada na publicação vigente; nenhuma declaração de conformidade foi preenchida com “sim”.

## Conferência final necessária

Confirmar versão dos modelos e prazo no canal oficial; validar a correspondência dos anexos de segurança; completar dados empresariais e comerciais com responsáveis; conferir campos obrigatórios/listas, formatação e recálculo no Excel; revisar limites de texto e requisitos de submissão. Essas dependências substituem a antiga pendência de localizar os modelos: **não é mais necessário pedir que o usuário os forneça**.
