"""The container binds ports, not adapters — checked structurally.

If a provider returned a concrete adapter type, a use case constructed from it would
still work, but the seam would be gone. This test keeps providers honest: every one
supplies a Protocol (a port) or a use case, never a class from `infrastructure/`.
"""

import pytest

from app.composition.container import AppContainer

pytestmark = pytest.mark.unit


def test_no_provider_is_typed_to_an_infrastructure_class() -> None:
    for name, supplied in AppContainer.provides().items():
        module = getattr(supplied, "__module__", "")
        assert not module.startswith("app.infrastructure"), (
            f"provider '{name}' is typed to {supplied.__name__} in {module}; "
            f"providers must return ports or use cases, never adapters"
        )
