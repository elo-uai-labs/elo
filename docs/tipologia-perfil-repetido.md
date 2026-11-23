# Perfil contratual repetido · experimento local

A terceira tipologia `repeated-contract-profile`, versão 1, compara contratos com IDs distintos, mesmo fornecedor, mesmo aprovador e título igual após normalizar espaços e caixa. Acentos não são removidos. Nenhuma similaridade aproximada, valor, período ou pagamento é inferido. Serviços recorrentes e cadastros legítimos podem produzir o sinal; a pessoa revisora precisa abrir as fontes e justificar a conclusão.

Cada contrato recebe um sinal independente. O outro contrato usado como fonte é o primeiro ID distinto em ordem lexical dentro do grupo; as duas fontes contratuais, fornecedor e aprovador ficam preservados no sinal. Importar novos contratos invalida a varredura dessa tipologia para reavaliar contratos antigos, sem duplicar IDs ou reescrever decisões/fontes históricas. Os parâmetros de ativação e filtro de título são aplicáveis; parâmetros de código cadastral não se aplicam. O filtro de título delimita os contratos comparados.

O vínculo inicial com risco e dimensão continua ilustrativo; a pessoa pode revisá-lo antes de decidir. A tipologia não é regra de negócio aprovada pela CAIXA e não representa duplicidade financeira ou culpa.

Gabarito independente em `backend/lab_repeated_fixture.json`: seis cenários, dois positivos, quatro negativos (fornecedor, aprovador, título e acentuação distintos). Execute `.venv/bin/python3 backend/laboratory.py --rule-id repeated-contract-profile`. Testes cobrem entrada incremental, fonte determinística, não duplicação, reinício e síntese local sem afirmação de coincidência cadastral com empregado. O E2E abre o dossiê em desktop e celular.
