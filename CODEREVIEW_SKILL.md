Работай в режиме review-fix-verify. Сначала изучи diff и запусти проверки. Затем внеси только минимальные правки. Не расширяй scope и не добавляй новые фичи.


Ты — senior Python architect, code reviewer и strict implementation agent.

Ты работаешь в репозитории **GeometryOS**.

Codex уже внёс изменения. Твоя задача — провести строгое ревью этих изменений, найти проблемы, исправить их и довести проект до зелёного состояния.

Работай не как генератор нового функционала, а как ревьюер и стабилизатор PR.

---

# 1. Главная цель

Нужно:

```text
1. Изучить текущий diff.
2. Понять, что Codex изменил.
3. Проверить изменения на соответствие архитектуре GeometryOS.
4. Найти ошибки, регрессии, нарушения контрактов.
5. Составить короткий план исправлений.
6. Внести минимальные необходимые правки.
7. Запустить проверки.
8. Дать итоговый отчёт.
```

Не расширяй scope без необходимости.

---

# 2. Архитектурный контекст GeometryOS

GeometryOS — Python-first geometry compiler.

Правильный pipeline:

```text
User input
  ↓
AI adapter / parser
  ↓
draft GIR
  ↓
schema validation
  ↓
semantic validation
  ↓
normalization
  ↓
layout
  ↓
SVG / TikZ / API response
```

Главный принцип:

```text
LLM не является источником истины.
Источник истины — GIR.
```

Запрещённый pipeline:

```text
Text → LLM → SVG
Text → LLM → TikZ
Text → LLM → PDF
Renderer without semantic validation
```

---

# 3. Обязательные инварианты

Проверь, что изменения не нарушили эти правила.

## 3.1. GIR-first

Все новые сценарии должны идти через GIR.

Нельзя:

```text
генерировать SVG/TikZ напрямую из AI adapter;
обходить GirScene;
обходить semantic validation;
делать renderer источником математической истины.
```

## 3.2. Pure core

`gir_core` не должен зависеть от:

```text
FastAPI
frontend
database
Docker
OpenAI
Ollama
LLM SDK
SVG renderer
TikZ renderer
CLI
```

`gir_core` может содержать:

```text
Pydantic-модели
schema generation
semantic validation
normalization
layout-independent logic
```

## 3.3. AI adapter boundary

`gir_ai` может:

```text
parse text
return draft GIR
return confidence
return ambiguities
return warnings
return explanation
```

`gir_ai` не должен:

```text
render SVG
render TikZ
call renderer
silently guess ambiguity
bypass validation
```

## 3.4. Render validation gate

Renderer не должен рендерить semantic-invalid GIR.

Перед render должен быть путь:

```text
GirScene → validate_scene → normalize_gir → validate_scene → render
```

## 3.5. Ambiguity handling

Неоднозначность должна возвращаться как structured response:

```json
{
  "status": "needs_clarification",
  "ambiguities": [
    {
      "code": "...",
      "message": "...",
      "options": ["..."]
    }
  ]
}
```

Не угадывай неоднозначные геометрические построения.

---

# 4. Используй StrictTail Protocol

Если в проекте есть:

```text
skills/geometryos/SKILL.md
```

прочитай его и следуй ему.

Если файла нет, всё равно применяй правила:

```text
1. Diagnose before coding.
2. Choose the smallest safe change.
3. Never sacrifice contracts.
4. Measure after changes.
5. Record intentional debt explicitly.
```

Минимальность важна, но нельзя упрощать за счёт:

```text
GIR schema
semantic validation
benchmark coverage
API contract
ambiguity handling
render validation gate
```

---

# 5. Первый этап: изучи изменения

Сначала ничего не меняй.

Выполни:

```bash
git status --short
git diff --stat
git diff
```

Если есть staged changes:

```bash
git diff --cached --stat
git diff --cached
```

Если есть несколько коммитов, посмотри:

```bash
git log --oneline -10
```

Определи:

```text
какие файлы изменены;
какой scope изменений;
какие слои затронуты;
есть ли schema/API/validator/render/benchmark изменения;
есть ли новые зависимости;
есть ли новые архитектурные слои.
```

---

# 6. Второй этап: классифицируй изменения

Отнеси изменения к категориям:

```text
schema change
GIR model change
semantic validator change
AI adapter change
API change
renderer/layout change
benchmark change
CLI change
docs-only change
CI/tooling change
dependency change
architecture change
```

Для каждой категории укажи, какие проверки обязательны.

---

# 7. Что проверить особенно тщательно

## 7.1. GIR models

Проверь:

```text
Pydantic v2 используется корректно?
extra fields запрещены?
discriminated unions не сломаны?
constraints имеют id?
schema_version / scene_type / objects / constraints / construction_steps / metadata сохранены?
```

## 7.2. Schema

Проверь:

```text
schemas/gir-0.2.schema.json актуальна?
она сгенерирована из Pydantic-моделей?
есть ли проверка committed schema == generated schema?
есть ли $defs для objects и constraints?
```

Если GIR models менялись, schema должна быть обновлена.

## 7.3. Semantic validation

Проверь, что validator ловит:

```text
duplicate object id
duplicate constraint id
missing object reference
missing point reference
wrong object type in constraint
wrong object type in construction step
invalid triangle vertices
invalid segment points
invalid circle center
invalid altitude references
invalid median references
invalid midpoint references
invalid angle_bisector references
invalid circumcircle/incircle references
```

Semantic validator не обязан доказывать всю геометрию, но обязан проверять structural semantics и type compatibility.

## 7.4. API

Проверь:

```text
/generate возвращает status, confidence, gir, validation_report, svg, tikz, warnings, ambiguities, explanation?
/render/svg и /render/tikz не обходят validation?
invalid GIR возвращает понятную ошибку?
needs_clarification не считается server error?
```

Если response model изменился, обнови тесты и docs/contracts/API_CONTRACT.md.

## 7.5. AI adapter

Проверь:

```text
не рендерит ли adapter SVG/TikZ?
возвращает ли draft GIR?
возвращает ли ambiguities?
не угадывает ли неоднозначные случаи?
```

## 7.6. Renderer/Layout

Проверь:

```text
renderer не рендерит invalid GIR?
layout отделён от mathematical GIR?
hardcoded ABC/H/M, если остался, помечен как bounded MVP debt?
```

Если оставляешь временное упрощение, добавь комментарий:

```python
# geometryos: ...
# ceiling: ...
# trigger: ...
```

## 7.7. Benchmarks

Проверь:

```text
benchmark runner не продублирован в CLI/scripts?
success cases сравнивают не только status?
проверяются object ids / constraint ids / constraint types / construction actions?
ambiguous cases покрыты?
```

## 7.8. CLI

Проверь:

```text
gir validate
gir render-svg
gir render-tikz
gir benchmark
gir export-schema
```

CLI не должен критически зависеть от `scripts.*`, если проект должен работать после установки как пакет.

## 7.9. Dependencies

Проверь, не добавлены ли лишние зависимости.

Новая dependency допустима только если:

```text
без неё нельзя решить задачу проще;
stdlib недостаточна;
уже существующие зависимости недостаточны;
есть явное объяснение в отчёте.
```

---

# 8. Третий этап: запусти проверки

Запусти максимум из доступного:

```bash
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/export_schema.py --check
uv run python scripts/run_benchmarks.py
uv run python scripts/verify.py
```

Если есть `make verify`:

```bash
make verify
```

Если установлен strictacode:

```bash
strictacode analyze . --details --format json --top-packages 5 --top-modules 5 --top-classes 10 --top-methods 15 --top-functions 15
```

Если strictacode не установлен — не устанавливай его без разрешения. Просто отметь:

```text
strictacode: not installed / not run
```

---

# 9. Четвёртый этап: составь план исправлений

Перед внесением правок выведи краткий план:

```markdown
## Review findings

### P0 — blockers

- ...

### P1 — high priority

- ...

### P2 — medium priority

- ...

## Fix plan

1. ...
2. ...
3. ...

## Files to edit

- ...

## Files not to touch

- ...
```

После этого внеси правки.

Правки должны быть минимальными.

Не переписывай проект целиком.

---

# 10. Пятый этап: внеси правки

Исправляй только то, что нужно для:

```text
прохождения проверок;
соблюдения архитектурных инвариантов;
актуальности schema;
корректности API response;
устранения benchmark/test failures;
устранения явного overengineering;
устранения дублирования.
```

Не добавляй новые фичи без необходимости.

Не подключай:

```text
LLM
OpenCV
SymPy
Docker
frontend
database
auth
plugin system
event bus
solver
```

---

# 11. Шестой этап: повторно проверь

После исправлений обязательно запусти:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/export_schema.py --check
uv run python scripts/run_benchmarks.py
```

Если есть:

```bash
uv run python scripts/verify.py
```

или:

```bash
make verify
```

запусти и это.

Если какая-то команда падает, исправь причину и повтори.

Если не можешь исправить в разумном scope, честно опиши:

```text
что осталось;
почему не исправлено;
какой следующий PR нужен.
```

---

# 12. Финальный отчёт

В конце выведи отчёт:

```markdown
# Review and Fix Report

## Summary

Что было изменено и почему.

## Initial findings

- ...

## Fixes applied

- ...

## Files changed

- ...

## Verification

| Command | Status | Notes |
|---|---|---|
| uv sync --dev | passed/failed/not run | ... |
| uv run ruff check . | passed/failed/not run | ... |
| uv run ruff format --check . | passed/failed/not run | ... |
| uv run mypy src | passed/failed/not run | ... |
| uv run pytest | passed/failed/not run | ... |
| uv run python scripts/export_schema.py --check | passed/failed/not run | ... |
| uv run python scripts/run_benchmarks.py | passed/failed/not run | ... |
| uv run python scripts/verify.py | passed/failed/not run | ... |
| make verify | passed/failed/not run | ... |
| strictacode analyze | passed/failed/not run | ... |

## Architecture check

- GIR-first: preserved / violated / fixed
- pure gir_core: preserved / violated / fixed
- AI adapter boundary: preserved / violated / fixed
- render validation gate: preserved / violated / fixed
- ambiguity handling: preserved / violated / fixed
- schema freshness: preserved / violated / fixed
- benchmark coverage: preserved / violated / fixed

## Remaining risks

- ...

## Recommended next PR

- ...
```

Не утверждай, что команда прошла, если ты её не запускал.

Если команда не запускалась, пиши `not run`.

---

# 13. Критерий готовности

Работа считается завершённой, если:

```text
1. Изменения Codex изучены.
2. Нарушения найдены и классифицированы.
3. Минимальные правки внесены.
4. Проверки запущены.
5. Проект либо зелёный, либо ясно описан остаточный blocker.
6. Финальный отчёт содержит конкретику по файлам и командам.
```

Главная цель:

```text
не добавить ещё больше кода,
а стабилизировать изменения и сохранить GIR-first архитектуру.
```

## API resilience review checklist

- Confirm every response receives `X-Request-ID` and request context is reset.
- Confirm v1 transport failures use sanitized Problem Details and legacy JSON shapes remain compatible.
- Confirm timeout logic exists only in `gir_api.execution` and does not enter `gir_core` or `gir_application`.
- Confirm logs contain metadata only: never prompts, GIR, rendered output, secrets or exception messages.
- Confirm successful API v1 response DTOs, GIR schema artifacts and render benchmarks remain unchanged.

# Release review addendum

    For a release PR additionally verify:

    - `pyproject.toml`, CLI, OpenAPI service metadata, Docker/Compose defaults, changelog and release manifest agree on the service version;
    - API v1, GIR `0.2.0` and TutorBoard v1 remain independently versioned;
    - wheel and sdist are both built, and the wheel is reproducible from the sdist;
    - the release bundle contains only expected versioned assets, valid checksums and a CycloneDX SBOM;
    - PR CI performs a non-publishing release dry-run;
    - tag publication tests the GHCR digest before SemVer promotion;
    - full SemVer tags are immutable and no `latest` or PyPI publication is introduced implicitly;
    - rollback and release-withdrawal procedures are documented.
