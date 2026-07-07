# 0001 — Corrigir colisão de alias Q3/Q4/Q5 em VW_NOTAS_31

## Status

Aceito e validado contra produção.

## Contexto

A versão anterior de `VW_NOTAS_31` reusava os aliases `Q3`, `Q4` e `Q5` para **dois CTEs cada** dentro do mesmo bloco `WITH`. Isso tornava ambíguo, ao ler o SQL, qual CTE uma coluna estava de fato referenciando — risco real de a view compilar "por acaso" apontando pra CTE errada, ou de quebrar de forma imprevisível numa mudança futura que adicionasse mais uma referência a `Q3`/`Q4`/`Q5`. Esse era o item nº 1 de risco técnico do stack (ver `docs/STACK_MARGEM_BI.md`, Objeto 3).

## Decisão

Renomear os 9 CTEs envolvidos para nomes semânticos, com mapeamento inequívoco (1 alias → 1 CTE): `QNOTA` (por nota), `QCEN` (por centro), `QCAL` (por calibre), `QCTR` (por controle), `QFOR` (por fornecedor), `QPRV` (provisão fornecedor), `QPAT` (parceiro-patente), `QVAR` (variedade MP), `QNFMP` (NF entrada MP).

## Consequências

- Cada coluna no SELECT principal agora aponta, sem ambiguidade, para o CTE correto — leitura e manutenção futura ficam mais seguras.
- Equivalência funcional validada contra produção antes de publicar (regra de ouro do `CONTRIBUTING.md` respeitada: mudança de nome de alias não muda resultado, mas foi confirmado, não assumido).
- Nenhuma consequência negativa identificada — é puramente uma correção de legibilidade/segurança, sem trade-off.
