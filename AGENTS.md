# Elo

- Leia README.md, docs/design-system.md e docs/entrega.md antes de alterar o projeto.
- Porsche Design System **4.10.1** é requisito de aceite. Use os componentes oficiais para todos os elementos que possuem equivalente; preserve suas variantes, fontes, escala, pesos e entrelinhas.
- Não simule componentes com CSS, não adicione outra biblioteca visual e não sobrescreva internals/shadow DOM. HTML semântico é permitido para estrutura e slots exigidos pelo PDS.
- Importe a folha completa do pacote e use partials oficiais. Confirme Porsche Next carregada e glifos webfont realmente renderizados, além do CSS computado. Execute os testes em desktop e celular.
- Mantenha dados sintéticos e o escopo local explícitos. IA não decide impactos; decisões humanas exigem justificativa.
- Não altere ou apague data/elo.sqlite3 para testes. Use bancos temporários.
- Não publique no GitHub nem exponha o servidor externamente sem nova instrução do usuário.
- Comandos canônicos: npm run build, npm test. Modelo real: ELO_TEST_DOSSIER=real npm run test:e2e, quando configurado.
