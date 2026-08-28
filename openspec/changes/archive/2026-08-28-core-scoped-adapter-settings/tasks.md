## 1. Conventions

- [x] 1.1 Add `arg_prefixes(core: str, tech: str) -> tuple[str, ...]` to `conventions.py`,
      returning `(f"{core}_{tech}", tech)` — most specific first — with a one-line docstring
      stating that an adapter argument may be scoped to the port it serves.

## 2. Resolver

- [x] 2.1 Change `_construct(self, cls, prefix)` to `_construct(self, cls, *prefixes)` and
      pass the prefixes through to `_argument`.
- [x] 2.2 In `_build_adapter`, take the core from `conventions.core_of(port)` and call
      `self._construct(adapter, *conventions.arg_prefixes(core, tech))`. The use-case call
      site keeps its single `conventions.prefix_of(hint)` prefix and needs no edit.
- [x] 2.3 In `_argument`, replace the single `field = f"{prefix}_{name}"` with a scan over
      the prefixes that stops at the first field the settings model declares
      (`field_value(...) is not MISSING`), keeping both the field name and its value; when
      none is declared, the result is `MISSING` as today.
- [x] 2.4 Make the type-mismatch error report the field that was actually read, not the
      first candidate.
- [x] 2.5 In `_unsuppliable`, keep naming the least specific prefix (`<backend>_<param>`)
      as the field to add, and append one clause offering `<core>_<backend>_<param>` for
      two ports sharing a backend.

## 3. Tests

- [x] 3.1 A scoped field supplies an adapter argument: a local `Settings` declaring
      `note_repository_jsonfile_path` and no `jsonfile_path` writes to the scoped path.
- [x] 3.2 The scoped field wins when both are declared — including when it is left at its
      default, which is the declaration-not-value rule.
- [x] 3.3 The plain field still supplies the argument when no scoped field is declared
      (the existing `test_an_adapter_argument_comes_from_settings` covers this; assert it
      is unchanged rather than duplicating it).
- [x] 3.4 Two adapters of one backend serving different ports read their own scoped fields
      and not each other's, using a local resolver, ports and fake adapters in the test
      module so the template gains no port for a corner case.
- [x] 3.5 The unsuppliable-argument message for an adapter names `<backend>_<param>` with
      its env var and mentions the scoped form.
- [x] 3.6 The type-mismatch message names the field that was read when a scoped field is
      the one declared.

## 4. Documentation

- [x] 4.1 `settings.py` docstring: document `<core>_<backend>_<arg>` beneath the existing
      `<backend>_<arg>` line, as the disambiguator, not an equal alternative. Add no field.
- [x] 4.2 `.env.example`: one commented block next to `APP_JSONFILE_PATH` showing the
      scoped form and the question it answers.
- [x] 4.3 `README.md`: move the stranded `| arguments | ... |` row back into the wiring
      table it belongs to, and give the scoped form a sentence after the table.
- [x] 4.4 `CLAUDE.md`: extend the `arguments` row of the conventions table, and note under
      the wiring rules that declaring a scoped field disables the plain one for that
      adapter.

## 5. Verify

- [x] 5.1 `make check` passes (lint, mypy `--strict` with zero new ignores, import-linter,
      unit tests).
- [x] 5.2 `make test-all` passes with every extra installed.
- [x] 5.3 `make explain` output is unchanged, confirming `explain()` was not touched.
