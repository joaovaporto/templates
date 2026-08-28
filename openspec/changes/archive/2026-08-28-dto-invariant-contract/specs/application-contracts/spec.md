## ADDED Requirements

### Requirement: A DTO is a validated, immutable value

Every class under `application/dtos/` whose name ends in `Dto` SHALL be a pydantic
`BaseModel` configured `frozen=True` and `extra="forbid"`, so that construction validates,
a validated instance cannot subsequently be mutated, and no undeclared field can enter
unvalidated. Each DTO module SHALL define exactly one such class.

#### Scenario: A DTO validates on construction

- **WHEN** a DTO class is defined under `application/dtos/`
- **THEN** it is a pydantic `BaseModel`, so building it runs its field types and validators

#### Scenario: A DTO cannot be mutated after validation

- **WHEN** a DTO's effective `model_config` is read
- **THEN** `frozen` is true
- **AND** assigning to a field of a built instance raises

#### Scenario: A DTO admits no undeclared field

- **WHEN** a DTO's effective `model_config` is read
- **THEN** `extra` is `"forbid"`

#### Scenario: A non-model DTO is rejected

- **WHEN** a class ending in `Dto` is declared as a plain dataclass, `TypedDict`, or
  `NamedTuple`
- **THEN** the architecture suite fails, naming the file

#### Scenario: One DTO per module

- **WHEN** a module under `application/dtos/` defines two classes ending in `Dto`
- **THEN** the architecture suite fails, naming the file and the classes found

#### Scenario: A DTO module may define supporting types

- **WHEN** a DTO module defines an enum or other helper alongside its single `*Dto` class
- **THEN** the suite passes, because only classes ending in `Dto` are counted

### Requirement: An input DTO is the use case's precondition

An input DTO SHALL carry the invariants its use case depends on, so that a successfully
constructed instance is proof that the use case may run. Data that violates a business rule
SHALL be rejected at construction of the DTO, not inside the use case.

#### Scenario: Invalid data never becomes a DTO

- **WHEN** a value violating a business rule is passed to an input DTO's constructor
- **THEN** construction raises and no instance exists

#### Scenario: A built input DTO is sufficient to proceed

- **WHEN** a use case receives an input DTO
- **THEN** it may read every field without checking presence, emptiness, or range

### Requirement: A use case does not re-validate its input

A module under `application/usecases/` SHALL NOT raise a validation error. A use case
receives proof, not data to be checked; re-validating means the DTO has stopped carrying
the invariant. A use case MAY catch a validation error raised by a collaborator.

#### Scenario: A use case raising a validation error

- **WHEN** a module under `application/usecases/` contains a `raise` of an exception whose
  name ends in `ValidationError`
- **THEN** the architecture suite fails, naming the file

#### Scenario: A use case catching a validation error

- **WHEN** a use case catches a validation error without raising one
- **THEN** the suite passes

#### Scenario: The example use case validates nothing

- **WHEN** `SaveNoteUseCase.execute` is read
- **THEN** it converts and stores its input with no presence or emptiness check

### Requirement: Conversion from an input DTO to an entity is total

An input DTO that exposes a method building a domain entity SHALL carry every invariant
that entity enforces, so the conversion cannot fail. The coupling SHALL be documented, so
that adding an invariant to an entity is known to require revisiting the DTOs that build it.

#### Scenario: Conversion cannot fail

- **WHEN** `SaveNoteInputDto.to_note()` is called on any successfully constructed instance
- **THEN** a `Note` is returned and no `DomainValidationError` is raised

#### Scenario: The coupling is stated where a DTO is written

- **WHEN** a developer consults the project documentation to write an input DTO
- **THEN** the documentation states that a DTO building an entity owes that entity's
  invariants, and that changing an entity's invariants means revisiting those DTOs
