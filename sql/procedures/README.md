# Procedures — Stack de Margem BI

Cole aqui o corpo real (`CREATE OR REPLACE PROCEDURE ...`) de cada procedure Oracle/Sankhya referenciada na documentação em `docs/`.

Convenção:
- Nome do arquivo = nome do objeto no Oracle, maiúsculo (ex.: `STP_BMC_CARGA_MRG_BI_BASE`). Extensão `.sql` ou `.txt`, tanto faz — o que importa é o nome do objeto e o conteúdo ser o `CREATE OR REPLACE` real.
- Toda procedure aqui precisa ter uma seção correspondente em `docs/STACK_MARGEM_BI.md` ou `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`. Ver `CLAUDE.md` para a regra completa.
- Mudança em procedure que publica dado pro BI (flag `ATIVO`, truncate+reload) exige reconciliação antes de ir pra produção — ver checklist do skill `bi-impact-check`.