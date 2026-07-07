# Como contribuir

Qualquer mudança neste repositório tem **impacto real em dado de negócio usado pra decisão** (margem por fruta/semana que alimenta o painel de BI). Trate este repositório com o mesmo rigor de um sistema em produção, não como um repositório de rascunho.

## Regra de ouro (não negociável)

Toda proposta de mudança num objeto que alimenta o BI de margem deve mirar **resultado idêntico** para qualquer conjunto de dados, a menos que a mudança seja explicitamente uma correção funcional (e nesse caso, isso deve estar destacado, não escondido dentro de uma "otimização").

- Se a equivalência não é 100% garantível só analisando o texto/SQL → marcar `[VALIDAR]` e descrever o risco.
- Antes de qualquer mudança ser tratada como "concluída" e ir para produção: **reconciliar** contra produção (por ANO/SEMANA/FRUTA, ou a granularidade equivalente) as métricas que a mudança toca — não é opcional quando o campo alimenta desconto/custo/margem.
- Nunca "corrigir" silenciosamente um ponto crítico conhecido (ver `ARCHITECTURE.md`) sem sinalizar explicitamente o que mudou de comportamento — isso é produção, não refactor de brincadeira.
- Qualquer alegação de performance ("ficou mais rápido", "gargalo é X") deve vir de medição real (`v$sql`, `EXPLAIN PLAN`, `DBA_TAB_STATISTICS`) — nunca números ou percentuais inventados.

## Tags usadas na documentação

- `[EXTERNO]` — dependência citada mas cujo corpo ainda não foi trazido para `sql/`. Lista consolidada de pendências no final de `docs/STACK_MARGEM_BI.md`.
- `[VALIDAR]` — mudança proposta (ou inconsistência encontrada) cuja equivalência/causa **não é garantível só pelo texto**. Descrever o risco em vez de recomendar/assumir às cegas.
- `✅ Confirmado` vs `⚠️ Pendência` — usado no `CHANGELOG.md` para distinguir o que foi **medido/evidenciado** do que ainda não foi. Nunca promover uma pendência a confirmado sem medição real.

## Regra obrigatória de documentação

Toda alteração em `sql/` → atualizar a seção correspondente em `docs/STACK_MARGEM_BI.md`, sempre com as mesmas 13 partes, nesta ordem:

1. Resumo
2. Fluxo de execução
3. Entradas
4. Saídas
5. Regras de negócio
6. Cálculos
7. Dependências
8. Objetos chamados
9. Objetos que provavelmente dependem deste objeto
10. Diagrama textual de dependências
11. Pontos críticos
12. Sugestões de melhoria
13. Resumo executivo (para analista funcional)

Depois de documentar, registrar uma entrada datada no `CHANGELOG.md`. Sem exceção — um `.sql`/`.txt` em `sql/` sem a seção correspondente em `docs/` é documentação desatualizada.

Passo a passo completo (como localizar o objeto no Sankhya, extrair o corpo, salvar, documentar e atualizar referências cruzadas): `skills/trazer-documentar-objeto/SKILL.md`.

## Antes de mexer em algo que alimenta o BI

Checklist obrigatório: `skills/bi-impact-check/SKILL.md`. Cobre: mapear o raio de impacto, classificar a mudança (correção funcional vs. otimização vs. automação nova), provar equivalência ou marcar `[VALIDAR]`, reconciliar antes de considerar concluído, nunca corrigir silenciosamente um ponto crítico conhecido, documentar e versionar.

## Decisões arquiteturais

Decisões técnicas relevantes (com contexto, alternativas consideradas e consequências) ficam em `docs/adr/` — um arquivo por decisão, numerado sequencialmente. Ver `docs/adr/README.md` para o formato.

## Convenção de commit

`tipo(#N): descrição` — `N` = número real da issue em `github.com/GrupoArgoFruta/BI-ArgoFruta`. Sem issue aberta, usar `tipo: descrição`.

Tipos: `feat`, `fix`, `docs`, `refactor`, `perf`, `infra`, `tech-debt`.

## Releases

Como não existe um "número de versão" de aplicativo aqui (é uma stack de dados), usar **tags de data** (`vAAAA.MM.DD`) no GitHub quando um lote de mudanças em `sql/`+`docs/` for publicado em produção. A release note deve conter o resumo de reconciliação (o que foi comparado, resultado) — o mesmo formato já usado no `CHANGELOG.md`.

## Ownership de commit e git

- Quem commita é o usuário, sempre.
- Nunca mexer em `git config` (o usuário alterna entre conta pessoal e conta da empresa manualmente conforme o repositório) — nem para leitura.
- Remoto: `https://github.com/GrupoArgoFruta/BI-ArgoFruta.git` (org da empresa).

## Automação que impacta dado de BI

Antes de criar/alterar qualquer script, pipeline ou automação que leia ou escreva num objeto desta stack (atual ou futura, GCP), seguir o checklist de `skills/bi-impact-check/SKILL.md`.
