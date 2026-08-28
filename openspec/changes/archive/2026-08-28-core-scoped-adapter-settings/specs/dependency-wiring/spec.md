## MODIFIED Requirements

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
