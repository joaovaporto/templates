## Context

`Resolver._construct(cls, prefix)` supplies a constructor parameter that is neither a port
nor another wirable class from `settings.<prefix>_<param>`. The prefix is fixed at one
string per class: `conventions.prefix_of(cls)` for a use case, and the **backend package
name** for an adapter, passed down by `_build_adapter`.

```python
def _build_adapter(self, port: type) -> Any:
    tech, module = conventions.choose_adapter(self.settings, port, ...)
    return self._construct(conventions.load_adapter(module), tech)
```

For an adapter, `tech` is only half of what identifies it. The other half — the core it
implements — is already computed inside `choose_adapter` (`conventions.core_of(port)`) and
then discarded. That discarded half is exactly what a colliding argument needs to name
itself, so the fix is to keep it rather than to invent anything.

Constraints this design works under:

- **Additive only.** Applications built on the template must resolve identically with no
  edit. Whatever field the resolver looks for first must be absent from their settings.
- **Nothing is imported to make a decision.** `choose_adapter` selects by reading package
  metadata; the argument rules must stay equally cheap and must not need an adapter's
  constructor to be introspectable before it is selected.
- **Failures name the fix.** Every existing wiring error names a file, field, or env var.
  A new form must not create a failure mode that names neither.

## Goals / Non-Goals

**Goals:**

- Let one backend package implement several ports whose adapters share an argument name,
  each argument configured independently, without splitting the package.
- Keep `<backend>_<param>` the default, so a value genuinely shared by a tech's adapters
  is still written once.
- Keep the resolution rule a reader can state in one sentence.

**Non-Goals:**

- Changing the `infrastructure/<backend>/` layout (see the proposal's Non-Goals).
- Any change to how a use case's own arguments are named.
- Detecting an unresolved collision statically.

## Decisions

### An ordered list of prefixes, not a new lookup step

`_construct` takes prefixes in most-specific-first order and `_argument` uses the first one
the settings model declares. An adapter is built with two, a use case with one:

```python
# _build_adapter
core = conventions.core_of(port)
return self._construct(conventions.load_adapter(module), *conventions.arg_prefixes(core, tech))

# conventions
def arg_prefixes(core: str, tech: str) -> tuple[str, ...]:
    """Most specific first: an argument may be scoped to the port it serves."""
    return (f"{core}_{tech}", tech)
```

*Alternative — a separate "scoped lookup, then plain lookup" branch inside `_argument`:*
rejected because it hardcodes "two" into the resolver and makes the adapter case
structurally different from the use-case case. With a list, both cases run the same loop
and the resolver never learns what a "core" is; the naming rule stays in `conventions`,
where every other one lives.

*Alternative — pass `port` down and let `_argument` derive the scope:* rejected because it
gives `_construct` a parameter meaningful for one of its two callers, and re-derives inside
the resolver something `conventions` already knows.

### Declaration decides precedence, not value

The winning prefix is the first whose field **exists on the settings model**
(`conventions.field_value(...) is not MISSING`), not the first whose value is non-default.

This matters because pydantic-settings cannot distinguish "left at its default" from
"explicitly set to the default value" without extra machinery, so a value-based rule would
make `APP_NOTE_REPOSITORY_JSONFILE_PATH=notes.json` silently fall through to
`APP_JSONFILE_PATH` whenever it happened to match the default. Declaration-based
precedence is static: read `Settings`, know which field feeds which adapter, with no
environment in hand.

The consequence is deliberate and worth stating in the docs: **declaring a scoped field
disables the plain one for that adapter**, even when the scoped field is left at its
default. A field declared is a field chosen.

### The type-mismatch error names the field that actually matched

`_argument` currently raises when a settings value's type does not match the parameter's
annotation, naming `field`. With two candidates, it must name the one that was used, or
the message sends the reader to a field they did not set. So the loop resolves to a
`(field, value)` pair first, and every message downstream uses that field.

### The unsuppliable-argument message teaches the plain form

`_unsuppliable` keeps naming `<prefix>_<param>` for the **least** specific prefix — the
plain `<backend>_<param>` — because that is the right advice for the overwhelmingly common
case, and adding a second field name to every such message would tax every reader for a
corner case most will never hit. The scoped form is offered in one trailing clause, as an
alternative, not as a second instruction.

*Alternative — name the most specific form:* rejected; it would push new users toward the
verbose field by default and quietly abandon the shared-`postgres_dsn` property that makes
the plain prefix worth keeping.

### `explain()` is left alone

`explain()` reports port → backend → module and imports nothing. Reporting which settings
field feeds each argument would require importing the adapter to read its constructor,
which is precisely what `explain()` avoids so it can answer for a backend whose extra is
not installed. Out of scope.

## Risks / Trade-offs

- **Two ways to name one thing.** → The plain form stays the documented default in the
  README, `CLAUDE.md` and `.env.example`; the scoped form appears as the answer to a
  specific question ("two ports, one backend, same argument name"), never as an equal
  option.

- **A scoped field silently shadows the plain one.** Someone declares
  `note_repository_jsonfile_path`, leaves it at its default, and wonders why
  `APP_JSONFILE_PATH` stopped taking effect. → Documented as the rule above, and it is the
  behaviour that makes precedence static. `make explain` still shows the adapter resolved;
  the value itself is one `Settings()` repr away.

- **A collision that nobody scopes still fails at the wrong altitude** — two adapters
  quietly sharing one value rather than erroring. → Unchanged from today, and out of
  scope: catching it means importing every adapter of a backend to compare constructors,
  which resolution deliberately does not do. The scoped form is the fix once the symptom
  appears.

- **The prefix pair `(f"{core}_{tech}", tech)` can be ambiguous in principle** — a backend
  literally named `note_repository_jsonfile` would produce the same field name as the pair
  `(note_repository, jsonfile)`. → Pathological; a backend package is named for a
  technology, and the resulting collision resolves to the same adapter's argument anyway.

## Migration Plan

None. The resolver looks for a field name that no existing settings model declares, so
every current application takes the fallback path and resolves exactly as before. Adoption
is per-argument, on the day a collision appears: declare the scoped field, and only that
argument moves.

Rollback is deleting the scoped field: resolution falls back to the plain prefix.

## Open Questions

None.
