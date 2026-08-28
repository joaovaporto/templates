"""The file-per-artifact rules, which import-linter cannot express.

These are tests rather than a lint plugin so that breaking a convention fails in the same
place, and with the same feedback, as breaking anything else. An architecture rule nobody
enforces is a comment.
"""

import ast
import importlib
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.presentation.composition import conventions
from app.presentation.settings import Settings

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "app"

DOMAIN = SRC / "domain"
APPLICATION = SRC / "application"
INFRASTRUCTURE = SRC / "infrastructure"
PRESENTATION = SRC / "presentation"
COMPOSITION = PRESENTATION / "composition"

INFRASTRUCTURE_PACKAGE = "app.infrastructure"
DTOS = APPLICATION / "dtos"
DTO_PACKAGE = "app.application.dtos"


def modules(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if p.name != "__init__.py"]


def classes_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.name for n in tree.body if isinstance(n, ast.ClassDef)]


def dto_classes(path: Path) -> list[type]:
    """The `*Dto` classes a module defines, imported so `model_config` is the effective one.

    Read from the class rather than the source because a DTO may inherit its config from a
    shared base, which an AST check of one file would miss.
    """
    module = importlib.import_module(f"{DTO_PACKAGE}.{path.stem}")
    return [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and value.__module__ == module.__name__
        and value.__name__.endswith("Dto")
    ]


def raised_names(source: str) -> list[str]:
    """The exception names a module raises, by their final identifier."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exception = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if isinstance(exception, ast.Name):
            found.append(exception.id)
        elif isinstance(exception, ast.Attribute):
            found.append(exception.attr)
    return found


class TestPorts:
    def test_every_port_file_carries_the_port_suffix(self) -> None:
        for path in modules(APPLICATION / "ports"):
            assert path.stem.endswith("_port"), f"{path.name} must end with '_port'"

    def test_no_port_lives_outside_application_ports(self) -> None:
        for layer in (DOMAIN, INFRASTRUCTURE, PRESENTATION):
            offenders = [p for p in modules(layer) if p.stem.endswith("_port")]
            assert not offenders, f"Ports belong in application/ports/: {offenders}"

    def test_every_port_defines_exactly_one_protocol(self) -> None:
        for path in modules(APPLICATION / "ports"):
            found = [c for c in classes_in(path) if c.endswith("Port")]
            assert len(found) == 1, f"{path.name} must define exactly one Port, found {found}"


class TestAdapters:
    def test_every_adapter_file_carries_the_adapter_suffix(self) -> None:
        for path in modules(INFRASTRUCTURE):
            if any(c.endswith("Adapter") for c in classes_in(path)):
                assert path.stem.endswith("_adapter"), f"{path.name} must end with '_adapter'"

    def test_no_adapter_lives_outside_infrastructure(self) -> None:
        for layer in (DOMAIN, APPLICATION, PRESENTATION):
            offenders = [p for p in modules(layer) if p.stem.endswith("_adapter")]
            assert not offenders, f"Adapters belong in infrastructure/: {offenders}"

    def test_every_adapter_file_defines_exactly_one_adapter(self) -> None:
        for path in modules(INFRASTRUCTURE):
            if not path.stem.endswith("_adapter"):
                continue
            found = [c for c in classes_in(path) if c.endswith("Adapter")]
            assert len(found) == 1, f"{path.name} must define one adapter, found {found}"


class TestDtos:
    """A DTO carries proven invariants, so a use case can trust what it is handed.

    The rules below are the structural half of that contract — construction validates, and
    nothing can undo or bypass the validation afterwards. Whether a field needs a rule
    beyond its type is a domain judgement, so no test demands a validator.
    """

    def test_every_dto_declares_its_direction(self) -> None:
        for path in modules(DTOS):
            assert path.stem.endswith(("_input_dto", "_output_dto")), (
                f"{path.name} must end with '_input_dto' (toward the core) or "
                f"'_output_dto' (away from it)"
            )

    def test_every_dto_validates_on_construction(self) -> None:
        for path in modules(DTOS):
            for dto in dto_classes(path):
                assert issubclass(dto, BaseModel), (
                    f"{path.name}: {dto.__name__} must be a pydantic BaseModel, so building "
                    f"it validates. A dataclass or TypedDict carries data, not proof."
                )

    def test_every_dto_is_frozen(self) -> None:
        for path in modules(DTOS):
            for dto in dto_classes(path):
                config = getattr(dto, "model_config", {})
                assert config.get("frozen") is True, (
                    f"{path.name}: {dto.__name__} must set frozen=True, so proof established "
                    f"at construction cannot be invalidated by a later assignment"
                )

    def test_every_dto_forbids_undeclared_fields(self) -> None:
        for path in modules(DTOS):
            for dto in dto_classes(path):
                config = getattr(dto, "model_config", {})
                assert config.get("extra") == "forbid", (
                    f"{path.name}: {dto.__name__} must set extra='forbid', so no undeclared "
                    f"field rides along unvalidated"
                )

    def test_each_dto_module_defines_exactly_one_dto(self) -> None:
        """Supporting types may share the file; only `*Dto` classes are counted."""
        for path in modules(DTOS):
            found = [c for c in classes_in(path) if c.endswith("Dto")]
            assert len(found) == 1, f"{path.name} must define one *Dto class, found {found}"


# A use case that catches a validation error without raising one is still trusting its
# input; only raising is the smell. The fixtures pin both halves of that distinction.
CATCHES_A_VALIDATION_ERROR = """
def execute(self, request):
    try:
        return self._store(request.to_note())
    except DomainValidationError as e:
        return Output.failed(str(e))
"""

RAISES_A_VALIDATION_ERROR = """
def execute(self, request):
    if not request.key:
        raise DomainValidationError("A note needs a key.")
"""


class TestUseCasesTrustTheirInput:
    """A use case receives proof, not data to check.

    An input DTO cannot be built unless the business rules hold, so a use case that
    re-validates has turned that proof back into a bag of fields. This is the half of the
    DTO contract that decays in practice, so it is the half worth a test.
    """

    def test_no_use_case_raises_a_validation_error(self) -> None:
        for path in modules(APPLICATION / "usecases"):
            source = path.read_text(encoding="utf-8")
            offenders = [n for n in raised_names(source) if n.endswith("ValidationError")]
            assert not offenders, (
                f"{path.name} raises {', '.join(offenders)}. A use case receives proof, not "
                f"data to check: put the rule in the input DTO, which then cannot be built "
                f"without it"
            )

    def test_catching_a_validation_error_is_allowed(self) -> None:
        assert not [
            n for n in raised_names(CATCHES_A_VALIDATION_ERROR) if n.endswith("ValidationError")
        ]

    def test_raising_one_is_what_the_rule_catches(self) -> None:
        assert [
            n for n in raised_names(RAISES_A_VALIDATION_ERROR) if n.endswith("ValidationError")
        ] == ["DomainValidationError"]


class TestUseCases:
    def test_each_use_case_file_carries_the_usecase_suffix(self) -> None:
        for path in modules(APPLICATION / "usecases"):
            assert path.stem.endswith("_usecase"), f"{path.name} must end with '_usecase'"

    def test_each_use_case_file_defines_exactly_one_use_case(self) -> None:
        for path in modules(APPLICATION / "usecases"):
            found = [c for c in classes_in(path) if c.endswith("UseCase")]
            assert len(found) == 1, f"{path.name} must define one use case, found {found}"


class TestWiringNames:
    """The names `Container.get()` reads to find an adapter."""

    @staticmethod
    def cores() -> set[str]:
        """One per port, read from the filename: `note_repository_port.py` -> `note_repository`."""
        return {path.stem.removesuffix("_port") for path in modules(APPLICATION / "ports")}

    @staticmethod
    def backends_implementing(core: str) -> list[str]:
        return [
            tech
            for tech in conventions.techs(INFRASTRUCTURE_PACKAGE)
            if conventions.adapter_modules(INFRASTRUCTURE_PACKAGE, tech, core)
        ]

    def test_every_adapter_module_names_a_known_port(self) -> None:
        cores = self.cores()
        for path in modules(INFRASTRUCTURE):
            if not path.stem.endswith("_adapter"):
                continue
            assert any(conventions.implements(path.stem, core) for core in cores), (
                f"{path.name} matches no port. Its stem must end with '_<port_core>_adapter' "
                f"for one of: {', '.join(sorted(cores))}"
            )

    def test_the_tree_is_as_flat_as_resolution_assumes(self) -> None:
        """A port and an adapter are found by listing one directory, never by walking.

        Nesting either would leave it invisible to the resolver while every other rule
        still passed, so the depth is a rule in its own right.
        """
        for path in modules(APPLICATION / "ports"):
            assert path.parent == APPLICATION / "ports", (
                f"{path.relative_to(SRC)} is nested; a port lives directly in application/ports/"
            )
        for path in modules(INFRASTRUCTURE):
            if not path.stem.endswith("_adapter"):
                continue
            assert path.parent.parent == INFRASTRUCTURE, (
                f"{path.relative_to(SRC)} is nested; an adapter lives directly in "
                f"infrastructure/<backend>/, one level down and no deeper"
            )

    def test_every_port_has_at_least_one_adapter(self) -> None:
        for core in sorted(self.cores()):
            assert self.backends_implementing(core), (
                f"No adapter implements '{core}'. Create "
                f"src/app/infrastructure/<backend>/<library>_{core}_adapter.py"
            )

    def test_a_port_with_two_backends_declares_a_backend_setting(self) -> None:
        for core in sorted(self.cores()):
            backends = self.backends_implementing(core)
            if len(backends) < 2:
                continue
            assert f"{core}_backend" in Settings.model_fields, (
                f"'{core}' is implemented by {', '.join(backends)}. Add "
                f"`{core}_backend: str` to Settings to say which one this application uses"
            )

    def test_every_backend_setting_defaults_to_a_real_package(self) -> None:
        available = conventions.techs(INFRASTRUCTURE_PACKAGE)
        for name, field in Settings.model_fields.items():
            if not name.endswith("_backend"):
                continue
            assert field.default in available, (
                f"Settings.{name} defaults to '{field.default}', which is not a subpackage "
                f"of src/app/infrastructure/. Available: {', '.join(available)}"
            )


class TestEdgeLookups:
    """An edge may resolve use cases, and only use cases.

    The composition module is exempt: naming what an edge may not is its job.
    """

    @staticmethod
    def use_case_names() -> set[str]:
        return {
            name
            for path in modules(APPLICATION / "usecases")
            for name in classes_in(path)
            if name.endswith(conventions.USECASE_SUFFIX)
        }

    def test_an_edge_resolves_only_real_use_cases(self) -> None:
        known = self.use_case_names()
        for path in modules(PRESENTATION):
            if path.is_relative_to(COMPOSITION):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
                    continue
                target = node.args[0]
                # A dict lookup passes a string, not an identifier.
                if not isinstance(target, ast.Name) or not target.id[:1].isupper():
                    continue
                assert target.id in known, (
                    f"{path.name} resolves {target.id}, which is not a use case. An edge "
                    f"may ask for use cases only; known: {', '.join(sorted(known))}"
                )
