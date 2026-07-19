# CLAUDE.md

Project instructions for this Python codebase. These complement the global
`~/.claude/CLAUDE.md`; where the global file is general, this one is concrete for this
repository. Read both.

## What this project is

A Python application built on **hexagonal architecture** with the dependency rule
**machine-enforced** (import-linter) and a typed composition root for wiring. The package
lives under `src/app/` — rename `app` to the real package when you start a project (see
"Renaming the package" below).

## Package management — uv, always

- Use `uv` for everything. Never `pip install` into the environment by hand.
- Keep the three dependency tiers cleanly separated in `pyproject.toml`:
  - **`[project].dependencies`** — needed for every normal run of the app.
  - **`[project.optional-dependencies]`** (extras) — needed only when a specific adapter
    is selected. One extra per adapter. The user decides whether to install it. An
    adapter whose extra is absent must fail loudly at startup naming the extra, never
    with a bare `ImportError` at first use (see `application/errors.py:MissingDependencyError`).
  - **`[dependency-groups].dev`** — needed only for development (tests, linters, types).
- Commit `uv.lock`. Common flows: `uv sync` (dev), `uv sync --no-dev` (runtime only),
  `uv sync --all-extras`, `uv run <cmd>`.

## Architecture — the rules are not suggestions

Four layers under `src/app/`, plus a composition root that is **not** a layer:

```
domain/         entities, value objects, domain errors. Pure Python — no third party.
application/    dtos/  ports/  usecases/  + application errors. Depends only on domain.
infrastructure/ adapters implementing ports. Depends on application + domain.
presentation/   settings, runners, edges (CLI/HTTP/worker). Depends on application + domain.
composition/    the object graph + entrypoints. The ONLY place that names a concrete adapter.
```

The dependency rule (imports flow inward only):

- `domain` imports nothing from other layers and **no third-party runtime dependency**.
- `application` → `domain` only.
- `infrastructure` → `application`, `domain`.
- `presentation` → `application`, `domain` — **never `infrastructure`**.
- `composition` → everything; nothing imports `composition` in return.
- `presentation` and `infrastructure` are independent siblings — neither imports the
  other. That is what forces adapter selection into the composition root.

All of the above is checked by `make arch` (import-linter) and by the tests under
`tests/architecture/`. **Do not weaken a contract to make code fit; change the code.**

## Conventions — one artifact per file, named by role

- Ports: one per file under `application/ports/`, `*_port.py`, one `Protocol` each.
- Adapters: one per file under `infrastructure/`, `*_adapter.py`, one class each.
- DTOs: one per file under `application/dtos/`, `*_input.py` (toward the core) or
  `*_output.py` (away from it).
- Use cases: one per file under `application/usecases/`, `*_usecase.py`, one class each.
- Entities/value objects: one per file under `domain/`.

`tests/architecture/test_naming_conventions.py` enforces these. Breaking one fails CI.

## Wiring — the composition root

- Use cases receive their collaborators as **ports through the constructor**. They never
  construct an adapter, read settings, or locate a service. That is what makes them
  unit-testable with a fake and no container.
- Bindings live in a `Container` subclass in `composition/`. Each `@provider` method is
  annotated with the **port** (or use case) it supplies — never a concrete adapter type;
  mypy checks it. Providers are lazy and cached (singleton per container).
- Adding a binding is one provider method. There is no central registration table.
- Selecting between implementations is a **named value in settings**
  (`APP_REPOSITORY_BACKEND=memory|jsonfile`), mapped to an adapter in the container. An
  unknown name fails at startup with the valid names, never defaults silently.

## Simplicity & comments

Follow the global rules: DRY, keep it simple, and comment sparingly. Comments here earn
their place by explaining **why** a non-obvious decision was made — not by narrating what
the code does. If an AI reader wouldn't need it, delete it.

## Verify before you claim done

`make check` = lint + typecheck + arch + unit tests. Run it. Also available:
`make format`, `make coverage` (domain+application gated at 90%), `make test`.

## Commits

I am the author; you are co-author with a stable co-author identity.

## Renaming the package

`app` is a placeholder. To adopt: rename `src/app/` → `src/<yourpkg>/`, then replace the
identifier `app` in `pyproject.toml` (`[project].name`, `[project.scripts]`,
`[tool.hatch...]`, every `[tool.importlinter]` contract), in `tests/architecture/*`, and
in the `from app...` imports. `make arch` and `make check` will tell you if you missed a
spot.
