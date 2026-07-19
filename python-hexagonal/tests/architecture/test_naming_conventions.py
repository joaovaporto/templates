"""The file-per-artifact rules, which import-linter cannot express.

These are tests rather than a lint plugin so that breaking a convention fails in the same
place, and with the same feedback, as breaking anything else. An architecture rule nobody
enforces is a comment.
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "app"

DOMAIN = SRC / "domain"
APPLICATION = SRC / "application"
INFRASTRUCTURE = SRC / "infrastructure"
PRESENTATION = SRC / "presentation"
COMPOSITION = SRC / "composition"


def modules(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if p.name != "__init__.py"]


def classes_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.name for n in tree.body if isinstance(n, ast.ClassDef)]


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
    def test_every_dto_declares_its_direction(self) -> None:
        for path in modules(APPLICATION / "dtos"):
            assert path.stem.endswith(("_input", "_output")), (
                f"{path.name} must end with '_input' (toward the core) or '_output' (away from it)"
            )


class TestUseCases:
    def test_each_use_case_file_carries_the_usecase_suffix(self) -> None:
        for path in modules(APPLICATION / "usecases"):
            assert path.stem.endswith("_usecase"), f"{path.name} must end with '_usecase'"

    def test_each_use_case_file_defines_exactly_one_use_case(self) -> None:
        for path in modules(APPLICATION / "usecases"):
            found = [c for c in classes_in(path) if c.endswith("UseCase")]
            assert len(found) == 1, f"{path.name} must define one use case, found {found}"
