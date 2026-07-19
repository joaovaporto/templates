# Python — Hexagonal Architecture Template

A starting point for a Python project with **hexagonal architecture**, a **machine-checked
dependency rule**, a **typed composition root**, and **clean dependency tiers** (core /
extras / dev) managed with `uv`.

Distilled from a real project whose architecture is enforced by tests rather than
discipline. Out of the box, `make check` passes — the enforcement is live, not aspirational.

## Layout

```
src/app/
├── domain/           # entities, value objects, errors — pure Python, zero third party
│   ├── entities/note.py
│   ├── value_objects/title.py
│   └── errors.py
├── application/       # the core's logic; depends only on domain
│   ├── dtos/          # *_input.py (toward the core) / *_output.py (away from it)
│   ├── ports/         # *_port.py — one Protocol each, the seams
│   ├── usecases/      # *_usecase.py — one class each, collaborators injected
│   └── errors.py
├── infrastructure/    # *_adapter.py — implements ports; depends on application + domain
│   ├── memory/        # default backend, no extra
│   └── jsonfile/      # optional backend behind the `jsonfile` extra
├── presentation/      # settings, runner, edges — NEVER imports infrastructure
└── composition/       # the object graph + entrypoint — the only place naming an adapter
    ├── provider.py    # tiny typed DI container: lazy, cached, infers bindings from return types
    ├── container.py
    └── main.py

tests/
├── architecture/      # the dependency rule + naming conventions, run in-suite
├── unit/              # use cases against fakes — no container, no I/O
└── fakes/
```

## The dependency rule (enforced by `make arch`)

Imports flow inward only. `domain` → nothing; `application` → `domain`; `infrastructure`
→ `application`+`domain`; `presentation` → `application`+`domain` (**never**
`infrastructure`); `composition` → everything, and nothing imports it back. `presentation`
and `infrastructure` are independent siblings, which is what forces adapter selection into
the composition root. See the contracts in `pyproject.toml` under `[tool.importlinter]`.

## Dependency tiers (`uv`)

- **core** (`[project].dependencies`): every run needs these.
- **extras** (`[project.optional-dependencies]`): one per optional adapter; the user
  chooses. Selecting an adapter whose extra is missing fails at startup naming the extra.
- **dev** (`[dependency-groups].dev`): tests, linters, types.

## Quick start

```bash
uv sync                 # dev environment (core + dev group)
make check              # lint + typecheck + arch + unit tests
uv run app              # run the demo entrypoint (in-memory backend)

# try the optional backend:
uv sync --extra jsonfile
APP_REPOSITORY_BACKEND=jsonfile uv run app
```

## Make targets

`install` · `install-dev` · `install-all` · `lint` · `format` · `typecheck` · `arch` ·
`test` · `test-unit` · `coverage` · `check` · `clean` — run `make help`.

## Adopting it

`app` is a placeholder package name. See **Renaming the package** in `CLAUDE.md` for the
exact edits; `make arch` and `make check` catch anything you miss.
