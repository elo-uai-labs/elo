> Rodada posterior: triagem OCR corrigida e nova avaliação independente concluída; veja [resultados e limites](../validacao-independente.md). O texto abaixo preserva a rodada histórica.

# Conclusão técnica da rodada TRL

Escopo: ampliar autonomamente as evidências para TRL5 do Elo, sem publicar, acessar sistemas da CAIXA, usar dados reais ou substituir avaliação humana. O [ambiente proposto](ambiente-relevante.md) e os protocolos foram definidos antes das execuções. Os resultados sustentam somente o ambiente simulado descrito.

## O que foi demonstrado

- **Integração de fonte separada:** serviço HTTP real em outro processo, contrato paginado/versionado, bearer sintético, reconciliação de IDs/contagens, coleta completa antes da transação, repetição e concorrência idempotentes. Seis testes incluem401/503/timeout/redirecionamento/mudança de versão/snapshot/duplicação inválida; destino preservado em falhas. CLI recusa banco em data/; endpoints somente loopback.
- **Operação autenticada e mista:** cinco papéis,60s,1251 requisições na carga/1288 no ensaio, todas reconciliadas com a trilha. Zero erros inesperados;99 negativas/conflitos esperados separados. Leituras p95=.05475s; escritas bem-sucedidas p95=.07833s. Foram exercitados ingestão, detecção, dossiês locais, planos, relatórios, TXT revisado, assistente local e trabalhos durante leituras concorrentes.
- **OCR/OpenAI reais com leituras autenticadas:** complemento explícito com duas chamadas GPT-6.2 Sol,144 leituras por três clientes em7,801s,p95 de leitura=.0136s,zero erros inesperados. OCR=.329s,dossiê=4.334s,consulta=3.129s; consulta citou EVD-0001 revisado e informou330,00.1639 tokens auditados;157 respostas reconciliadas com a trilha, snapshot protegido e reinício conferidos. Fixture conhecida e revisão de teste automatizada, não nova avaliação de qualidade nem carga sustentada.
- **Continuidade e isolamento:** reinício após SIGKILL quiescente, sessão antiga recusada, expiração/logout/desativação após reinício, backup e restauração exatos. Ensaio adicional interrompeu o processo DENTRO da transação, após INSERT da auditoria e antes do UPDATE do workflow: snapshot anterior restaurado, auditoria íntegra e repetição com um único registro/evento. Não simula falha elétrica/disco nem atomicidade entre commit e recibo HTTP.
- **IA em conjunto novo:**16 tentativas reais GPT-6.2 Sol, 15 respostas aceitas e uma falha de geração/validação. Nas15 aceitas,20/20 afirmações sustentadas após revisão independente por agente,0/16 fatos esperados omitidos e0/15 sugestões/limitações inseguras. A falha está fora desses denominadores e NÃO foi apagada. Uma sugestão de maturidade menciona “registro da contratação”, domínio não estabelecido pela fonte: extrapolação de escopo registrada na revisão, sem tratá-la como ação automaticamente executada.
- **Correção de citações:** teste independente confirmou assimetria: dossiês recusavam entidades literalmente mencionadas em contrato citado, embora a consulta já as permitisse. `7ede206` usa a mesma checagem por fonte efetivamente citada, sem transformar uma entidade mencionada em nova fonte. Citações desconhecidas, entidade inventada e entidade de fonte não citada continuam recusadas. Regressão real separada do caso exposto passou,1/1 afirmação sustentada. A causa exata da primeira resposta falhada não foi preservada e não é atribuída retrospectivamente a esse defeito.
- **OCR em novos formatos:** sete arquivos, sendo cinco legíveis, branco e ilegível. CER 0/1170 nos legíveis e zero caracteres falsos no branco; porém triagem 4/7, abaixo do critério7/7. Carta, JPEG e PDF de duas páginas ficaram inconclusivos por confiança baixa, apesar do texto correto. São apenas três conteúdos textuais distintos com variações de formato, não1170 amostras independentes. Não alteramos limiar/gabarito para obter aprovação.

## Aceites separados

| Frente | Resultado | Interpretação |
| --- | --- | --- |
| Fonte e idempotência | Aprovado no protocolo | Contrato sintético próprio, não integração corporativa homologada |
| Operação mista e recuperação | Aprovado no protocolo | Ambiente pequeno/local, tempo limitado, sem pessoas reais |
| Validação IA da primeira rodada | Parcial/falhou critério automático | Uma das16 tentativas falhou; revisão semântica cobre apenas15 |
| Regressão dirigida do dossiê | Aprovado | Conjunto já exposto; não substitui a primeira rodada nem novo holdout |
| OCR da primeira rodada | Parcial/falhou triagem | Texto correto não elimina a indisponibilidade causada pela triagem conservadora |
| Representatividade do ambiente | Hipótese documentada | Não verificada contra operação-alvo ou corpus de domínio independente |

## O que continua pendente

1. **Sustentar a representatividade.** Confrontar volumes, distribuição de exceções, documentos, identidade/integrações e critérios com um ambiente operacional-alvo ou referência independente verificável. Pode ser outra organização/profissional de controles; não exige necessariamente a CAIXA. Hoje os dados e o contrato foram produzidos pela equipe de desenvolvimento.
2. **Resolver e revalidar a utilidade do OCR.** Investigar/calibrar recusas excessivas sem permitir aceitação insegura; avaliar em outro conjunto reservado após qualquer alteração. O resultado atual não autoriza alegar triagem7/7 ou qualidade geral.
3. **Confirmar robustez da IA após correção em nova amostra.** A regressão de um caso mostra comportamento corrigido, não taxa de sucesso em produção nem validação independente de domínio. Revisão por agente não é homologação profissional humana.
4. **Validar a operação-alvo.** SSO/MFA, TLS, rede externa, ambiente hospedado, múltiplas instâncias, observabilidade externa, disponibilidade prolongada e metas corporativas não foram exercitados. Aplicabilidade depende da arquitetura-alvo, não de adicionar tecnologias apenas para elevar uma etiqueta.
5. **Observar pessoas e benefício.** Instrumento de comparação está pronto, mas ninguém participou de um estudo com tarefas reais; não há ganho de tempo, redução de erro ou usabilidade humana comprovados.

## Classificação sustentada

**A autoavaliação conservadora permanece TRL4 fortalecido, com evidências adicionais para transição ao TRL5.** Não declaramos TRL5 integral ou homologado. O impedimento é a combinação de representatividade ainda não comprovada e critérios de qualidade não integralmente satisfeitos; não uma exigência artificial de autorização da CAIXA para qualquer simulação. A classificação deve identificar exatamente tecnologia, versão, ambiente e resultados aceitos. A referência utilizada é [NASA/ESTO, critérios de TRL para software](https://esto.nasa.gov/trl/).

## Rastreabilidade

Fixtures novas congeladas em41cf4bc; fonte399a4c2; operaçãofc7b248; correção7ede206; ensaio de interrupçãoa4ef5f9/e6ed7ff. Revisões: [geral](../reviews/general-trl5.md), [segurança](../reviews/security-trl5.md), [DBA](../reviews/dba-trl5.md), [performance](../reviews/performance-trl5.md). Artefatos originais e regressão permanecem separados. O pacote contém manifesto com hashes; consistência local não equivale a assinatura externa.

## Inicialização do leitor PDF

A primeira rodada canônica encontrou um timeout de5s na importação inicial da dependência PDF. Um diagnóstico isolado sem documentos mediu importação de pypdf em31,13s; a repetição em0,071s. O teste PDF isolado passou depois e o limite de5s não foi ampliado. A falha inicial foi preservada em `output/validation/trl5/canonical-first-failed.log`. Não se atribui causa de sistema de arquivos específica sem evidência; o tempo de inicialização deve ser verificado no ambiente de homologação, especialmente a frio.

## Aceite integrado final

`npm run build` e repetição de `npm test` aprovados: **237 testes backend + 5 testes offline**, jornadas desktop/celular, autenticação, operação e supervisão, com PDS 4.10.1/Porsche Next e glifos web verificados. Jornada completa com `ELO_AI_PROVIDER=openai ELO_MODEL=gpt-6.2-sol ELO_TEST_DOSSIER=real npm run test:e2e` também aprovada, após a correção do validador: 14 casos, 122 eventos, auditoria íntegra e estado idêntico após reinício. Isso não reclassifica os resultados originais do conjunto reservado como aprovados.

Servidor local atualizado; health/backend e frontend responderam 200. Banco manual preservado, nenhuma publicação/envio. Os protocolos são reproduzíveis pelos comandos documentados; chamadas pagas são explícitas. O pacote `output/trl5/elo-evidencias-trl5.zip` inclui fontes sintéticas, relatórios e manifesto, sem chave ou banco.
