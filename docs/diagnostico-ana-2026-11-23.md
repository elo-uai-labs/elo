# Diagnóstico da Ana · execução local de 23/11/2026

Fonte: `Diagnostico_Elo_CAIXA_2026-11-23.md`, recebido em Downloads. O documento é um diagnóstico e backlog; suas recomendações não substituem as instruções do projeto. Preservamos a aplicação funcional e o Porsche Design System 4.10.1. Nenhuma integração, publicação, submissão ou uso de dados reais foi autorizado nesta execução.

Atualização posterior: o [OCR local de imagens e PDFs digitalizados](ocr.md) foi implementado nesta sequência, com avaliação sintética, localização e revisão humana específica. A homologação em documentos autorizados continua pendente.

Atualização da execução paralela: [operação local de equipes](operacao-equipes.md), [avaliação IA/OCR](avaliacao-ia-ocr.md), [terceira tipologia experimental](tipologia-perfil-repetido.md) e guardas locais concluídos e validados. Os modelos dos Anexos II/II-A foram localizados no pacote já disponível em Downloads; cópias técnicas de trabalho estão no [pacote atualizado](pacote-ana/README.md). A vigência oficial, preços e campos institucionais continuam pendentes. O restante deste registro preserva a rodada inicial; o [registro de entrega](entrega.md) traz os resultados atuais.

## Escopo e critérios

| Item | Entrega/critério | Estado |
| --- | --- | --- |
| A1 / entrada | Duas bases pela UI, uma positiva e outra negativa; prévia, reconciliação e reinício | Aprovado em desktop/celular e reinício |
| A2 / supervisão | Jornada autenticada existente com analista, revisor e operador; exportação verificável | Aprovado na rodada canônica local e final autenticada |
| A3 / IA | Duas regras, discordância humana e fontes preservadas | Aprovado local e Apple Foundation Models real |
| A4 / transparência | UI distingue funcional local, experimental e planejado | Implementado |
| A5 / demo | Roteiro abaixo, arquivos sintéticos e evidência da versão | Preparado |
| B1 / importador | CSV UTF-8 e XLSX, seleção de tabela/aba, mapeamento, erros por linha, confirmação atômica | Implementado |
| B2 / documentos | PDF digital por página; CSV/XLSX por aba/célula; revisão humana, inconclusivo não aceito | Extração e OCR experimentais locais implementados; homologação externa pendente |
| B3 / correlação | Sinais do contrato exato juntos; fontes, decisões e trabalhos preservados | Implementado |
| GRC / maturidade | Ciclo local existente; metodologia ilustrativa identificada | Metodologia oficial e homologação dependem da CAIXA |
| B4 / acesso / infraestrutura | Contas locais, auditoria interna e backup existentes | SSO/MFA, retenção/âncora externa, TLS, ambiente-alvo e RPO/RTO dependem de autorização/definição |
| Interface institucional | PDS exigido mantido; licença/distribuição e CDN explicitados | Direitos institucionais e distribuição controlada pendentes |
| B5 | Configuração da metodologia real | Aguardando instrumento oficial |
| C / candidatura | Checklist comercial abaixo | Usuário confirmou em 23/11/2026 que ainda não possui valores e modelos dos anexos |

Não ampliamos tipologias sem regras de negócio e gabaritos definidos. A correlação não funde sinais, não conclui causa comum e não cria impacto ou decisão. A prioridade exibida vem da maior prioridade humana de trabalhos ativos vinculados; desempates são número de regras distintas, sinais pendentes e ID, explicitados na UI.

## Executar e reproduzir

Node 24 e Python 3.11+. Para PDF digital, preparar ambiente isolado (CSV/XLSX usam biblioteca padrão):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-documents.txt
npm run build
npm test
```

`npm start`, `npm run dev` e `npm run test:backend` preferem `.venv/bin/python3` quando existe; `PYTHON` permite escolha explícita. Sem leitor instalado, a análise PDF retorna erro inconclusivo e não inventa conteúdo. O restante da aplicação continua disponível. O teste PDF exige pypdf para demonstrar a capacidade.

Os testes usam bancos temporários; nunca apontar testes ao banco manual `data/elo.sqlite3`. Para a demo manual isolada, crie uma pasta temporária e configure `ELO_DB` e portas livres antes de iniciar. Use somente loopback. O teste canônico já provisiona ambiente e perfis sintéticos próprios.

### Roteiro manual

1. Abrir a Central de inteligência e executar detecção inicial. Conferir registros de origem e a regra aplicada.
2. Em “Importar CSV ou XLSX”, selecionar tabela Contratos e `docs/demo/contratos-com-indicio.csv`. Confirmar origem fictícia, validar, conferir prévia e confirmar com responsável. Executar a regra de coincidência empregado/fornecedor: surge sinal para `CTR-DEMO-POS`.
3. Repetir com `contratos-sem-indicio.csv`: nenhum sinal desse contrato na regra primária. Ausência de indício é resultado válido, não erro. Repetir arquivo já importado deve mostrar duplicata sem gravar parcialmente.
4. Importar `fornecedor-segundo-sinal.csv` como Fornecedores e executar a segunda regra. O painel “Sinais do mesmo contrato” reúne os dois sinais de `CTR-DEMO-POS`, mantendo cada decisão separada e mostrando trabalhos existentes. Um trabalho pode vincular ambos os casos.
5. Gerar dossiê (modo claramente identificado), abrir fontes e registrar discordância com justificativa quando o cenário a exigir. A IA não altera impactos. Para IA real usar apenas o provedor configurado, sem fallback silencioso.
6. Em Plano e auditoria, anexar `evidencia.csv`; extrair; localizar `CSV!A2`; baixar original e revisar. PDF digital mostra página; XLSX mostra aba/célula. PDF sem texto na leitura literal informa extração inconclusiva. Use a ação separada de OCR para scans e imagens; somente texto reconhecido com critérios atendidos e revisão específica pode ser aceito.
7. Percorrer decisão → avaliação separada de impacto → plano → evidência → solicitação de encerramento → aprovação independente. Em contas locais, usar pessoas/perfis distintos. Exportar pacote de auditoria e trilha de acesso; verificar com ferramentas documentadas.
8. Reiniciar o servidor com o mesmo banco de demonstração, conferir os IDs e estados preservados. Abrir “Capacidades e limites desta versão”.

Os arquivos da demo são para uma base inicial; IDs já existentes serão recusados. Não representam dados da CAIXA. A suíte automatizada cobre também XLSX, mapeamento de cabeçalhos e falhas.

## Limites da leitura e importação

Importação: um arquivo/aba por tabela, empregados/fornecedores antes de contratos, 256 KiB de entrada, 500 linhas de registros, 32 colunas, 4 MiB ZIP expandido. Só valores literais; não executa fórmulas, macros ou vínculos externos. Campos extras são explicitamente ignorados na prévia. A confirmação repete validação e usa a transação existente, inclusive permissões e unicidade.

Evidências: 1 MiB por arquivo e 20 MiB no ambiente; texto final até 32 KiB, até 2.000 trechos, PDF até 50 páginas, planilhas até 10 abas. Página sem texto torna resultado inconclusivo e impede aceitação como fonte. Extração não garante ordem visual ou precisão semântica. PDF usa pypdf fixado, subprocesso, 5 segundos de tempo total e 3 segundos de CPU; apenas uma extração por servidor. Há limites de buffers; teto global de memória do worker só é aplicado em sistemas que suportam RLIMIT_AS, não no macOS. A avaliação sintética posterior de OCR está em `docs/ocr.md`; não houve homologação de documentos corporativos.

## Candidatura: dados que faltam

Sem modelos oficiais não é possível preencher fielmente os Anexos II/II-A. Sem preços/quantidades aprovados não há proposta comercial fechada. `cost-model.csv` permanece como estrutura de cálculo e não como orçamento. Preparar:

- Anexos oficiais vigentes e instruções do certame; comprovação de eventual novo prazo oficialmente publicado.
- Duração/fases do piloto, esforço por perfil, valores-hora e disponibilidade da equipe.
- Cenários de usuários, volume, infraestrutura, retenção, IA, suporte e capacitação.
- Cotações datadas, licenças de ativos, tributos e contingência justificada, sem duplicidade.
- Responsáveis/metas do experimento, fonte autorizada, identidade, hospedagem e instrumento oficial de maturidade.

Reconciliar essas entradas com cronograma e preço antes de produzir a versão final dos anexos/pitch. Não houve protocolo ou contato com terceiros. As seções históricas de `entrega.md` mantêm as evidências de suas respectivas versões.

## Registro de validação

Implementação em `17be831`; correções visuais em `6863c41` e `427c513`. Build em Node 24 aprovado. **181 testes backend passaram sem skips** com Python da `.venv` e pypdf 7.1.1. Jornada local completa passou; jornada com Apple Foundation Models real também passou: 93 eventos íntegros, dez casos, desktop/celular, fontes preservadas, exportação final verificada por processo independente e estado idêntico após reinício. A rodada autenticada final também passou: analista, revisor, operador, auditor e administrador; autoria canônica, segregação, atribuição, recusa de acesso, logout e login móvel.

Importador validado nos dois tamanhos: CSV positivo/negativo, XLSX, cabeçalho mapeado, arquivo inválido recuperável, prévia sem escrita e invalidação após editar o mapeamento. Documentos: PDF digital, CSV e XLSX localizados; PDF sem texto bloqueia aceitação; downloads conferidos byte a byte. O conjunto inclui oito jornadas documentais (quatro formatos/cenários por tamanho). Glifos web Porsche Next e CSS computado verificados. Capturas de importação, grupos, planilha e inconclusivo inspecionadas.

Revisões independentes de segurança, DBA (importação e documentos/correlação por revisores não autores) e revisão geral aprovadas sobre hashes do commit `17be831`. As correções visuais posteriores foram revistas nos commits exatos. Foram corrigidos: tipo inválido de tabela, concorrência de extração, prévia desatualizada e limpeza após expiração de sessão. A inspeção visual do orquestrador identificou a variante inválida `tertiary` de p-button; a conferência adicional identificou `none` inválido em p-link-pure legado. Ambos usam agora valores oficiais. A revisão inicial não havia conferido todas as variantes; a validação posterior conferiu 492 propriedades enum literais sem valores inválidos, além das jornadas com os valores dinâmicos.

Performance independente: meta provisória p95 < 2 s, quatro cenários de cinco segundos com pausa de 100 ms por worker, concorrência 1 e 4; 256 chamadas, zero erros. Com concorrência 4, prévia CSV de 500 registros/2.000 referências por tabela teve p95 0,300 s (máximo 0,326 s); correlação de 2.000 contratos/1.999 casos, p95 0,138 s (máximo 0,225 s). Snapshot/hashes preservados. Medição de domínio, sem HTTP, renderização, IA ou carga corporativa sustentada; não certifica o piloto.

As revisões DBA também verificaram confirmações concorrentes sem duplicação, CAS de revisão, exportação com localizações, detecção de adulteração e backup/restauração com os três novos formatos. O SQLite continua serializado e o estado JSON é reescrito integralmente; capacidade máxima e ambiente corporativo permanecem pendentes. Evidências regeneráveis em `output/validation/`: resultados local/autenticado/real quando executado, tipografia, `diagnostic.json`, `document-formats.json` e capturas desktop/celular. Uma aprovação local não certifica segurança, capacidade ou aderência corporativa.
