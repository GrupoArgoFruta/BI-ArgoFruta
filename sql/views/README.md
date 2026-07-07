# Views — Stack de Margem BI

Cole aqui o corpo real (`CREATE OR REPLACE VIEW ...`) de cada view Oracle/Sankhya referenciada na documentação em `docs/`.

Convenção:
- Nome do arquivo = nome do objeto no Oracle, maiúsculo (ex.: `VW_NOTAS_31`, `VW_BMC_BI_BASE_ITENS_V9`). Extensão `.sql` ou `.txt`, tanto faz — o que importa é o nome do objeto e o conteúdo ser o `CREATE OR REPLACE` real.
- Toda view aqui precisa ter uma seção correspondente em `docs/STACK_MARGEM_BI.md` ou `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md` (Resumo, Fluxo de execução, Entradas, Saídas, Regras de negócio, Cálculos, Dependências, Objetos chamados, Pontos críticos). Ver `CLAUDE.md` para a regra completa.
- Dependências ainda não trazidas para o repo continuam marcadas `[EXTERNO]` na documentação até o `.sql` correspondente ser adicionado aqui.