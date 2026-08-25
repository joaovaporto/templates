# dev-tooling Specification

## Purpose
TBD - created by archiving change convention-driven-wiring. Update Purpose after archive.
## Requirements
### Requirement: A tool already in the dev group runs from the dev environment

A quality gate whose tool is declared in `[dependency-groups].dev` SHALL be run by
pre-commit from that environment rather than installed a second time from a remote hook
repository. `uv.lock` SHALL therefore be the single source of truth for the version of every
such tool, and no pre-commit `rev` SHALL pin a second version of it.

#### Scenario: ruff runs from the project environment
- **WHEN** pre-commit runs on staged Python files
- **THEN** `ruff check` and `ruff format` are invoked through the project's dev environment
- **AND** no ruff hook repository is fetched or installed into a separate pre-commit venv

#### Scenario: One version of ruff
- **WHEN** ruff's version is changed in `uv.lock`
- **THEN** pre-commit uses the new version with no other file to edit
- **AND** `pre-commit autoupdate` cannot move ruff to a different version

#### Scenario: A remote hook is still used where the tool is not a project dependency
- **WHEN** a hook's tool is not declared in the dev group
- **THEN** it continues to be sourced from its upstream hook repository with a pinned `rev`

### Requirement: Local lint hooks respect the project's lint configuration

Hooks that receive staged filenames SHALL apply the exclusions declared in `pyproject.toml`,
which passing explicit filenames would otherwise bypass, and SHALL run in an order where
autofixes are applied before the checks that read the resulting files.

#### Scenario: Excluded file stays excluded
- **WHEN** a staged file matches an exclusion in the project's lint configuration
- **THEN** the hook skips it, as it would in a full-project run

#### Scenario: Fix before check
- **WHEN** a commit triggers the local hooks
- **THEN** lint autofix and formatting run before type checking and the architecture check

#### Scenario: Fixed files fail the commit
- **WHEN** a hook rewrites a staged file
- **THEN** the commit fails so the rewritten file is reviewed and re-staged

