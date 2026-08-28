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

Four layers under `src/app/`, with the composition root as one module inside the layer
that starts the system:

```
domain/         entities, value objects, domain errors. Pure Python — no third party.
application/    dtos/  ports/  usecases/  + application errors. Depends only on domain.
infrastructure/ adapters implementing ports. Depends on application + domain.
presentation/   settings, runners, edges (CLI/HTTP/worker) — never names an adapter.
  └ composition/  the resolver + entrypoints. The ONLY module that may name one.
```

Presentation is the system's natural entry point, so the wiring lives there — **as one
module, not spread through the layer**. Every other presentation module stays barred from
`infrastructure`.

The dependency rule (imports flow inward only):

- `domain` imports nothing from other layers and **no third-party runtime dependency**.
- `application` → `domain` only.
- `infrastructure` → `application`, `domain`.
- `presentation` → `application`, `domain` — **never `infrastructure`**.
- `presentation.composition` → everything; it is the single exception, declared as an
  `ignore_imports` on the contract so the exemption is visible rather than assumed.
- An edge may hold the resolver and ask it for a use case; it may never name the adapter
  behind one. The same split runs through the tests: `TestEdgeLookups` exempts
  `composition/` for the same reason the contract does.

All of the above is checked by `make arch` (import-linter) and by the tests under
`tests/architecture/`. **Do not weaken a contract to make code fit; change the code.**

## Conventions — one artifact per file, named by role

- Ports: one per file under `application/ports/`, `*_port.py`, one `Protocol` each.
- Adapters: one per file under `infrastructure/`, `*_adapter.py`, one class each.
- DTOs: one per file under `application/dtos/`, `*_input_dto.py` (toward the core) or
  `*_output_dto.py` (away from it), one `*Dto` class each.
- Use cases: one per file under `application/usecases/`, `*_usecase.py`, one class each.
- Entities/value objects: one per file under `domain/`.

`tests/architecture/test_naming_conventions.py` enforces these. Breaking one fails CI.

## Wiring — the composition root

- Use cases receive their collaborators as **ports through the constructor**. They never
  construct an adapter, read settings, or locate a service. That is what makes them
  unit-testable with a fake and no resolver.
- `resolver.get(SomeUseCase)` reads that constructor and supplies every parameter.
  It is typed (a class in, an instance of that class out), lazy, and each type is built
  once per resolver. **Adding a use case costs no wiring** — there is nothing to register.
- **The composition root builds the edges and hands each one the resolver.** An edge that
  fans out asks for each use case where it uses it, so its constructor does not grow; an
  edge that drives a single use case should take it through the constructor instead.
- The conventions the resolver reads:

  | step | rule | example |
  |---|---|---|
  | port | a `*Port` Protocol in `application/ports/` | `NoteRepositoryPort` |
  | core | the port name minus `Port`, snake_cased | `note_repository` |
  | backend | settings field `<core>_backend` = a subpackage of `infrastructure/` | `APP_NOTE_REPOSITORY_BACKEND=jsonfile` |
  | module | in that subpackage, the one stem ending `_<core>_adapter` | `jsonfile/orjson_note_repository_adapter.py` |
  | class | the one `*Adapter` class in that module | `OrjsonNoteRepositoryAdapter` |
  | arguments | non-port parameters read `<backend>_<param>` from settings | `path: Path` ← `APP_JSONFILE_PATH` |
  | scoped argument | when one backend serves two ports, `<core>_<backend>_<param>` wins over the plain field | `APP_NOTE_REPOSITORY_JSONFILE_PATH` |

  **The tree is flat where resolution looks.** A port lives directly in
  `application/ports/`, and an adapter directly in `infrastructure/<backend>/` — one level
  down and no deeper. Resolution lists a single directory rather than walking a tree, so
  anything nested is invisible to it; `test_naming_conventions.py` fails on nesting rather
  than letting it fail silently at runtime.

- **Adding an adapter costs one file**: `infrastructure/<backend>/<library>_<core>_adapter.py`
  with one `*Adapter` class. It is found by the module's *stem*, so the class keeps the
  name of whatever it wraps.
- **A settings field appears only when there is a real choice.** A port with one
  implementation needs none; the moment a second exists, `test_naming_conventions.py`
  fails until you add `<core>_backend`. Do not add the field pre-emptively.
- **`@provider` is the escape hatch, not the norm.** A `Resolver` declares no bindings.
  Subclass it and add a method only where names cannot express one, annotated with the
  **port** it supplies — never a concrete adapter; an architecture test rejects that. It
  overrides the convention for its type, and stays lazy and cached.
- **When an adapter needs something the conventions cannot supply, the value enters through
  the resolver — never through the port.** In order of preference:
  1. *A scalar the edge computes at startup is still a setting.* `Settings` lives in
     `presentation/` and takes explicit values, so
     `Settings(postgres_pool_size=workers() * 2)` feeds `PostgresNoteRepositoryAdapter(pool_size: int)`
     by the ordinary `<backend>_<param>` rule. **No provider.**

     *An argument is named after the backend, not the port*, so every Postgres adapter
     shares one `postgres_dsn`. That is the point, and the default. Only when a single
     backend implements two ports whose adapters take an argument of the same name does
     the plain field become ambiguous — then name the field `<core>_<backend>_<param>`,
     which the resolver reads in preference. **Declaring the scoped field is what selects
     it**, not the value it holds, so it wins even left at its default and the plain field
     stops feeding that adapter. Scope the one argument that collides, not the rest.
  2. *A live object* — an open pool, an HTTP client, a channel — cannot be a settings
     field. Give a `Resolver` subclass a constructor parameter for it and one `@provider`
     returning the port that uses it:

     ```python
     class AppResolver(Resolver[Settings]):
         def __init__(self, settings: Settings, pool: ConnectionPool) -> None:
             super().__init__(settings)
             self.pool = pool

         @provider
         def note_repository(self) -> NoteRepositoryPort:
             return PostgresNoteRepositoryAdapter(pool=self.pool)
     ```

     **The use cases do not change.** A provider is keyed by the type it *returns*, so
     everything depending on that port receives the object, and the whole graph still comes
     from `resolver.get(SomeUseCase)`.
- **The only thing that forces a `@provider` for a use case** is an argument in that use
  case's *own* constructor which is neither a port nor a settings field. An awkward
  argument on an adapter never propagates to its consumers — the port is where it stops.
- **An error belongs to the layer that raises it.** `ConfigurationError` is composition's
  (the wiring is wrong), `MissingDependencyError` is infrastructure's (an extra is
  missing), and `application/errors.py` holds only what the core itself raises or catches.
  An error class that no layer but another one uses does not belong to the layer it sits in.
- **Nothing guesses, and nothing defaults silently.** An unknown backend fails at startup
  listing the packages that exist; every other failure names the file, settings field, or
  env var that would fix it, and carries the chain of types it was resolving.
- **Composition does wiring between layers, and nothing else. Session and connection
  management is not its job.** A pool or session shared by every Postgres adapter belongs
  in `infrastructure/`, resolved inside that layer: the resolver builds
  `PostgresNoteRepositoryAdapter`, and the adapter obtains its connection itself, so the
  use case and the edge never hear of one. Connection or transaction handling that is
  genuinely the edge's concern belongs in `presentation/`. **That is why there is no scope
  machinery here, and why none should be added** — a request lifetime is a concern of the
  layer that owns the resource, not of the wiring.
- A resolver caches what it builds, so its own lifetime is its objects' lifetime: one per
  process shares them, one per request does not.
- **Resolving in a method defers a wiring failure to first use**, since building the edge
  does not touch its use cases. `test_wiring_resolves` is what catches it in CI.
- **The suite is the compiler for the wiring.** No module names an adapter statically, so
  `tests/architecture/test_wiring_resolves.py` builds every use case on every backend.
  **Do not skip it**, and run `make test-all` (or CI) so no backend is skipped for a
  missing extra. `make explain` prints what the current settings resolve to.
- For an application that wants config fully validated before anything is constructed,
  type the field as `Literal["memory", "jsonfile"]`: the failure moves into `Settings()`
  and you get editor completion, at the cost of re-hardcoding the list.

## Simplicity & comments

Follow the global rules: DRY, keep it simple, and comment sparingly. A comment earns its
place only by generating useful documentation, or by clarifying something an AI reader
could not work out from the code itself. **Comments are not a record of how the codebase
got here** — decisions, alternatives, and rationale belong in `openspec/`, not in a
docstring. If an AI reader wouldn't need it, delete it.

## Types and tooling

- mypy runs `--strict` and the tree carries **zero** `type: ignore`. Keep it that way. The
  one construct that needs an ignore is `resolver.get(SomePort)` — mypy rejects a
  Protocol where `type[T]` is expected — spelled `# type: ignore[type-abstract]`. It is a
  named code, and `warn_unused_ignores` will retire it if it stops being needed.
- Protocol detection reads the private `_is_protocol`; switch to `typing.is_protocol` when
  the floor moves to 3.13 (`conventions.is_port` is the only place).
- ruff runs in pre-commit from the dev environment, so `uv.lock` is the only place its
  version is pinned. Bump it with `uv lock --upgrade-package ruff` — `pre-commit
  autoupdate` no longer touches it.

## Verify before you claim done

`make check` = lint + typecheck + arch + unit tests. Run it. Also available:
`make format`, `make coverage` (domain+application gated at 90%), `make test`,
`make test-all` (every extra installed — what CI should run), `make explain`.

## Commits

Human is the author; AI-agent is co-author with a stable co-author identity.

## Renaming the package

`app` is a placeholder. To adopt: rename `src/app/` → `src/<yourpkg>/`, then replace the
identifier `app` in `pyproject.toml` (`[project].name`, `[project.scripts]`,
`[tool.hatch...]`, every `[tool.importlinter]` contract), in `tests/*`, and in the
`from app...` imports. **`composition/` needs no edit** — the resolver derives its
package name from its own module. `make arch` and `make check` will tell you if you
missed a spot.
