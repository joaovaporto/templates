## Why

An adapter's constructor arguments are read from settings under the **backend package
name**: `OrjsonNoteRepositoryAdapter(path)` in `infrastructure/jsonfile/` is fed by
`APP_JSONFILE_PATH`. That prefix is the tech, not the port, which is usually right — every
Postgres adapter in a system should share one `APP_POSTGRES_DSN` rather than repeat it per
port — but it has no way to express the exception. The moment one backend package
implements two ports with a same-named argument (`infrastructure/json/` holding both a
`*_note_repository_adapter` and a `*_parser_adapter`, each taking `path`), the two
arguments collide on `APP_JSON_PATH` and the only escape is to split the backend into
`json_repo/` and `json_parser/` — duplicating a tech package to work around a settings
name.

The layout is not the problem: one backend package implementing several ports is already
supported, because resolution matches a module *stem* per core. **Only the settings
namespace is too coarse.** So widen it rather than reshape the tree.

## What Changes

- **An adapter argument may be scoped to the port it serves.** Alongside the existing
  `<backend>_<param>`, the resolver also recognises `<core>_<backend>_<param>` —
  `APP_NOTE_REPOSITORY_JSONFILE_PATH` next to `APP_JSONFILE_PATH`.

- **The specific form wins when it is declared.** For each argument the resolver tries
  `<core>_<backend>_<param>` first and falls back to `<backend>_<param>`. "Declared" means
  the field exists on the settings model, not that it differs from its default, so
  precedence is a property of the model and does not shift at runtime with the values.

- **Nothing is required and nothing moves.** A settings model that declares only
  `jsonfile_path` behaves exactly as today; the scoped field is something you add on the
  day two ports actually collide, and only for the argument that collides. Adapters,
  ports, package layout and the `<core>_backend` rule are untouched.

- **The failure message teaches both forms.** An unsuppliable adapter argument names the
  plain field to add and mentions the scoped one as the way to keep two ports apart.

- **NOT BREAKING.** The change is purely additive: it introduces a field name the resolver
  previously ignored. Applications already built on this template resolve identically,
  with no edit to settings, adapters or wiring.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dependency-wiring`: the requirement *"Adapter and object arguments read from settings by
  convention"* gains a second, more specific field name for adapter arguments and a defined
  precedence between the two. The rule for non-adapter classes (a use case's own
  `<usecase>_<param>`) is unchanged.

## Impact

- `src/app/presentation/composition/resolver.py` — `_build_adapter` passes an ordered pair
  of prefixes instead of one; `_construct` and `_argument` take that order and use the
  first prefix the settings model declares; `_unsuppliable` names both forms.
- `src/app/presentation/composition/conventions.py` — the prefix pair is derived here, so
  the naming rules stay in the module that owns them.
- `src/app/presentation/settings.py` — the docstring documents the scoped form. No field
  is added: the template has no collision, and adding one pre-emptively would contradict
  the rule that a settings field appears only when there is a real choice.
- `tests/unit/test_resolver.py` — precedence, fallback, scoped-only, and two adapters of
  one backend configured apart; all against a local settings model, so the template does
  not grow a port to demonstrate a corner case.
- `.env.example`, `CLAUDE.md`, `README.md` — the argument convention documented as two
  forms with the plain one still the default. The README's `arguments` row, currently
  stranded below the table it belongs to, is put back in it while that line is edited.
- `openspec/specs/dependency-wiring/spec.md` — delta for the modified requirement.
- No runtime, extra, or dev dependency is added or removed.

## Non-Goals

- **Reshaping `infrastructure/` to `<core>/<backend>/`.** The port-first tree reads more
  intuitively, but it buys discoverability the settings fix does not need, costs every
  application using this template as a reference a migration, and loses the "one
  `postgres_dsn` for every Postgres adapter" sharing that the tech-first prefix gives for
  free. Rejected in favour of the smaller change.
- **Making the scoped form mandatory, or detecting collisions statically.** Requiring it
  everywhere would make the common case verbose and break the sharing above. Detecting a
  real collision means importing every adapter to read its constructor, which resolution
  deliberately avoids — the failure is already loud at the point of use.
- **Any change to how a non-adapter class reads its arguments.** A use case's name is
  unique in the package, so its prefix cannot collide.
