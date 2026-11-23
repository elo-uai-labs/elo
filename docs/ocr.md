# OCR local · documentos sintéticos

Reconhecimento opcional de texto em PNG/JPEG e PDF digitalizado no macOS. Usa Tesseract para reconhecimento e PDFKit/ImageIO para rasterização local, sem enviar arquivos a um serviço. É experimental: o escore interno do motor não mede a probabilidade de cada palavra estar correta e não substitui a conferência humana.

## Preparação e jornada

```sh
brew install tesseract
npm run setup:ocr
npm run dev
```

A preparação requer macOS, Tesseract e ferramentas Swift/SDK. O rasterizador compilado e os modelos instalados ficam em `.local/` e não são versionados. O setup baixa apenas os modelos oficiais português/inglês de `tessdata_fast`, no commit `87416418657359cb625c412a48b6e1d6d41c29bd`, verificando tamanho e SHA-256 do manifesto versionado `backend/ocr_models.json`. Documentos nunca são enviados nesse preparo ou no reconhecimento. `ELO_TESSERACT_BIN` permite selecionar um executável por caminho absoluto; sem override, o leitor procura no PATH e nas instalações padrão do Homebrew. Sem ele, o pedido informa a indisponibilidade; não há fallback para um serviço externo. A extração literal de TXT, PDF digital e planilhas continua separada.

1. Em Plano e auditoria, anexar uma imagem ou PDF exclusivamente sintético.
2. Escolher “Reconhecer texto” e informar o responsável. OCR é acionado explicitamente, não no upload.
3. Conferir texto, página e região. Coordenadas percentuais partem do canto superior esquerdo da imagem orientada. Baixar o original para comparar cada trecho.
4. Para aceitar, justificar e confirmar tanto a revisão geral quanto a conferência de cada trecho OCR com a imagem. Nenhum resultado entra automaticamente nas fontes do assistente.
5. Se estiver inconclusivo, rejeitar ou anexar nova versão mais legível. Uma extração literal inconclusiva pode ser seguida por OCR do mesmo arquivo; ambas permanecem no histórico. Cada método só pode ser executado uma vez por arquivo, e apenas uma análise desse arquivo pode ser aceita como fonte.

O original, seu hash, o método, a versão do motor, a página, a região, os escores e a revisão permanecem na trilha/exportação. As fontes do assistente identificam explicitamente quando o texto veio de OCR. O reconhecimento não decide vínculos, impactos, riscos ou encerramentos.

## Limites e critérios

- Arquivo até 1 MiB; PNG/JPEG até 12 milhões de pixels; PDF até cinco páginas, rasterizado com lado máximo de 2.048 pixels.
- Texto até 32 KiB; execução isolada com timeout global de 30 segundos e Tesseract limitado a uma thread; somente uma extração em andamento por servidor.
- Ausência de texto/página sem reconhecimento torna o resultado inconclusivo. Escore abaixo de 0,8 exige corroboração limitada descrita abaixo; sem ela, bloqueia aceitação. O limiar continua provisório, sem calibração com documentos da CAIXA.
- Uma página pode conter texto ou objetos que o motor omita mesmo com escores altos nos trechos reconhecidos. Por isso a revisão cobre também omissões, números, identificadores, acentos e ordem de leitura.
- Não recupera estrutura de tabelas, assinaturas ou autenticidade. Imagens ruins, texto manuscrito e documentos complexos exigem avaliação específica. Não há homologação corporativa nem garantia de precisão geral.

## Validação

Gabaritos sintéticos independentes do reconhecimento permitem comparar caracteres reconhecidos (CER: distância de edição / quantidade de caracteres do gabarito), presença dos IDs e localização. Testes positivos e negativos cobrem imagem clara, JPEG, PDF sem camada textual, documento degradado e página vazia. O motor Tesseract 5.5.4 teve zero erros nos gabaritos legíveis: 0/48 caracteres em PNG, JPEG e PDF digitalizado; 0/54 no exemplo com acentos. Vazio não produziu texto; a versão degradada omitiu 48/48 caracteres e foi corretamente bloqueada como inconclusiva. CER inclui espaços e quebras de linha, calculado por distância de Levenshtein. Não é uma estimativa de acurácia em documentos reais.

Nove testes específicos do engine cobrem também rotação EXIF, entrada acima dos limites, TSV malformado, limiar/valores inválidos, timeout, limpeza de temporários e PATH mínimo. Sete testes de integração cobrem autorização, confirmação adicional, fonte única e persistência/exportação/backup. Os testes de UI cobrem oito jornadas OCR, quatro cenários por tamanho. **197 testes backend e a rodada canônica completa passaram** (`ELO_TEST_DOSSIER=real npm test`), incluindo desktop/celular, IA real, cinco perfis de acesso, tipografia/glifos Porsche Next, exportação verificável e persistência idêntica após reinício. A jornada com síntese local também passou. Commit de implementação/revisão: `d3bdc7e`.

Revisão independente de performance: 12 extrações sequenciais (quatro PNG, quatro JPEG e quatro PDF de uma página), p95/máximo 0,406 s contra meta provisória de 5 s, zero falhas nos exemplos claros. Medição de engine, sem HTTP/SQLite/UI e sem teste de saturação. Tempo e CER são métricas distintas. Metadados preservam versão do adapter/runtime, modelos, rasterizador e parâmetros de execução.

Evidências regeneráveis: `output/validation/ocr-quality.json`, `ocr-performance.json`, `ocr.json` e capturas `desktop-ocr-*`/`mobile-ocr-*`. Apple Vision não faz parte do aceite desta entrega: foi substituído por Tesseract após inicialização lenta neste ambiente. Testes usam bancos temporários, nunca `data/elo.sqlite3`.

## Referências técnicas

[Interface de linha de comando do Tesseract](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage) · [Modelos oficiais fixados](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd) · [Rasterização PDFKit](https://developer.apple.com/documentation/pdfkit/pdfpage/thumbnail(of:for:)).

## Revisões e aceite local

Segurança, DBA, revisão geral e performance foram avaliadas por agentes independentes dos implementadores dos respectivos trechos, com hashes vinculados ao commit `d3bdc7e`. Ajustes incluíram validação de TSV truncado, descoberta do executável fora do shell de login e descrição correta de fontes OCR no assistente. Revisão de dados incluiu dez disputas de aceite entre métodos do mesmo anexo (sempre um sucesso/uma recusa), preservação de registros v2 sem `method`, exportação e backup com regiões/escores.

O ambiente continua local/sintético. No macOS não há teto rígido de memória para o rasterizador; limites de entrada, pixels, páginas, CPU e tempo reduzem risco, mas não certificam resistência a documentos hostis ou capacidade corporativa. Não houve publicação ou uso do banco manual em testes.


## Correção de triagem v2 · política congelada antes da validação independente

O corpus de desenvolvimento `tests/fixtures/trl-evaluation/ocr.json`, já exposto, mostrou dois mecanismos distintos: PNG/JPEG reconheciam o hífen após `CTR-701` corretamente com escore baixo; no PDF, a letra `A` de `Servico A` tinha escore 0,693. A regra do mínimo de todas as palavras bloqueava a revisão desses documentos apesar de o texto estar correto. Essa constatação é específica do conjunto conhecido.

`elo-tesseract-ocr-v2` aplica `layout-corroboration-v1`: somente uma página com escore abaixo de 0,8 recebe uma segunda leitura, PSM11, após a leitura PSM3. O texto principal nunca é substituído. A sequência de todos os tokens da página deve coincidir exatamente, incluindo números, acentos e pontuação; apenas limites de linhas/espaços de layout podem diferir. Não há consulta ao gabarito no runtime.

- Quando todos os tokens da segunda leitura atingem 0,8, a página pode seguir para revisão humana. Isso inclui um número cuja primeira leitura tenha escore baixo: a igualdade textual e o limiar da segunda leitura são necessários, mas não comprovam exatidão.
- Exceção provisória dirigida ao defeito conhecido: se as duas leituras têm baixa confiança somente em hífen isolado entre um identificador `CTR|FOR|EMP|DOC` e um rótulo alfabético, na mesma linha de cada leitura, permite revisão. Não permite sinal diante de número, moeda, intervalo entre IDs, sinal de soma ou conteúdo fraco. Códigos de moeda usuais são recusados. Esta heurística não interpreta o significado e não prova que o hífen esteja correto.
- Divergência em qualquer token, omissão, baixa confiança não abrangida, erro ou timeout mantém bloqueio. Página vazia continua inconclusiva. Não há terceira tentativa ou seleção da resposta com maior confiança.
- Mínimos/escores originais e o flag `low_confidence` são preservados. A interface existente exibe o aviso e a nota da corroboração; para o hífen, informa que permanece incerto. Palavras/escores das duas leituras e política aplicada ficam nos metadados auditáveis, inclusive exportação e backup. A revisão OCR explícita continua obrigatória antes de virar fonte de IA.
- Limites continuam 30 segundos globais compartilhados entre rasterização e ambas as leituras, cinco páginas, 500 segmentos por leitura e 32KiB por texto. Nada é enviado externamente; não há mudança de SQL, schema, OCR Swift ou UI.

A regressão exposta passou 7/7 triagens, mantendo os textos originais, vazio e degradado bloqueados. Evidência: `output/validation/ocr-correction-development.json`. Esse resultado é desenvolvimento, não validação independente nem precisão geral. A validação independente será relatada pelo orquestrador separadamente, sem usar suas fixtures para ajustar esta política. Novos testes cobrem divergência numérica/pontuação, sinais financeiros, intervalos, mudança de linha, metadados malformados, segunda leitura dentro do orçamento e limpeza após timeout, além de revisão obrigatória/exportação/backup com banco temporário.

Resultado posterior da v2: regressão conhecida7/7 e novo conjunto de autoria independente12/12triagens, CER1/1299. O conjunto novo não acionou a segunda leitura; esse ramo é coberto pela regressão exposta e testes específicos. Consulte [registro atual de validação](validacao-independente.md) para verificações e limites; resultados de197testes acima são históricos.
