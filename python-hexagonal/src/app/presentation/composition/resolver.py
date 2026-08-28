"""Builds application objects from their constructor annotations."""

import inspect
from collections.abc import Callable
from typing import Any, cast, get_type_hints

from pydantic_settings import BaseSettings

from app.presentation.composition import conventions
from app.presentation.composition.conventions import MISSING
from app.presentation.composition.errors import ConfigurationError

_PROVIDES = "__provides__"

_INDEX: dict[type, dict[Any, Callable[[Any], Any]]] = {}


def provider[T](method: Callable[[Any], T]) -> Callable[[Any], T]:
    """Bind this method's return type by hand, overriding the conventions.

    For bindings names cannot express: an adapter wrapped in a decorator, two ports
    sharing one client, or a constructor argument that is neither a port nor a settings
    value. The declared return type is the binding, and must be a port or a use case —
    an architecture test rejects a concrete adapter.
    """

    setattr(method, _PROVIDES, True)
    return method


class Resolver[SettingsT: BaseSettings]:
    """Supplies an edge with the use cases it asks for, building each from its
    constructor annotations: a port becomes the adapter the settings select, another
    class here is built the same way, anything else is read from settings.

    Lazy, and each type is built at most once, so collaborators are shared.
    """

    #: The package whose classes this resolver may construct.
    package: str = __name__.split(".", 1)[0]

    def __init__(self, settings: SettingsT) -> None:
        self.settings: SettingsT = settings
        self._cache: dict[Any, Any] = {}
        self._path: list[str] = []
        self._trail: tuple[str, ...] | None = None

    # --- Resolution ----------------------------------------------------------------

    def get[T](self, usecase: type[T]) -> T:
        """The use case, built with its dependencies resolved. Cached per resolver."""
        return cast("T", self._resolve(usecase))

    # Any, not type[T]: mypy rejects a Protocol where type[T] is expected, so the loose
    # hop stays private and `get` above stays precise.
    def _resolve(self, hint: Any) -> Any:
        if hint in self._cache:
            return self._cache[hint]

        label = getattr(hint, "__name__", repr(hint))
        if label in self._path:
            raise ConfigurationError(
                f"Dependency cycle: {' -> '.join([*self._path, label])}. A constructor "
                f"cannot require something that requires it back."
            )

        self._path.append(label)
        try:
            # Any failure here happened while building the graph, so it earns the trail —
            # including an adapter's own, which composition must not name to catch.
            instance = self._build(hint)
        except Exception as e:
            if self._trail is None:
                self._trail = tuple(self._path)
            if len(self._path) == 1 and len(self._trail) > 1:
                e.add_note(f"while resolving: {' -> '.join(self._trail)}")
            raise
        finally:
            self._path.pop()
            if not self._path:
                self._trail = None

        self._cache[hint] = instance
        return instance

    def _build(self, hint: Any) -> Any:
        method = self._index().get(hint)
        if method is not None:
            return method(self)
        if conventions.is_port(hint):
            return self._build_adapter(hint)
        if self._is_wirable(hint):
            return self._construct(hint, conventions.prefix_of(hint))
        raise ConfigurationError(
            f"Nothing supplies {getattr(hint, '__name__', hint)!r}: it is neither a port nor "
            f"a class in '{self.package}'. Add a @provider for it."
        )

    def _build_adapter(self, port: type) -> Any:
        tech, module = conventions.choose_adapter(
            self.settings, port, f"{self.package}.infrastructure"
        )
        prefixes = conventions.arg_prefixes(conventions.core_of(port), tech)
        return self._construct(conventions.load_adapter(module), *prefixes)

    def _construct(self, cls: type, *prefixes: str) -> Any:
        try:
            # eval_str resolves string and forward-referenced annotations against the
            # module that declared the constructor.
            signature = inspect.signature(cls, eval_str=True)
        except (NameError, TypeError, ValueError) as e:
            raise ConfigurationError(
                f"{cls.__name__}'s constructor annotations cannot be resolved: {e}."
            ) from e

        kwargs: dict[str, Any] = {}
        for name, parameter in signature.parameters.items():
            if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                continue
            hint = MISSING if parameter.annotation is parameter.empty else parameter.annotation
            value = self._argument(cls, name, hint, prefixes)
            if value is MISSING:
                if parameter.default is not parameter.empty:
                    continue
                raise ConfigurationError(self._unsuppliable(cls, name, hint, prefixes))
            kwargs[name] = value
        return cls(**kwargs)

    def _argument(self, cls: type, name: str, hint: Any, prefixes: tuple[str, ...]) -> Any:
        if hint is not MISSING and self._is_resolvable(hint):
            return self._resolve(hint)

        field, value = self._from_settings(name, prefixes)
        if value is not MISSING and isinstance(hint, type) and not isinstance(value, hint):
            raise ConfigurationError(
                f"Settings.{field} is a {type(value).__name__}, but "
                f"{cls.__name__}({name}: {hint.__name__}) needs a {hint.__name__}. Annotate "
                f"the settings field as {hint.__name__} and let pydantic do the conversion."
            )
        return value

    def _from_settings(self, name: str, prefixes: tuple[str, ...]) -> tuple[str, Any]:
        """The first field the settings model declares, most specific prefix first.

        Declaring the field is what selects it, not the value it holds, so which field
        feeds an adapter can be read off `Settings` without the environment in hand.
        """
        for prefix in prefixes:
            field = f"{prefix}_{name}"
            value = conventions.field_value(self.settings, field)
            if value is not MISSING:
                return field, value
        return f"{prefixes[-1]}_{name}", MISSING

    # --- Predicates ----------------------------------------------------------------

    def _is_resolvable(self, hint: Any) -> bool:
        return hint in self._index() or conventions.is_port(hint) or self._is_wirable(hint)

    def _is_wirable(self, hint: Any) -> bool:
        """Classes this resolver may construct: ours, minus entities and DTOs, which
        arrive as call-time arguments rather than as dependencies."""
        if not isinstance(hint, type) or not hint.__module__.startswith(f"{self.package}."):
            return False
        data = (f"{self.package}.domain.", f"{self.package}.application.dtos.")
        return not hint.__module__.startswith(data)

    def _unsuppliable(self, cls: type, name: str, hint: Any, prefixes: tuple[str, ...]) -> str:
        shown = getattr(hint, "__name__", "an unannotated parameter" if hint is MISSING else hint)
        field = f"{prefixes[-1]}_{name}"
        scoped = (
            f" Name it `{prefixes[0]}_{name}` instead to keep it apart from another port's "
            f"adapter in the same backend."
            if len(prefixes) > 1
            else ""
        )
        return (
            f"Cannot supply {cls.__name__}({name}: {shown}). Add `{field}: {shown}` to "
            f"Settings (env {conventions.env_var(self.settings, field)}), give the parameter a "
            f"default, or add a @provider for {cls.__name__}.{scoped}"
        )

    # --- Introspection -------------------------------------------------------------

    def explain(self) -> str:
        """Which adapter each port resolves to, under the current settings.

        Imports nothing, so it answers even for a backend whose extra is not installed.
        """
        lines = []
        for port in conventions.ports_in(f"{self.package}.application"):
            try:
                tech, module = conventions.choose_adapter(
                    self.settings, port, f"{self.package}.infrastructure"
                )
            except Exception as e:
                lines.append(f"{port.__name__:<24} !! {e}")
            else:
                lines.append(f"{port.__name__:<24} -> {tech:<10} {module}")
        return "\n".join(lines)

    # --- Providers -----------------------------------------------------------------

    @classmethod
    def provides(cls) -> dict[str, type]:
        """Map each provider's method name to the type it supplies."""
        found: dict[str, type] = {}
        for name in dir(cls):
            attribute = getattr(cls, name, None)
            if attribute is None or not getattr(attribute, _PROVIDES, False):
                continue
            hints = get_type_hints(attribute)
            if "return" in hints:
                found[name] = hints["return"]
        return found

    @classmethod
    def _index(cls) -> dict[Any, Callable[[Any], Any]]:
        index = _INDEX.get(cls)
        if index is None:
            index = {}
            for name, supplied in cls.provides().items():
                if supplied in index:
                    raise ConfigurationError(
                        f"Two providers supply {supplied.__name__} in {cls.__name__}; a type "
                        f"has one binding."
                    )
                index[supplied] = getattr(cls, name)
            _INDEX[cls] = index
        return index
