"""A `@provider` binds a port or a use case, never a concrete adapter."""

import pytest

from app.presentation.composition.resolver import Resolver

pytestmark = pytest.mark.unit


def test_no_provider_is_typed_to_an_infrastructure_class() -> None:
    for name, supplied in Resolver.provides().items():
        module = getattr(supplied, "__module__", "")
        assert not module.startswith("app.infrastructure"), (
            f"provider '{name}' is typed to {supplied.__name__} in {module}; "
            f"providers must return ports or use cases, never adapters"
        )


def test_no_type_has_two_providers() -> None:
    provided = Resolver.provides()
    supplied = list(provided.values())
    assert len(set(supplied)) == len(supplied), (
        f"two providers supply the same type in {Resolver.__name__}; "
        f"a type has one binding: {provided}"
    )
