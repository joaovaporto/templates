from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

_PROVIDES = "__provides__"


def provider[T](method: Callable[[Any], T]) -> Callable[[Any], T]:
    """Mark a container method as supplying its return type.

    Two properties, and they are the whole point:

    - **Lazy**: nothing is built until something asks for it. Choosing the in-memory
      backend means the JSON-file adapter is never constructed and its extra never needs
      to be installed.
    - **Cached**: a provider yields the same instance for the life of its container, so
      collaborators share one connection rather than opening one apiece.

    The declared return type is recorded as what the method supplies, which is what lets
    `Container.provides` answer "which method gives me a NoteRepositoryPort?" without a
    registration table to keep in step.
    """

    @wraps(method)
    def resolve(self: Any) -> T:
        cache = self._cache
        name = method.__name__
        if name not in cache:
            cache[name] = method(self)
        return cache[name]  # type: ignore[no-any-return]

    setattr(resolve, _PROVIDES, True)
    return resolve


class Container:
    """Base for the application's object graph.

    Subclasses live in this package — the composition root — because they are the only
    code allowed to name a concrete adapter. A module under `presentation/` gets its
    collaborators handed to it and could not construct one if it tried: the import would
    not survive the architecture check.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    @classmethod
    def provides(cls) -> dict[str, type]:
        """Map each provider's method name to the type it supplies.

        Read off the return annotations, so adding a provider adds an entry with no
        second place to update. Used by the tests to assert providers are typed to ports
        rather than to concrete adapters.
        """
        found: dict[str, type] = {}
        for name in dir(cls):
            attribute = getattr(cls, name, None)
            if attribute is None or not getattr(attribute, _PROVIDES, False):
                continue
            hints = get_type_hints(attribute)
            if "return" in hints:
                found[name] = hints["return"]
        return found
