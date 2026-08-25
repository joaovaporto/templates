"""Every use case, on every backend, must build.

Since no module names an adapter, this is where a typo in a filename, a port nobody
implements, or a constructor argument no setting supplies fails.
"""

import importlib
import itertools
from pathlib import Path

import pytest

from app.infrastructure.errors import MissingDependencyError
from app.presentation.composition import conventions
from app.presentation.composition.resolver import Resolver
from app.presentation.settings import Settings
from tests.support import build_settings

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "app"
INFRASTRUCTURE = "app.infrastructure"


def use_cases() -> list[type]:
    found: list[type] = []
    for path in sorted((SRC / "application" / "usecases").glob("*_usecase.py")):
        module = importlib.import_module(f"app.application.usecases.{path.stem}")
        found += [
            value
            for value in vars(module).values()
            if isinstance(value, type)
            and value.__name__.endswith(conventions.USECASE_SUFFIX)
            and value.__module__ == module.__name__
        ]
    return found


def backend_combinations() -> list[dict[str, str]]:
    """The cross product of every declared `*_backend` field's legal values."""
    choices: dict[str, list[str]] = {}
    for port in conventions.ports_in("app.application"):
        field = conventions.backend_field(port)
        if field not in Settings.model_fields:
            continue
        choices[field] = [
            tech
            for tech in conventions.techs(INFRASTRUCTURE)
            if conventions.adapter_modules(INFRASTRUCTURE, tech, conventions.core_of(port))
        ]
    fields = sorted(choices)
    return [
        dict(zip(fields, combination, strict=True))
        for combination in itertools.product(*(choices[field] for field in fields))
    ] or [{}]


@pytest.mark.parametrize("target", use_cases(), ids=lambda t: t.__name__)
@pytest.mark.parametrize(
    "backends", backend_combinations(), ids=lambda b: "+".join(b.values()) or "defaults"
)
def test_the_graph_builds(target: type, backends: dict[str, str], tmp_path: Path) -> None:
    # tmp_path so a file-backed adapter never writes into the repository.
    settings = build_settings(jsonfile_path=tmp_path / "notes.json", **backends)
    try:
        instance: object = Resolver(settings).get(target)
    except MissingDependencyError as e:
        pytest.skip(str(e))
    assert isinstance(instance, target)
