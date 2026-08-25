## Why

The template wires its object graph with one `@provider` method per binding, so the
composition root grows a method for every use case added, and every edge names each use
case it drives in its constructor. Both are boilerplate a naming convention could derive.
The alternative usually reached for — resolving everything by guessing from settings
values, keyed by strings, with a session threaded through the lookup — trades that
boilerplate for a system nobody can debug.

This change takes the middle: **convention over boilerplate, without giving up types,
determinism, or clear failures.**

## What Changes

- **A resolver builds any application object from its constructor annotations.**
  `resolver.get(SaveNoteUseCase)` supplies every parameter: a `*Port` becomes the
  adapter the settings select, another class in the package is built the same way, and
  anything else is read from settings. Adding a use case costs **no wiring at all**.

- **Adapter selection is deterministic.** `NoteRepositoryPort` → `note_repository_backend`
  → the `infrastructure/` subpackage of that name → the one module whose stem ends
  `_note_repository_adapter` → its one `*Adapter` class. Nothing else in settings can
  influence the choice. A port with a single implementation needs no settings field; an
  architecture test forces one the moment a second appears.

- **The edge holds the resolver and asks for each use case where it uses it**, so an edge
  that fans out does not grow a constructor parameter per use case. The composition root
  builds each edge and passes the resolver in — one line, in the place whose job is wiring.

- **`@provider` survives as the escape hatch**, for bindings names cannot express: an
  adapter wrapped in a decorator, two ports sharing a client, or a constructor argument
  that is neither a port nor a settings value. A provider is keyed by the type it returns,
  so a use case depending on a provided port needs no provider of its own.

- **Each layer owns the errors it raises.** `ConfigurationError` moves to `composition/`
  and `MissingDependencyError` to `infrastructure/`; `application/errors.py` keeps only
  what the core itself raises or catches.

- **The tree is flat where resolution looks** — a port directly in `application/ports/`,
  an adapter directly in `infrastructure/<backend>/`. Nesting is rejected by a test rather
  than failing silently at runtime.

- **The suite is the compiler.** Because no module names an adapter statically, every use
  case is built against every backend combination in CI, and an edge may resolve only real
  use cases.

- **The composition root moves inside presentation**, as `presentation/composition/` — one
  module, not spread through the layer. Presentation is the system's entry point, so the
  wiring belongs where the call chain starts.

- **BREAKING (contract):** the presentation contract becomes "never names an adapter",
  with `presentation.composition` carved out by an explicit `ignore_imports`. Every other
  presentation module may **never** import `infrastructure`: an edge may ask for a use case
  but can never name the adapter behind one.

- **BREAKING (settings):** `APP_REPOSITORY_BACKEND` → `APP_NOTE_REPOSITORY_BACKEND`; the
  convention derives the name from the port. The `BACKEND_*` constants are deleted as a
  hand-maintained mirror of a directory listing.

- **ruff moves into pre-commit's `local` hooks.** It is already a dev dependency, so
  `uv.lock` becomes the only place its version is pinned.

## Capabilities

### New Capabilities
- `dependency-wiring`: how an application object is resolved — the naming conventions
  mapping a port to an adapter, the typed lookup, provider overrides, how an edge obtains
  what it drives, and what happens when a convention is unmet.
- `dev-tooling`: which quality gates run locally, where each tool is installed from, and
  the single source of truth for their versions.

### Modified Capabilities

None. `openspec/specs/` is empty; both capabilities are new.

## Impact

- `src/app/presentation/composition/` — `resolver.py` (the `Resolver`), `conventions.py` (the naming
  rules), `main.py`. `provider.py` is deleted.
- `src/app/presentation/settings.py` — field renamed to match its port, `jsonfile_path`
  typed `Path`, backend constants removed.
- `src/app/application/dtos/` — `*_input_dto.py` / `*_output_dto.py`, classes suffixed
  `Dto`, so a DTO's filename declares its role like every other artifact's.
- `src/app/presentation/runner.py` — holds the resolver.
- `src/app/application/`, `src/app/infrastructure/` — one added use case, port, and backend
  package, purely to demonstrate that neither costs wiring.
- `tests/` — a wiring smoke test, naming rules tying an adapter to a port, an edge-lookup
  rule, and resolver unit tests including every failure message.
- `pyproject.toml` — the presentation contract narrowed to forbid `infrastructure` only.
- `.pre-commit-config.yaml`, `Makefile`, `CLAUDE.md`, `README.md`, `.env.example`.
- No runtime dependency is added or removed.

## Non-Goals

Deliberately absent, because the purpose is convention over boilerplate and nothing more:
scope and child-resolver machinery, teardown hooks, and injecting the settings object
itself. The first two are not merely unused but misplaced — session and connection
management belongs to the layer that owns the resource, never to the wiring. Shipping any
of them unused would be the boilerplate this change exists to remove.

`explain()` is the one introspection that stays: because no module names an adapter
statically, it is how an operator answers "what is actually wired".
