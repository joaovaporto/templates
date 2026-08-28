## Context

The application layer already runs on an assumption it never states. `SaveNoteUseCase`:

```python
def execute(self, request: SaveNoteInputDto) -> SaveNoteOutputDto:
    note = request.to_note()
    ...
```

No presence check, no emptiness check, no try around the conversion. That is only correct
because `SaveNoteInputDto` validated `key` and `body` on construction, is frozen so they
cannot have changed since, and forbids extras so nothing unvalidated rode along. The use
case is entitled to its assumption — but the entitlement is invisible.

What exists today to protect it: `TestDtos`, one test, asserting the filename ends in
`_input_dto` or `_output_dto`. Direction, not contract.

Constraints:

- **No change to `src/`.** Every current DTO already complies; this change states and
  checks the status quo. A test that fails on the tree as it stands is a bug in the test.
- **No new dependency.** The architecture suite uses `ast` and ordinary imports.
- **A rule must be decidable.** `CLAUDE.md` treats an unenforced rule as a comment, but an
  over-eager rule is worse: it trains people to satisfy the checker rather than the intent.

## Goals / Non-Goals

**Goals:**

- Make "constructing this DTO proves the use case may run" a rule a reader meets in the
  docs and a checker enforces, not a docstring they may never open.
- Catch the decay that actually happens: validation migrating into use cases.
- Leave the coupling between a DTO's validators and its entity's invariants visible.

**Non-Goals:**

- Judging whether a given DTO's validation is sufficient.
- Changing any DTO, entity, or use case.

## Decisions

### The guarantee is split into what is decidable and what is documented

The full contract is *"a DTO exists only if its values respect all business rules."*
Whether a rule was missed is not mechanically decidable — it needs the domain. So the
contract is enforced along the axes that are decidable, chosen so that each one closes a
concrete way the guarantee is lost:

| enforced | closes |
|---|---|
| a DTO is a pydantic `BaseModel` | a plain dataclass or `TypedDict` that never validates |
| `frozen=True` | proof established at construction, invalidated by later mutation |
| `extra="forbid"` | an unvalidated field smuggled past the declared schema |
| exactly one `*Dto` class per file | two DTOs sharing a file, one silently unchecked |
| no validation error raised in `usecases/` | the use case re-validating, i.e. not trusting the DTO |

Business-rule sufficiency stays documented rather than tested, for the reason in the
proposal's Non-Goals.

### The negative-space rule is expressed as "a use case may not raise a validation error"

This is the load-bearing test, and the one the philosophy is really about. It is checked
by AST over `application/usecases/`: a `raise` whose exception name ends in
`ValidationError` fails, naming the file.

*Alternative — flag `if not request.<field>` patterns:* rejected. Too syntactic; it fires
on legitimate business branching (`if not request.tags: ...` is a decision, not a
validation) and misses re-validation written any other way.

*Alternative — forbid a use case importing `DomainValidationError` at all:* rejected as
too strong. A use case may legitimately *catch* one — say, around a domain operation that
is genuinely partial — without re-validating its input. Raising is the signal; catching is
not.

The rule targets raising specifically because a use case that raises a validation error is
asserting its input was invalid, which is precisely the claim the DTO already settled.

### Structural checks import; shape checks parse

`frozen`, `extra`, and `BaseModel`-ness are read from `model_config` on the imported class,
not from the AST. The application layer has no optional dependencies, so importing it is
free, and `model_config` reflects inheritance — an AST check would miss a DTO that sets
`frozen` on a shared base. `ports_in()` already imports application modules for the same
reason.

The "exactly one `*Dto` class per file" rule stays on the AST, matching `TestPorts` and
`TestUseCases`, which count class definitions rather than module attributes so an imported
name cannot be miscounted as a definition.

### The entity-conversion coupling is documented, not tested

`to_note()` is annotated *"Total: the invariants already hold, so this cannot fail"*. That
holds only while `SaveNoteInputDto`'s validators cover `Note.__post_init__`'s invariants —
today both check `key` and `body` non-empty. Testing this generally means enumerating an
entity's invariants from its `__post_init__`, which is not tractable.

So it becomes a documented hazard at the point where someone would break it: the docs say
that an input DTO with a `to_<entity>()` method owes that entity's invariants, and that
adding an invariant to an entity means revisiting the DTOs that build it.

*Alternative — a property-based test over `to_note()`:* rejected; it needs a new
dependency, and it would prove totality for `Note` only, not state the rule.

## Risks / Trade-offs

- **The use-case rule is a name match, so `raise MyValidationError` is caught and
  `raise BadInput` is not.** → Accepted. It is precise about the convention this template
  already follows (`DomainValidationError`, pydantic's `ValidationError`), and the docs
  carry the intent. A checker that tried to recognise validation semantically would be the
  over-eager rule this design rejects.

- **Documenting the DTO/entity coupling without removing it leaves a real footgun in
  place.** → Deliberate: removing it is a behaviour change to a template class and is
  scoped to its own proposal. Naming it is strictly better than today, where it is
  unremarked.

- **More rules for a reader to absorb.** → They replace nothing and contradict nothing;
  the DTO section is where a reader already looks when writing a DTO, and the tests fail
  with a message naming the file and the fix, as the rest of the suite does.

## Migration Plan

None. Every existing artifact satisfies every new rule — the tests must pass on the
unmodified tree, which is the acceptance criterion for the test tasks.

## Open Questions

None.
