# dependency-wiring Specification

## Purpose
TBD - created by archiving change convention-driven-wiring. Update Purpose after archive.
## Requirements
### Requirement: Typed resolution of any wirable class

The composition root SHALL expose a single generic entry point,
`Resolver.get(target)`, that returns an instance of `target` with every
constructor dependency supplied. The return
type SHALL be `target`'s type, not `Any`, and the parameter SHALL be a class object, not a
string name. Each type SHALL be constructed at most once per container instance, and nothing
SHALL be constructed until it is asked for.

#### Scenario: Resolving a use case
- **WHEN** `resolver.get(SaveNoteUseCase)` is called
- **THEN** a `SaveNoteUseCase` is returned with its `NoteRepositoryPort` parameter supplied
- **AND** a static type checker infers the result as `SaveNoteUseCase`

#### Scenario: Resolution is recursive
- **WHEN** a resolved class declares a parameter that is itself resolvable
- **THEN** it is resolved by the same rules and passed in

#### Scenario: Instances are cached per container
- **WHEN** the same type is resolved twice from one resolver
- **THEN** both calls return the identical object
- **AND** a type that no resolution reached is never constructed

#### Scenario: Adding a use case requires no wiring code
- **WHEN** a new `*_usecase.py` is added under `application/usecases/` whose constructor
  declares only ports already implemented
- **THEN** `resolver.get(NewUseCase)` succeeds with no edit to any file under `composition/`

### Requirement: Deterministic port-to-adapter selection

A constructor parameter annotated with a `*Port` Protocol SHALL be satisfied by exactly one
adapter, chosen deterministically from the port's name and the settings. The system SHALL
derive the settings field name from the port name (`NoteRepositoryPort` →
`note_repository_backend`), treat that field's value as the name of a subpackage of
`infrastructure/`, and select within it the single module whose stem ends with
`_<core>_adapter`, then the single class in that module whose name ends with `Adapter`.
The system SHALL NOT infer a backend from any settings value other than that field.

#### Scenario: Backend named in settings
- **WHEN** `APP_NOTE_REPOSITORY_BACKEND=jsonfile` and a `NoteRepositoryPort` is required
- **THEN** `infrastructure/jsonfile/orjson_note_repository_adapter.py` is imported
- **AND** its `OrjsonNoteRepositoryAdapter` is constructed and supplied

#### Scenario: Adapter class name need not match its package
- **WHEN** the selected subpackage is `memory` and it contains
  `in_memory_note_repository_adapter.py` defining `InMemoryNoteRepositoryAdapter`
- **THEN** that class is selected, because discovery matches the module stem, not the class name

#### Scenario: Port with a single implementation needs no settings field
- **WHEN** a port is implemented by exactly one adapter across all of `infrastructure/`
  and `Settings` declares no `<core>_backend` field for it
- **THEN** that adapter is selected

#### Scenario: Only the selected adapter is imported
- **WHEN** the selected backend is `memory`
- **THEN** no module under any other infrastructure subpackage is imported
- **AND** an optional dependency belonging to an unselected adapter is never required

### Requirement: Adapter and object arguments read from settings by convention

A constructor parameter that is neither a port nor another wirable class SHALL be supplied
from a settings field named `<prefix>_<parameter>`. For a class that is not an adapter the
prefix SHALL be the class's own name minus its role suffix, snake_cased. For an adapter the
system SHALL consider two prefixes in order — `<core>_<backend>`, then `<backend>` — and
use the first one for which the settings model **declares** a matching field, regardless of
whether that field holds its default value. The system SHALL NOT coerce types; the settings
field SHALL carry the declared type so that validation happens in the settings model. A
parameter with no matching field under any of its prefixes SHALL fall back to its default if
it has one.

#### Scenario: Adapter argument from settings

- **WHEN** `OrjsonNoteRepositoryAdapter(path: Path)` in backend package `jsonfile` is constructed
- **AND** `Settings` declares `jsonfile_path` and no `note_repository_jsonfile_path`
- **THEN** `path` is supplied from `settings.jsonfile_path` (env `APP_JSONFILE_PATH`)
- **AND** the value arrives already typed as `Path`, coerced by the settings model

#### Scenario: An argument scoped to the port it serves

- **WHEN** `Settings` declares `note_repository_jsonfile_path`
- **AND** a `NoteRepositoryPort` is resolved to an adapter in backend package `jsonfile`
  taking `path`
- **THEN** `path` is supplied from `settings.note_repository_jsonfile_path`
  (env `APP_NOTE_REPOSITORY_JSONFILE_PATH`)

#### Scenario: Two ports served by one backend, configured apart

- **WHEN** one backend package holds an adapter for `NoteRepositoryPort` and an adapter for
  `ParserPort`, both taking a parameter of the same name
- **AND** `Settings` declares a `<core>_<backend>_<parameter>` field for each
- **THEN** each adapter receives the value scoped to its own port
- **AND** neither adapter reads the other's field

#### Scenario: A scoped field takes precedence over the plain one

- **WHEN** `Settings` declares both `note_repository_jsonfile_path` and `jsonfile_path`
- **THEN** the adapter serving `NoteRepositoryPort` is supplied from
  `note_repository_jsonfile_path`
- **AND** this holds even when that field is left at its default value

#### Scenario: One value shared by every adapter of a backend

- **WHEN** two adapters in backend package `postgres` serve different ports and both take `dsn`
- **AND** `Settings` declares only `postgres_dsn`
- **THEN** both adapters are supplied from `settings.postgres_dsn`

#### Scenario: A settings model declaring no scoped field is unaffected

- **WHEN** a settings model declares only `<backend>_<parameter>` fields
- **THEN** every adapter resolves to the same argument values as before the scoped form existed

#### Scenario: Parameter with a default and no settings field

- **WHEN** a constructor parameter has no matching settings field under any of its prefixes
  but declares a default
- **THEN** the default is used and no error is raised

#### Scenario: An unsuppliable adapter argument names a field to add

- **WHEN** an adapter parameter matches no settings field and has no default
- **THEN** resolution fails naming the adapter, the parameter, and the `<backend>_<parameter>`
  field with its environment variable
- **AND** the message also offers `<core>_<backend>_<parameter>` as the way to keep two ports apart

#### Scenario: A type mismatch names the field that was read

- **WHEN** the settings field supplying a parameter holds a value of the wrong type
- **THEN** the error names the specific field that was read, not another candidate prefix

### Requirement: Resolution looks in one directory, not down a tree

A port SHALL live directly in `application/ports/` and an adapter directly in
`infrastructure/<backend>/`. Resolution lists a single directory rather than walking a
tree, so a nested artifact SHALL be rejected by the suite rather than being silently
invisible to the resolver.

#### Scenario: A nested adapter
- **WHEN** an adapter module sits deeper than `infrastructure/<backend>/`
- **THEN** the architecture suite fails, naming the file and the expected depth

#### Scenario: A nested port
- **WHEN** a port module sits in a subdirectory of `application/ports/`
- **THEN** the architecture suite fails, naming the file

### Requirement: Each layer owns the errors it raises

An error class SHALL live in the layer that raises it. `application/errors.py` SHALL hold
only what the core itself raises or catches, so that the core carries nothing existing
solely for another layer.

#### Scenario: A wiring failure
- **WHEN** the conventions cannot be satisfied
- **THEN** the error raised is composition's, not the core's

#### Scenario: A missing optional extra
- **WHEN** a selected adapter's package is absent
- **THEN** the error raised is infrastructure's, and still reaches the operator with the
  resolution trail attached

### Requirement: Explicit providers override the conventions

A container subclass SHALL be able to override the conventional resolution of a type with a
`@provider`-decorated method annotated with the type it supplies. The override SHALL win for
that type wherever it is required. A provider SHALL NOT be annotated with a class from
`infrastructure/`, and two providers in one container SHALL NOT supply the same type.

#### Scenario: Provider wins over the convention
- **WHEN** a container subclass declares `@provider def note_repository(self) -> NoteRepositoryPort`
- **THEN** every use case resolved from that container receives the provider's object rather
  than the adapter the settings name

#### Scenario: Provider typed to an adapter is rejected
- **WHEN** a provider's return annotation is a class defined under `infrastructure/`
- **THEN** the architecture test suite fails, naming the provider and the class

#### Scenario: A use case depending on a provided port needs no provider
- **WHEN** a `@provider` supplies a port that several use cases depend on
- **THEN** each of those use cases still resolves by convention, receiving the provided
  object, because a provider is keyed by the type it returns

#### Scenario: An empty resolver still resolves the whole graph
- **WHEN** the application's container declares no providers at all
- **THEN** every use case and the runner still resolve by convention

### Requirement: Composition wires layers and does not manage sessions

The composition root's role SHALL be limited to wiring the layers together. Session,
connection, and pool management SHALL NOT live there: a resource shared by several
adapters of one technology belongs to `infrastructure/` and SHALL be obtained within that
layer, and connection or transaction handling that is genuinely the edge's concern belongs
to `presentation/`. Consequently no resolution call SHALL take a session, connection, or
scope, and the composition root SHALL NOT ship scope or teardown machinery.

#### Scenario: An adapter needing a connection
- **WHEN** a use case depends on a port whose adapter needs a database session
- **THEN** the resolver builds that adapter by the ordinary conventions
- **AND** the adapter obtains its session within `infrastructure/`
- **AND** neither the use case nor the edge references a session

#### Scenario: A connection concern owned by the edge
- **WHEN** a transaction boundary belongs to the edge itself
- **THEN** it is handled in `presentation/`, not in the composition root

#### Scenario: No lifetime argument
- **WHEN** an edge resolves a use case
- **THEN** it passes only the use case class

#### Scenario: Nothing unused ships
- **WHEN** the composition root is read
- **THEN** it contains no scope or teardown code that nothing uses

### Requirement: Every failure to wire names its remedy

When resolution cannot proceed, the system SHALL raise a configuration error at startup —
never a bare `ImportError`, `AttributeError`, or `TypeError` at first use — and the message
SHALL name the concrete action that fixes it. The error SHALL also carry the chain of types
being resolved when it occurred.

#### Scenario: Unknown backend name
- **WHEN** a `*_backend` setting names a package that does not exist under `infrastructure/`
- **THEN** startup fails with an error listing the subpackages that do exist

#### Scenario: Backend does not implement the port
- **WHEN** the named backend package contains no module for the required port
- **THEN** the error names the expected module filename and lists the ports that package does implement

#### Scenario: Ambiguous port with no settings field
- **WHEN** two or more backends implement one port and `Settings` declares no `<core>_backend`
  field for it
- **THEN** the error names the settings field and environment variable to add, and lists the candidates

#### Scenario: Unsuppliable parameter
- **WHEN** a constructor parameter is neither a port, nor a wirable class, nor a known
  settings field, and has no default
- **THEN** the error names the parameter, its declared type, and the environment variable searched

#### Scenario: Optional dependency not installed
- **WHEN** the selected adapter's optional package is absent
- **THEN** startup fails with the existing missing-dependency error naming the extra to install
- **AND** that error keeps its own type rather than being replaced by a generic one

#### Scenario: Dependency cycle
- **WHEN** two classes require each other through their constructors
- **THEN** resolution fails naming the cycle rather than exhausting the stack

#### Scenario: Resolution trail
- **WHEN** resolution fails several levels deep
- **THEN** the error carries the chain of types from the requested one down to the failure

### Requirement: An edge obtains use cases without a constructor per use case

An edge SHALL be able to obtain a use case at the point of use, so the number of use cases
it drives does not change its constructor. The composition root SHALL build each edge and
pass it the resolver; no interface SHALL be introduced between them, and nothing SHALL be
added to `application/` for this purpose — the core neither uses nor references such a
thing. Presentation MAY import composition; it SHALL NOT import `infrastructure`.

#### Scenario: Resolving inside a method
- **WHEN** an edge method resolves a use case
- **THEN** a fully constructed use case is returned and the edge's constructor names none

#### Scenario: Adding a use case to an edge
- **WHEN** an existing edge starts driving an additional use case
- **THEN** the only change is the call that resolves it

#### Scenario: Only the wiring module may name an adapter
- **WHEN** the architecture check runs
- **THEN** `presentation/composition/` importing `infrastructure` is permitted, by an
  exemption declared on the contract rather than assumed
- **AND** any other presentation module importing `infrastructure` fails the check,
  directly or through a chain
- **AND** the same exemption applies to the rule that an edge resolves only use cases,
  since naming what an edge may not is the wiring module's job

#### Scenario: An edge resolves only real use cases
- **WHEN** a module under `presentation/` resolves a class that is not a use case defined
  under `application/usecases/`
- **THEN** the architecture suite fails, naming the module and the class

#### Scenario: A wiring failure surfaces at first use
- **WHEN** an edge is built while a backend is misconfigured
- **THEN** construction succeeds and the failure is raised when a method resolves,
  with the suite catching it in CI instead

#### Scenario: An edge is tested without a new double
- **WHEN** a test constructs an edge with a resolver subclass whose single `@provider`
  supplies a fake
- **THEN** the edge runs against that fake, with no I/O and no test double for the resolver

### Requirement: The wiring is verified in the test suite

Because no module statically names the adapter it uses, the test suite SHALL construct every
use case against every declared backend combination, so that a broken convention fails in CI
rather than at runtime. The suite SHALL also enforce the naming rules the resolution depends on.

#### Scenario: Every use case builds on every backend
- **WHEN** the architecture suite runs
- **THEN** each use case under `application/usecases/` is resolved once per legal backend
  combination and asserted to be an instance of itself

#### Scenario: Adapter module names a real port
- **WHEN** an adapter module's stem does not correspond to any port under `application/ports/`
- **THEN** the naming test fails, naming the file

#### Scenario: Second implementation forces a settings field
- **WHEN** a second backend implements a port for which `Settings` declares no `<core>_backend`
- **THEN** the naming test fails, naming the field to add

#### Scenario: The resolved wiring can be inspected
- **WHEN** an operator asks which adapter each port resolves to
- **THEN** the answer is printed for the current settings, without importing any adapter,
  so it works for a backend whose extra is not installed
- **AND** a misconfigured port is reported in that listing rather than raised

#### Scenario: Every port is implementable
- **WHEN** a port has no adapter anywhere under `infrastructure/`
- **THEN** the naming test fails, naming the port
