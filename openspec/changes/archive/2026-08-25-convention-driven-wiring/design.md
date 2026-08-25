## Context

`composition/container.py` today holds one `@provider` method per binding. The decorator is
sound — lazy, cached per container, annotated with the port it supplies so mypy rejects an
adapter leaking into a use case — but writing a method per object is a tax that grows
linearly with the application and produces nothing a naming convention could not derive.

The counter-example that prompted this change is a `dependency_solver.py` from another
project, which removes the boilerplate entirely and pays for it three times over:

```python
def get_use_case(use_case_name: str, settings: AppSettings, session: Any) -> Any:
    ...
    for tech in settings.iter_string_values():
        cls = getattr(infrastructure, f"{tech}{core}Adapter", None)
        if cls is not None:
            return cls.build(settings, session)
```

- `session` is a parameter of the resolver, so request lifetime is part of the wiring API;
- the lookup is stringly-typed and returns `Any`, so the edge loses its types;
- adapter selection *guesses*: any string field in settings may become a tech prefix, so a
  wrong value silently selects a different adapter and a missing one is undiagnosable.

The constraints this template already imposes and that the design must not weaken:
import-linter's layer contracts (`presentation` may never import `infrastructure`, so
adapter selection has to stay in `composition/`), mypy `--strict`, one-artifact-per-file
naming rules already enforced by `tests/architecture/test_naming_conventions.py`, and the
optional-extra rule — selecting a backend whose extra is absent must fail at startup naming
the extra, never with a bare `ImportError`.

## Goals / Non-Goals

**Goals:**

- Adding a use case costs zero lines under `composition/`; adding an adapter costs one file.
- Resolution is deterministic and typed: a class in, an instance of that class out.
- Every failure is a startup error naming the fix — the settings field, the env var, the
  filename to create, the extra to install.
- The laziness and per-container caching of `@provider` survive, now as properties of the
  resolver itself.
- Request lifetime is expressible without appearing in `get()`'s signature.
- The convention is machine-checked, because nothing statically names an adapter any more.

**Non-Goals:**

- A general-purpose DI framework. No scope strings, no qualifiers, no auto-discovery of
  anything outside this package, no third-party container dependency.
- Resolving anything the application does not own. Entities and DTOs are call-time
  arguments, not dependencies, and the resolver refuses them by design.
- Async resolution or async teardown. Nothing in this template is async yet; the scope's
  teardown is synchronous and an async variant is an additive change when it is needed.
- Changing the layer contracts, the naming rules, or the extras model.

## Decisions

### D1 — `Resolver.get(target)` resolves from constructor annotations

`def get[T](self, usecase: type[T]) -> T`. Resolution reads `get_type_hints(target.__init__)`
together with `inspect.signature`, and fills each parameter by the first matching rule:

1. an explicit `@provider` supplies this exact type → call it;
2. the hint is a `*Port` Protocol → select an adapter (D2);
3. the hint is any other class inside this package, excluding `domain/` and
   `application/dtos/` → recurse;
4. otherwise → a settings field named `<prefix>_<param>` (D3);
5. the parameter has a default → leave it to the default;
6. otherwise → `ConfigurationError` naming the parameter, its type, and the env var searched.

Each resolved type is cached on the resolver, so laziness and singleton-sharing are
properties of `get()` rather than of a hand-written method. Rule 4's exclusion of
`domain/` and `application/dtos/` matters: without it a use case taking an input DTO would
send the resolver into pydantic and produce a baffling `TypeError` instead of a sentence.

*Alternative rejected:* keying resolution on a string name. It costs the return type, costs editor navigation, and turns a
rename into a runtime failure. Passing the class costs nothing and keeps mypy in the loop.

### D2 — A port maps to an adapter through the settings field its own name derives

| step | rule | example |
|---|---|---|
| port | `*Port` Protocol in `application/ports/` | `NoteRepositoryPort` |
| core | port name minus `Port`, snake_cased | `note_repository` |
| backend | settings field `<core>_backend`, whose value is a subpackage of `infrastructure/` | `APP_NOTE_REPOSITORY_BACKEND=jsonfile` |
| module | in that subpackage, the one stem ending `_<core>_adapter` | `jsonfile/orjson_note_repository_adapter.py` |
| class | the one `*Adapter` class defined in that module | `OrjsonNoteRepositoryAdapter` |

One field, one candidate, and nothing else in settings can influence the choice — the
opposite of iterating every string value until something resolves.

**Discovery is by module stem, never by class-name prefix.** `memory/` holds
`InMemoryNoteRepositoryAdapter` and `jsonfile/` holds `OrjsonNoteRepositoryAdapter`: the
directory carries the selector, the class name carries which library it wraps. A
class-name-prefix rule would force renames to `MemoryNoteRepositoryAdapter` /
`JsonfileNoteRepositoryAdapter`, destroying that information to satisfy the resolver. The
existing naming test already guarantees exactly one `*Adapter` per `*_adapter.py`, so the
"find the class" half of the lookup is enforced for free.

**A port with exactly one implementation needs no settings field.** If `<core>_backend` is
absent from `Settings`, the resolver lists every backend package for a matching stem;
exactly one is used, zero or two-or-more is an error. This keeps "add an adapter, add
nothing else" true for the common case, and it is safe *only because* of the architecture
test in D6 that fails the moment a second implementation appears without the field. The two
are one decision — remove the test and the shortcut has to go with it.

The listing is done with `importlib.util.find_spec` plus `pkgutil.iter_modules`, which read
package metadata without executing any module. The chosen module alone is then imported.
That is what preserves the extras model: `uv sync` with no extras can still *list* the
jsonfile adapter while never importing `orjson`, and selecting `jsonfile` without the extra
reaches the adapter's constructor, where the existing deferred import raises
`MissingDependencyError` naming the extra — unchanged behaviour.

*Alternative rejected:* keeping `BACKENDS = ("memory", "jsonfile")` in settings for
validation. It is a hand-maintained mirror of a directory listing, i.e. exactly the second
source of truth this change exists to delete. Validation stays crisp because the error
lists the real subpackages.

*Alternative noted, not taken:* typing the field as `Literal["memory", "jsonfile"]`. It
moves the failure into `Settings()` and gives editor completion, but re-hardcodes the list
and breaks "drop in a backend package and it works". It is worth one line in `CLAUDE.md` as
the stricter opt-in for a real application.

### D3 — Scalar arguments come from one settings field, not a search

A non-port, non-class parameter is filled from `settings.<prefix>_<param>`, where `<prefix>`
is the backend package name for an adapter. `OrjsonNoteRepositoryAdapter(path: Path)` in
`jsonfile/` reads `jsonfile_path`. Exactly one candidate name is tried — adding a bare
`<param>` fallback would make `path`, `url`, and `timeout` collide across adapters and would
make every error message list two environment variables instead of one.

The resolver never coerces. `Settings.jsonfile_path` is declared `Path` and pydantic does
the conversion, so an invalid value fails in settings validation where it belongs. A settings
value whose type does not match the parameter's annotation is reported as a settings problem
naming the field and both types, rather than surfacing inside the adapter.

### D4 — `@provider` is the escape hatch and keeps its guard rail

A `Resolver` declares no bindings. A `@provider` method still binds its return type and now
*overrides* the convention for it — for a decorator around the conventional adapter, two
ports sharing one connection, an adapter built from a hand-made client. Two providers
supplying the same type is an error, and `test_providers_are_typed_to_ports` continues to
reject a provider annotated with an `infrastructure/` class.

No `@provider` is kept in the template as a live demonstration: `Runner`'s dependencies are
fully derivable, so such a method would be precisely the boilerplate this change removes,
and showing the escape hatch where it is not needed teaches the wrong reflex. It is covered
by the class docstring and by a unit test asserting override-beats-convention.

`@provider` is a marker and nothing more — it sets an attribute and returns the method
untouched. An earlier version wrapped the method so that calling it directly went through
the cache, but the index binds the underlying function, so the wrapper was only ever
reached by a call nothing makes. Dropping it also drops a real hazard: `get_type_hints` on
a `@wraps`-ed wrapper resolves against the decorator's module, so a forward-referenced
return annotation would have been read in the wrong namespace.

### D5 — The edge holds the resolver, and nothing sits between them

The composition root builds the edge and passes the resolver in:

```python
Runner(Resolver(settings)).run()
```

so an edge that fans out asks for each use case where it uses it, and its constructor does
not grow. Two earlier drafts put an interface in the middle and both were wrong. The first
declared a `UseCasesPort` in `application/ports/`: the core neither used nor referenced it,
so the core carried an artefact existing only to wire the outer layers — a violation
import-linter cannot see, because the import arrow points inward while the purpose points
outward. The second moved the same Protocol to `presentation/`, which was correct placement
for an unnecessary idea.

What actually changed is the direction of containment: the resolver no longer contains the
edge, the edge contains the resolver. The contract is amended to permit
`presentation -> composition`, and renamed to state the rule that was always doing the
work — **presentation never names an adapter**. `Container` is renamed `Resolver`, since it
no longer contains anything, and the empty `AppContainer` subclass is deleted.

The cost, stated plainly: building an edge no longer touches its use cases, so a
misconfiguration surfaces at first use rather than at startup. D6's suite is what catches
it.

### D5b — What was deliberately not built

Frugality is part of the goal, so the following were removed once they had no user:

- **Scope / child resolvers**, and **`close()` / teardown / the context-manager
  protocol.** Not merely unused — misplaced. Composition's role is to wire layers
  together; session and connection management is not its job. A pool shared by every
  Postgres adapter belongs to `infrastructure/` and is obtained inside that layer, so the
  resolver builds `PostgresNoteRepositoryAdapter` by the ordinary conventions and neither
  the use case nor the edge ever references a session. A transaction boundary that really
  is the edge's concern belongs to `presentation/`. Putting a scope in the composition
  root would move a resource concern into the one place that should hold none, so this is
  a standing decision rather than a deferral.
- **Injecting the settings object itself.** The convention is `<backend>_<param>`; handing
  an adapter the whole settings object contradicts it, and nothing asked for it.

### D6 — The wiring is compiled by the test suite

This design's real cost is stated plainly: static traceability. Today `OrjsonNoteRepositoryAdapter`
is greppable to the container line that builds it; afterwards no module names it. The
mitigation is not documentation, it is tests:

- **`test_wiring_resolves.py`** parametrises every use case in `application/usecases/`, plus
  `Runner`, over the cross product of every declared `*_backend` field's legal values, and
  builds each one. A typo in a filename, a port with no adapter, an unsuppliable parameter —
  all fail here. Backends whose extra is not installed skip with the missing-dependency
  message, so the suite is honest on a core install and exercises the real adapter under
  `uv sync --all-extras`.
- **naming rules** added to `test_naming_conventions.py`: every adapter module stem
  corresponds to an existing port; every port has at least one adapter; a port with two
  backends must declare its `<core>_backend` field; a `*_backend` default must name a real
  package.

`Resolver.explain()` prints `NoteRepositoryPort -> jsonfile -> …` for each port, restoring
the grep affordance the conventions cost. Because D2's selection decides before importing,
it answers even for a backend whose extra is absent, and reports a misconfigured port in
the listing rather than raising.

### D7 — mypy strict, `type[Protocol]`, and where the seam is

mypy rejects passing a Protocol class where `type[T]` is expected (`type-abstract`). It does
not affect the resolver: hints arrive as runtime `type` objects through an intentionally
`Any`-typed private hop, so `get()` stays precise and the loose typing is one method deep
and never visible to a caller. Nothing in `src/` or the tests calls
`get(SomePort)` — the wiring test resolves use cases and pulls ports transitively — so the
result is **zero `# type: ignore` comments**. If a real application ever needs
`resolver.get(SomePort)`, the spelling is `# type: ignore[type-abstract]`, a named code that
strict mode's `warn_unused_ignores` will retire on its own; that is documented rather than
pre-emptively disabled in `pyproject.toml`.

Protocol detection on Python 3.12 reads the private `_is_protocol` attribute — stable since
3.8 and exactly what `typing.is_protocol` reads on 3.13. It is isolated in one predicate with
a comment and a note to switch when the floor moves.

### D7b — The composition root lives inside presentation

Presentation is where the call chain starts, and the wiring is small, so it lives at
`presentation/composition/` — one module, not diluted through the layer.

The cost is exact and worth stating: the contract can no longer prove "presentation never
touches infrastructure" for the layer as a whole, because the wiring module must. It is
narrowed to "never names an adapter, except when wiring", with a single
`ignore_imports = ["app.presentation.composition.* -> app.infrastructure.*"]`. Verified
both ways: an adapter imported from `runner.py` still breaks the contract, and the
`TestEdgeLookups` rule needed the same carve-out, because a `@provider` resolving a port is
legitimate code that the edge rule would otherwise reject.

### D8 — Two modules, and the package name is derived

`composition/` becomes `resolver.py` (the mechanism) and `conventions.py` (the name rules
and their error prose); `provider.py` is deleted, because `@provider` is no longer the
headline API. The split keeps the file a
reader opens to understand *how wiring works* free of the error strings. The container
derives its package name from its own `__module__`, so the "renaming the package" chore in
`CLAUDE.md` does not touch `composition/` at all — and, as a side effect, a test can point a
container at its own module to exercise failure paths against synthetic ports.

### D9 — ruff moves into the local hook block

`ruff` and `ruff-format` move from `astral-sh/ruff-pre-commit` into the existing `local`
repo as `uv run ruff check --force-exclude --fix --exit-non-zero-on-fix` and
`uv run ruff format --force-exclude`, `language: system`, `types_or: [python, pyi]`,
`require_serial: true`, placed **before** mypy so autofixes land before the type check reads
the tree.

Three details carry the weight. Filenames *are* passed (unlike the mypy and import-linter
hooks) because ruff is correct and much faster on a subset, and staged-file semantics are
what a formatter wants. `--force-exclude` is therefore mandatory: with explicit filenames
ruff otherwise ignores the project's `exclude` configuration — it is the flag hand-rolled
versions of this hook forget, and upstream's own hook definition sets it. `require_serial`
matches upstream, since ruff parallelises internally and letting pre-commit fan out only
oversubscribes the CPU.

The gain: one ruff install instead of two, and `uv.lock` as the only place its version is
pinned — the current config pins `rev: v0.9.0` against a lock that installs 0.15.x. The
cost: `pre-commit autoupdate` no longer bumps ruff; `uv lock --upgrade-package ruff` does.
That is the correct place for it, and it is documented in `CLAUDE.md`.

## Risks / Trade-offs

- **Loss of static traceability** → the wiring smoke test (D6) plus `explain()`. The test is
  not optional garnish; without it this change makes the template less safe than it is today.
- **Convention drift as the template is adopted** → every rule the resolver depends on has a
  matching architecture test, and each error message names the exact file, field, or env var
  that would satisfy it.
- **Runtime introspection replaces compile-time wiring** → mitigated by resolving the entire
  graph at startup (`get(Runner)` before anything runs), so a wiring fault is a startup
  failure with a resolution trail, not a request-time surprise.
- **Reliance on `_is_protocol`, a private attribute** → isolated in one predicate, with the
  3.13 replacement noted.
- **Renaming `APP_REPOSITORY_BACKEND`** → breaking for anyone who already copied the
  template, but the convention requires the name to derive from the port. `.env.example`,
  `README.md`, and `CLAUDE.md` are updated together, and an unknown backend value fails at
  startup listing the real ones, so the failure mode is loud.
- **Two adapters for one port in one backend package** → rejected with both filenames; one
  backend implements a port once.

## Migration Plan

Template-local, no data and no deployment. Land in the order the tasks list, with two hard
constraints: the composition rewrite, the settings rename, and `main.py` must land together
(they do not type-check independently), and the ruff hook change is independent and can land
first on its own.

Rollback is `git revert` — nothing outside this repository is affected.

For an existing project copied from this template: rename `APP_REPOSITORY_BACKEND` to
`APP_<PORT_CORE>_BACKEND` per port, delete the `BACKEND_*` constants, delete every provider
whose body is `return SomeUseCase(self.some_port())`, and keep only providers that do
something the convention cannot express.

## Open Questions

- Should CI run the suite with `--all-extras` so the wiring test never silently skips a
  backend? Proposed: yes, and add a `make test-all` target for it. There is no CI workflow
  in this repository yet, so this lands as a `Makefile` target plus a line in `CLAUDE.md`.
- Should the four local hooks use `uv run --frozen` to skip lock resolution and fail loudly
  on a drifted `pyproject.toml`? Proposed as a follow-up, not bundled here.
- `pre-commit-hooks` is pinned at `v4.6.0` and is well behind. Out of scope for this change.
