## 1. Local ruff hooks

- [x] 1.1 Remove the `astral-sh/ruff-pre-commit` repo; add `ruff` and `ruff-format` to the existing `local` hooks before mypy, with `--force-exclude`, `types_or: [python, pyi]`, `require_serial`, filenames passed
- [x] 1.2 Verify the hooks pass and that pre-commit installs no ruff environment of its own

## 2. The conventions

- [x] 2.1 `presentation/composition/conventions.py`: the name helpers — `is_port`, `snake`, `core_of`, `prefix_of`, `backend_field`, `field_value`, `env_var`
- [x] 2.2 Package listing that imports nothing, via `find_spec` + `pkgutil.iter_modules`
- [x] 2.3 `choose_adapter` deciding before importing: settings field present → validate; absent → a single implementation wins, zero or many is an error
- [x] 2.4 Every failure message names the fix: the real backends, the expected filename, the settings field, the env var, the extra to install
- [x] 2.5 `load_adapter` imports the one chosen module and returns its single `*Adapter`

## 3. The resolver

- [x] 3.1 `presentation/composition/resolver.py`: `Resolver[SettingsT]`, per-type cache, package name derived from `__module__`
- [x] 3.2 `get[T](usecase: type[T]) -> T` over a private `Any`-typed hop, so no caller needs a `type: ignore`
- [x] 3.3 The parameter rules in order, excluding `domain/` and `application/dtos/` from wirable classes
- [x] 3.4 Reject dependency cycles by name; attach the resolution trail to a failing error with `add_note`, preserving the exception class
- [x] 3.5 Report a settings value whose type does not match the parameter as a settings problem
- [x] 3.6 `@provider` as the override marker, with a per-class index rejecting two providers of one type
- [x] 3.7 Delete `composition/provider.py`

## 4. Settings and the entrypoint

- [x] 4.1 Rename `repository_backend` → `note_repository_backend`, type `jsonfile_path` as `Path`, drop the `BACKEND_*` constants
- [x] 4.2 `main.py`: `Runner(Resolver(settings)).run()`, logging `__notes__` so the trail reaches the operator
- [x] 4.3 Verify both backends run, and that mypy strict stays clean with zero `type: ignore`

## 5. The edge

- [x] 5.1 `Runner` takes the resolver and asks for each use case where it uses it
- [x] 5.2 Move the composition root to `presentation/composition/` — one module inside the layer that starts the system
- [x] 5.3 Narrow the contract to "Presentation never names an adapter, except when wiring", with an explicit `ignore_imports` for the wiring module; verify an adapter imported from an edge still breaks it
- [x] 5.4 Give `TestEdgeLookups` the same carve-out, so a `@provider` resolving a port is not rejected
- [x] 5.5 Add nothing to `application/` for this: the core neither uses nor references it

## 6. Grow the demo

- [x] 6.1 `ClockPort` + `infrastructure/system/` — a port with one implementation, needing no settings field
- [x] 6.2 `ListNotesUseCase` taking two ports, and a unit test against fakes
- [x] 6.3 Confirm the diff under `composition/` for 6.1–6.2 is zero lines

## 7. The suite as the compiler

- [x] 7.1 `test_wiring_resolves.py`: every use case × every backend combination, with `_env_file=None` and `tmp_path`, skipping on a missing extra
- [x] 7.2 Naming rules: an adapter stem names a known port; every port has an adapter; a second backend forces a settings field; a `*_backend` default names a real package
- [x] 7.3 An edge resolves only real use cases (AST over `presentation/`)
- [x] 7.4 Verify each guard fails when abused
- [x] 7.5 Resolver unit tests, asserting every failure message and the typed lookup

## 8. Frugality pass

- [x] 8.1 Remove scope / child resolvers — session and connection management belongs to `infrastructure/` (or `presentation/`), never to the composition root
- [x] 8.2 Remove `close()`, teardown and the context-manager protocol — a resource's lifetime is owned by the layer that holds it
- [x] 8.3 Remove injecting the settings object — the convention is `<backend>_<param>`
- [x] 8.4 Keep `explain()` and `app-explain`: nothing names an adapter statically, so this is how an operator answers "what is actually wired"
- [x] 8.5 Confirm no remaining code exists only for a resolver that owned the graph

## 9. Coherence pass

- [x] 9.0 Move `ConfigurationError` to `composition/` and `MissingDependencyError` to `infrastructure/`; keep in `application/errors.py` only what the core raises or catches
- [x] 9.1 Attach the resolution trail to any failure during construction, so composition need not name an infrastructure error to catch it
- [x] 9.2 Rename DTOs to `*_input_dto.py` / `*_output_dto.py` with `Dto`-suffixed classes
- [x] 9.3 Name the use-case suffix as a constant beside `PORT_SUFFIX` and `ADAPTER_SUFFIX`
- [x] 9.4 Rename `get_usecase` back to `get`: it resolves ports too, so the narrower name overclaimed
- [x] 9.5 Add to `@provider`'s docstring the case of a constructor argument that is neither a port nor a settings value
- [x] 9.6 Enforce the flat tree that resolution assumes, in both directions

## 10. Documentation

- [x] 10.0 `CLAUDE.md`: how a value the conventions cannot supply reaches an adapter — a computed scalar through `Settings`, a live object through a resolver subclass — and why neither reaches the use cases
- [x] 10.1 `CLAUDE.md`: the convention table, the two edge styles, the amended contract, that composition never manages sessions, and that comments are not a record of how the codebase got here
- [x] 10.2 `README.md`: "How wiring works", the layout, the quick start
- [x] 10.3 `.env.example` and the root `README.md`

## 11. Verification

- [x] 11.1 `make check` green: lint, mypy strict with zero `type: ignore`, 5/5 contracts, 50 tests
- [x] 11.2 `make test-all` green
- [x] 11.3 Unknown backend exits 2 listing what implements the port; a missing extra exits 2 naming it
- [x] 11.4 Adding a use case, an adapter, or driving one more from an edge each leave `composition/` untouched
