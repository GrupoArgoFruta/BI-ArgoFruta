# Views — Stack de Margem BI

Cole aqui o corpo real (`CREATE OR REPLACE VIEW ...`) de cada view Oracle/Sankhya referenciada na documentação em `docs/`.

Convenção:
- Nome do arquivo = nome do objeto no Oracle, maiúsculo (ex.: `VW_NOTAS_31`, `VW_BMC_BI_BASE_ITENS_V9`). Extensão `.sql` ou `.txt`, tanto faz — o que importa é o nome do objeto e o conteúdo ser o `CREATE OR REPLACE` real.
- Toda view aqui precisa ter uma seção correspondente em `docs/STACK_MARGEM_BI.md` ou `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`, sempre com as mesmas 13 partes, nesta ordem: 1. Resumo, 2. Fluxo de execução, 3. Entradas, 4. Saídas, 5. Regras de negócio, 6. Cálculos, 7. Dependências, 8. Objetos chamados, 9. Objetos que provavelmente dependem deste objeto, 10. Diagrama textual de dependências, 11. Pontos críticos, 12. Sugestões de melhoria, 13. Resumo executivo (para analista funcional). Ver `CONTRIBUTING.md` para a regra completa.
- Dependências ainda não trazidas para o repo continuam marcadas `[EXTERNO]` na documentação até o `.sql` correspondente ser adicionado aqui.