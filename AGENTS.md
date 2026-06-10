# Проект cheque

## Описание

Python-проект для работы с кассовым оборудованием Штрих.

## Путь проекта

`d:\PythonProject\cheque\`

## Связанный проект

`d:\PythonProject\honest_sign\`

## Важные правила

- Предпочитать REST API, если есть выбор между REST и Protobuf.
- Не трогать реальные токены, ключи и `.env`.
- Перед изменениями в протоколе обмена объяснять возможные риски.
- Проверять обработку ошибок устройства, таймауты, повторные запросы и логирование.

<!-- ontoindex:start -->
# OntoIndex — Code Intelligence

This project is indexed by OntoIndex as **cheque** (1169 symbols, 2264 relationships, 102 execution flows). Use the OntoIndex MCP tools to understand code, assess impact, and navigate safely.

> If any OntoIndex tool warns the index is stale, coordinate first; exactly one process should run `ontoindex analyze`.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `ontoindex_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `ontoindex_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `ontoindex_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `ontoindex_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `ontoindex_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `ontoindex_rename` which understands the call graph.
- NEVER commit changes without running `ontoindex_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `ontoindex://repo/cheque/context` | Codebase overview, check index freshness |
| `ontoindex://repo/cheque/clusters` | All functional areas |
| `ontoindex://repo/cheque/processes` | All execution flows |
| `ontoindex://repo/cheque/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/ontoindex/ontoindex-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/ontoindex/ontoindex-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/ontoindex/ontoindex-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/ontoindex/ontoindex-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/ontoindex/ontoindex-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/ontoindex/ontoindex-cli/SKILL.md` |

<!-- ontoindex:end -->

- Перед изменениями бизнес логике, протоколах обмена, обработке ошибок и кассовых интеграциях использовать 
OntoIndex/Continuum для поиска связанных символов и анализа влияния
- для рефакторинга сначала проверять call graph и места вызова
- после изменений запускать подходящие проверки pytest, py_compile. rumm/mypy если настроены 
- 