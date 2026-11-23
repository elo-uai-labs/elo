# Demonstração reproduzível e coleta de evidências

Escopo: sintéticos, loopback e ambiente de demonstração isolado. Nunca usar ou apagar `data/elo.sqlite3` para teste. O pacote não contém credenciais, banco preenchido nem modelo OCR binário. A instalação precisa das dependências descritas no README da raiz. OCR exige `npm run setup:ocr`; PDF digital exige o ambiente Python de documentos. Sem esses recursos, registrar capacidade indisponível em vez de simular sucesso.

## Execução automatizada de referência

Na raiz do checkout, Node 24 e dependências instaladas:

```sh
npm run build
npm test
```

A suíte provisiona bancos temporários, cobre UI, autenticação local e reinício. Para modelo real previamente configurado pelo responsável:

```sh
ELO_AI_PROVIDER=openai ELO_MODEL=gpt-6.2-sol ELO_TEST_DOSSIER=real npm run test:e2e
```

Esse comando faz chamadas pagas à API com dados sintéticos. A chave fica no ambiente local protegido e não integra a evidência. Arquivar resultados e manifesto após a execução, sem sobrescrever o registro histórico de uma rodada anterior. Arquivos em `output/validation/` podem ser regenerados; confira data e modelo antes de apresentá-los.

## Sessão acompanhada

Previsão de roteiro: 20 minutos, não tempo medido. Use instância própria e contas sintéticas com perfis separados conforme `docs/access.md`; não reutilize nomes autodeclarados para demonstrar segregação autenticada. Os CSVs de `docs/demo/` pressupõem a base sintética inicial. Importar novamente IDs existentes deve ser recusado.

| Etapa | Ação | Resultado esperado | Guardar |
| --- | --- | --- | --- |
| 1 | Mostrar capacidades/limites e modo de identidade | Local/sintético explícitos; IA, extração/OCR e dependências corretamente identificados | Captura sem segredos e versão |
| 2 | Importar `docs/demo/contratos-com-indicio.csv` como Contratos; conferir mapeamento e prévia | Registros e erros reconciliados antes da confirmação; origem sintética confirmada | Contagem, IDs e resultado da prévia |
| 3 | Executar detecção; importar `contratos-sem-indicio.csv` e repetir | Positivo para `CTR-DEMO-POS`; ausência de sinal para negativo; repetição não duplica | IDs/versão de regra e contagens |
| 4 | Importar `fornecedor-segundo-sinal.csv`, executar segunda regra e abrir grupo | Sinais do mesmo contrato juntos; fontes e decisões distintas; trabalho pode compartilhar vínculos | Captura do grupo e IDs |
| 5 | Gerar dossiê IA real, abrir referências e registrar discordância fundamentada | Modelo/prompt visíveis; cada afirmação com fontes; nenhuma decisão de risco automática | Dossiê, motivo e evento |
| 6 | Anexar `docs/demo/evidencia.csv`, extrair e abrir célula; demonstrar PDF/imagem de fixture aprovada quando disponível | Célula/página/região localizável; original baixável; revisão humana; inconclusivo não aceita | Hash e localização; resultado da revisão |
| 7 | Consultar risco e documento revisado no assistente; fazer pergunta fora das fontes | Resposta citada ou limitação/abstenção; consulta não altera risco/plano | Perguntas, modelo, claims e fontes |
| 8 | Qualificar, propor impacto e revisar em outro perfil | Justificativas, versões e revisão independente; conflito de versão recusado | IDs de decisão/impacto e perfis sintéticos |
| 9 | Atribuir plano, anexar execução, solicitar e revisar encerramento | Executor atribuído e aprovador distinto; painel reflete resultado | IDs, prazo/status e eventos |
| 9a | Abrir Avisos e acompanhamento operacional, combinar filtros e concluir trabalho | Aviso resolvido desaparece; SLA por prazo vigente e recorrência têm critérios explícitos; filtros não mudam universo dos indicadores | IDs, data de referência e resultados filtrados |
| 10 | Exportar auditoria de negócio/acesso; verificar e reiniciar | Pacotes íntegros; mesmo estado após reinício | Resultado do verificador e comparação |

Para testar OCR legível/degradado/branco use as fixtures e procedimentos em `docs/ocr.md`; não invente um PDF a partir de informações reais. Se uma capacidade evoluída nesta execução ainda não tiver aceite, apresente-a como em validação.

## Registro mínimo por rodada

Preencher `registro-ensaio.csv` com início/fim, tempo humano ativo separado de espera, esperado/observado, IDs e defeito. Registrar commit base e hashes do checkout, modelo, prompt, regras, versões de dependências e hash da amostra. Não colocar chave, sessão, senha, arquivo de contas ou dados corporativos no pacote.

Critério de sucesso local: todos os resultados esperados satisfeitos e evidência preservada. Qualquer falha mantém a etapa aberta; corrigir e repetir a etapa afetada. Qualidade semântica da IA, precisão do OCR e metas do piloto exigem avaliação própria, além desta demonstração funcional.
