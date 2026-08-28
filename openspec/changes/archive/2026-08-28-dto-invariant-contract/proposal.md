## Why

This template already treats a DTO as a **carrier of proven invariants**: build one and
the data is correct, so the use case never re-checks it. `SaveNoteInputDto` validates on
construction, is frozen, and hands the use case a `to_note()` that cannot fail;
`SaveNoteUseCase.execute` therefore contains no validation at all. That is negative-space
programming — the use case's correctness rests on what the type system has already made
impossible, not on defensive checks.

**None of it is written down, and none of it is enforced.** Every mention of DTOs in
`README.md` and `CLAUDE.md` is about filenames and direction (`*_input_dto.py` toward the
core, `*_output_dto.py` away); `TestDtos` contains exactly one test, on the filename
suffix. The contract lives in a single class docstring inside `save_note_input_dto.py`. A
developer adopting this template copies that file, writes their second input DTO with no
validators, adds the presence checks to the use case instead, and nothing objects — the
architecture has quietly become the one it exists to prevent.

Every other rule in this template is stated and then machine-checked; `CLAUDE.md` says an
architecture rule nobody enforces is a comment. This one is currently a comment.

## What Changes

- **The DTO contract becomes a documented rule**, in `CLAUDE.md` and `README.md`,
  alongside the dependency rule and the wiring conventions rather than buried in a
  docstring: an input DTO is a use case's precondition made into a type; constructing one
  is what proves the use case may run; a use case never validates what it was handed.

- **`TestDtos` grows from one test to the set that makes the contract mechanical:**
  a DTO is a pydantic `BaseModel`, so construction validates; it is `frozen`, so proof
  cannot be invalidated after the fact; it sets `extra="forbid"`, so no unvalidated field
  can be smuggled in; and each DTO file defines exactly one `*Dto` class — the rule
  `CLAUDE.md` already claims but nothing checks.

- **The negative space gets its own test.** A module under `application/usecases/` may not
  raise a validation error. This is the half of the contract that actually decays in
  practice: the moment a use case re-validates, the DTO has stopped being proof and become
  a bag of fields.

- **The entity-conversion hazard is documented.** `SaveNoteInputDto.to_note()` is total
  only because the DTO's validators mirror `Note.__post_init__`'s invariants. That
  duplication is load-bearing and currently unremarked; add an invariant to an entity
  without mirroring it in the DTO and the "cannot fail" claim silently becomes false.

- **NOT BREAKING.** Every existing DTO already satisfies every new rule; the tests pass
  against the tree as it stands. The change makes explicit what the template already does.

## Capabilities

### New Capabilities

- `application-contracts`: what an application-layer artifact guarantees to its
  collaborators — what constructing a DTO proves, what a use case is therefore entitled to
  assume, and what neither may do. Distinct from `dependency-wiring`, which covers how
  objects are *supplied*; this covers what they *promise* once supplied.

### Modified Capabilities

None. `dependency-wiring` and `dev-tooling` are untouched.

## Impact

- `CLAUDE.md` — a "DTOs carry invariants" subsection under Conventions, and the
  entity-conversion hazard noted where the DTO rules are stated.
- `README.md` — the contract with the `SaveNoteInputDto` example, so a reader meets it
  before copying the file.
- `tests/architecture/test_naming_conventions.py` — `TestDtos` extended; a new test class
  for the use-case rule.
- No change to `src/`. No dependency added or removed. No public signature changes.

## Non-Goals

- **Testing that a DTO's validators are "enough".** Whether a field needs a constraint
  beyond its type is a domain judgement; a test demanding a validator on every input DTO
  would be wrong for a DTO whose every value is legitimately valid, and would train people
  to add empty validators to satisfy it. The decidable guarantees are structural
  (`BaseModel`, frozen, `extra="forbid"`) plus the negative-space rule that catches the
  real failure — a use case validating. See design.md.
- **De-duplicating the DTO/entity invariant overlap.** Making `SaveNoteInputDto` delegate
  to `Note`'s rules is a behaviour change to a template class and deserves its own
  proposal; this change documents the coupling so the next reader sees it.
- **The output-DTO outcome convention.** That a use case returns `SaveNoteOutputDto.failed`
  rather than raising for a routine outcome is a real, undocumented contract too, but it
  is about error strategy rather than invariants. Left for a follow-up.
