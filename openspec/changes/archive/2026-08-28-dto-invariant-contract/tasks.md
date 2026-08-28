## 1. Documentation

- [x] 1.1 `CLAUDE.md`: add a "DTOs carry invariants" subsection under *Conventions*,
      stating that an input DTO is the use case's precondition made into a type, that
      constructing one is what proves the use case may run, and that a use case therefore
      never checks presence, emptiness or range. Keep it at the altitude of the dependency
      rule — the rule and its consequence, not a tutorial.
- [x] 1.2 `CLAUDE.md`: note the entity-conversion coupling where the DTO rules are stated —
      an input DTO with a `to_<entity>()` method owes that entity's invariants, so adding
      an invariant to an entity means revisiting the DTOs that build it.
- [x] 1.3 `README.md`: state the contract with the `SaveNoteInputDto` example, in the
      wiring/conventions region where a reader arrives before copying a DTO file. Mention
      that output DTOs share the structural rules but carry no precondition.
- [x] 1.4 Check the existing `dtos/` line in the README layout tree and the DTO bullet in
      `CLAUDE.md`'s conventions list still read correctly beside the new text, with no
      duplicated statement of the direction rule.

## 2. Structural tests

- [x] 2.1 Add a helper to `test_naming_conventions.py` that imports each module under
      `application/dtos/` and yields its `*Dto` classes, so `model_config` is read with
      inheritance applied rather than parsed from the AST.
- [x] 2.2 `TestDtos`: every `*Dto` class is a pydantic `BaseModel`. Failure names the file
      and the class.
- [x] 2.3 `TestDtos`: every `*Dto` class has `frozen=True` in its effective `model_config`.
- [x] 2.4 `TestDtos`: every `*Dto` class has `extra="forbid"` in its effective `model_config`.
- [x] 2.5 `TestDtos`: each DTO module defines exactly one class ending in `Dto`, counted
      from the AST like `TestPorts` and `TestUseCases` do, so a supporting enum such as
      `SaveOutcome` does not count.

## 3. The negative-space test

- [x] 3.1 Add a test class asserting no module under `application/usecases/` contains a
      `raise` of an exception whose name ends in `ValidationError`. Walk the AST for
      `ast.Raise`, resolving both `raise Foo(...)` and `raise Foo`. Failure names the file
      and explains that a use case receives proof, not data to check.
- [x] 3.2 Confirm the rule permits catching: a use case with `except DomainValidationError`
      and no matching `raise` passes. Cover it with a fixture in the test module rather
      than by adding one to `src/`.

## 4. Verify

- [x] 4.1 Every new test passes against the unmodified `src/` tree — no DTO, entity or use
      case is edited by this change. A test that requires a source edit is a bug in the test.
- [x] 4.2 Each new test fails for the right reason: temporarily break one rule at a time
      (a non-frozen DTO, a second `*Dto` in one file, a `raise DomainValidationError` in a
      use case) and confirm the message names the file. Revert each probe.
- [x] 4.3 `make check` passes — ruff, mypy `--strict` with zero `type: ignore`,
      import-linter, unit suite.
- [x] 4.4 `make test-all` passes with every extra installed.
