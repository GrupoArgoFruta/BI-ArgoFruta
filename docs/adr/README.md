# Architecture Decision Records (ADR)

Registro de decisões técnicas relevantes deste repositório: o contexto que levou à decisão, alternativas consideradas e as consequências (inclusive as negativas/trade-offs aceitos).

## Quando criar um ADR

Uma decisão merece um ADR quando: muda comportamento de um objeto que alimenta o BI de margem (ver `CONTRIBUTING.md`, regra de ouro), afeta como o time trabalha neste repositório (convenção, estrutura, ferramenta), ou envolve um trade-off que vale a pena não esquecer (ex.: abrir mão de uma automação em troca de visibilidade/portabilidade).

## Formato

Um arquivo por decisão, numerado sequencialmente: `NNNN-titulo-curto.md`. Seções:

- **Status**: proposto / aceito / substituído por ADR-NNNN.
- **Contexto**: qual problema/situação motivou a decisão.
- **Decisão**: o que foi decidido, em uma frase direta.
- **Consequências**: o que melhora, o que piora/vira trade-off, o que fica pendente.

Nunca editar um ADR aceito pra mudar a decisão — se a decisão mudou, criar um novo ADR marcando o antigo como "substituído por".

## Índice

- [0001 — Corrigir colisão de alias Q3/Q4/Q5 em VW_NOTAS_31](0001-corrigir-colisao-alias-vw-notas-31.md)
- [0002 — Refatorar VW_NOTAS_31 (rev. 3) com MATERIALIZE e novas CTEs de devolução](0002-refatorar-vw-notas-31-rev3.md)
- [0003 — Remover CLAUDE.md e mover skills/ para a raiz do repositório](0003-remover-claude-md-e-mover-skills-para-raiz.md)
