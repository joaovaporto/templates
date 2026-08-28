# Python — Hexagonal Architecture Template

A starting point for a Python project with **hexagonal architecture**, a **machine-checked
dependency rule**, a **typed composition root you do not have to write**, and **clean
dependency tiers** (core / extras / dev) managed with `uv`.

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
│   ├── dtos/          # *_input_dto.py (toward the core) / *_output_dto.py (away)
│   ├── ports/         # *_port.py — one Protocol each, the seams
│   ├── usecases/      # *_usecase.py — one class each, collaborators injected
│   └── errors.py
├── infrastructure/    # <backend>/*_adapter.py — one subpackage per technology
│   ├── memory/        # default backend, no extra
│   ├── jsonfile/      # optional backend behind the `jsonfile` extra
│   └── system/        # the clock — a port with one implementation, so no setting names it
└── presentation/      # settings, runner, edges — NEVER names an adapter
    ├── settings.py
    ├── runner.py
    └── composition/   # the wiring, and the only module that may name an adapter
        ├── resolver.py    # builds any class from its constructor annotations; lazy, cached
        ├── conventions.py # the naming rules, and what to say when one is unmet
        ├── errors.py
        └── main.py

tests/
├── architecture/      # the dependency rule + naming conventions, run in-suite
├── unit/              # use cases against fakes — no resolver, no I/O
└── fakes/
```

## How wiring works

`resolver.get(SaveNoteUseCase)` reads that class's constructor and supplies every
parameter. Nothing is registered, so **adding a use case costs no wiring at all**:

| step | rule | example |
|---|---|---|
| port | a `*Port` Protocol in `application/ports/` | `NoteRepositoryPort` |
| core | the port name minus `Port`, snake_cased | `note_repository` |
| backend | settings field `<core>_backend`, whose value is a subpackage of `infrastructure/` | `APP_NOTE_REPOSITORY_BACKEND=jsonfile` |
| module | in that subpackage, the one stem ending `_<core>_adapter` | `jsonfile/orjson_note_repository_adapter.py` |
| class | the one `*Adapter` class in that module | `OrjsonNoteRepositoryAdapter` |
| arguments | non-port parameters read `<backend>_<param>` from settings | `path: Path` ← `APP_JSONFILE_PATH` |

A port lives directly in `application/ports/` and an adapter directly in
`infrastructure/<backend>/` — resolution lists one directory rather than walking a tree, so
the depth is itself a checked rule.

Naming an argument after the backend is what lets every Postgres adapter share one
`APP_POSTGRES_DSN`. When that is too coarse — one backend implementing two ports whose
adapters both take `path` — scope the argument to its port as
`<core>_<backend>_<param>` (`APP_NOTE_REPOSITORY_JSONFILE_PATH`), which is read in
preference to the plain field. Declaring the scoped field is what selects it, so it wins
even when left at its default.

Adapters are found by **module stem**, never by class name, so an adapter may keep the
name of the library it wraps. A port with a single implementation needs no settings field;
one appears when there is a real choice, and an architecture test fails until you add it.

An edge holds the resolver and asks it for what each method needs, so its constructor does
not list the use cases it drives:

```python
class Runner:
    def __init__(self, resolver: Resolver[Settings]) -> None:
        self._resolver = resolver

    def run(self) -> None:
        self._resolver.get(SaveNoteUseCase).execute(...)
```

Three things follow, and they are the point:

- **Nothing guesses.** One settings field decides, unknown values fail at startup listing
  the packages that exist, and every error names the file, field, or env var that fixes it.
- **`@provider` is the escape hatch, not the norm.** A `Resolver` declares no bindings;
  subclass it and add a method only where names cannot express one, annotated with the
  port it supplies.
- **The suite is the compiler.** Because no module names an adapter,
  `tests/architecture/test_wiring_resolves.py` builds every use case on every backend, and
  `make explain` shows what the current settings actually resolve to.

Composition wires layers together and does nothing else — **session and connection
management is not its job**. A pool shared by every Postgres adapter belongs in
`infrastructure/`, resolved inside that layer, so the use case and the edge never hear of
one; connection handling that is genuinely the edge's concern belongs in `presentation/`.
That is why no resolution call takes a session and why there is no scope machinery.

## DTOs carry invariants

A use case trusts what it is handed. **An input DTO is its precondition made into a type**:
constructing one is what proves the use case may run, so the use case reads every field
without checking presence, emptiness, or range.

```python
class SaveNoteInputDto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    body: str

    @field_validator("key", "body")
    @classmethod
    def _must_be_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class SaveNoteUseCase:
    def execute(self, request: SaveNoteInputDto) -> SaveNoteOutputDto:
        note = request.to_note()   # no checks: an invalid request could not exist
```

Bad data is rejected where the DTO is built, at the edge, and never reaches the core —
the use case is correct because of what the type made impossible, not because it defends
itself. `BaseModel` makes construction validate, `frozen=True` stops the proof being
invalidated afterwards, and `extra="forbid"` keeps an unvalidated field from riding along.
`tests/architecture/test_naming_conventions.py` checks all three, that each file holds one
`*Dto` class, and that **no use case raises a validation error** — re-validating means the
DTO has stopped being proof.

An input DTO that builds an entity owes that entity's invariants: `to_note()` cannot fail
only because the DTO validates the same `key` and `body` that `Note` does, so changing an
entity's invariants means revisiting the DTOs that build it. Output DTOs share the
structural rules but carry no precondition — they are evidence, not permission.

## The dependency rule (enforced by `make arch`)

Imports flow inward only. `domain` → nothing; `application` → `domain`; `infrastructure`
→ `application`+`domain`; `presentation` → `application`+`domain`, **never**
`infrastructure`. The one exception is `presentation/composition/`, the wiring module,
which may know everything — declared as an `ignore_imports` on the contract, so the
exemption is visible rather than assumed. An edge may hold the resolver and ask for a use
case, but may never name the adapter behind one. See `pyproject.toml` under
`[tool.importlinter]`.

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
APP_NOTE_REPOSITORY_BACKEND=jsonfile uv run app

make explain            # which adapter each port resolves to right now
```

## Make targets

`install` · `install-dev` · `install-all` · `lint` · `format` · `typecheck` · `arch` ·
`test` · `test-unit` · `test-all` · `coverage` · `check` · `explain` · `clean` — run
`make help`. CI should run `make test-all`: the wiring test skips a backend whose extra is
absent, and that target installs every extra so nothing is skipped.

## Adopting it

`app` is a placeholder package name. See **Renaming the package** in `CLAUDE.md` for the
exact edits; `make arch` and `make check` catch anything you miss.
