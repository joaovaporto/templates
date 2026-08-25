"""Names in, classes out — the conventions behind `Resolver.get()`.

Package contents are read from import metadata, so listing a backend never imports it.
Only the adapter actually selected is loaded, by `load_adapter`.
"""

import importlib
import importlib.util
import pkgutil
import re
from types import ModuleType
from typing import Any, TypeGuard

from pydantic_settings import BaseSettings

from app.presentation.composition.errors import ConfigurationError

#: Distinguishes "no value" from a legitimately falsy one.
MISSING: Any = object()

PORT_SUFFIX = "Port"
ADAPTER_SUFFIX = "Adapter"
USECASE_SUFFIX = "UseCase"
BACKEND_SUFFIX = "_backend"


def is_port(hint: object) -> TypeGuard[type]:
    # On 3.12 the private attribute is the only spelling; use typing.is_protocol on 3.13.
    if not isinstance(hint, type) or not getattr(hint, "_is_protocol", False):
        return False
    return hint.__name__.endswith(PORT_SUFFIX)


def snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def core_of(port: type) -> str:
    """`NoteRepositoryPort` -> `note_repository`, the stem every other rule is built on."""
    return snake(port.__name__.removesuffix(PORT_SUFFIX))


def prefix_of(cls: type) -> str:
    """The settings prefix a non-adapter class reads its scalar arguments under."""
    return snake(cls.__name__.removesuffix(USECASE_SUFFIX))


def backend_field(port: type) -> str:
    return f"{core_of(port)}{BACKEND_SUFFIX}"


def field_value(settings: BaseSettings, field: str) -> Any:
    if field not in type(settings).model_fields:
        return MISSING
    return getattr(settings, field)


def env_var(settings: BaseSettings, field: str) -> str:
    prefix = settings.model_config.get("env_prefix") or ""
    return f"{prefix}{field}".upper()


def _search_locations(package: str) -> list[str] | None:
    try:
        spec = importlib.util.find_spec(package)
    except (ImportError, ValueError):
        return None
    if spec is None or spec.submodule_search_locations is None:
        return None
    return list(spec.submodule_search_locations)


def _defined_in(module: ModuleType) -> list[Any]:
    """The module's own classes, not the ones it imported."""
    return [v for v in vars(module).values() if getattr(v, "__module__", None) == module.__name__]


def techs(infrastructure: str) -> tuple[str, ...]:
    """Every backend package — the legal values of a `*_backend` setting."""
    locations = _search_locations(infrastructure)
    if locations is None:
        return ()
    return tuple(sorted(m.name for m in pkgutil.iter_modules(locations) if m.ispkg))


def adapters_in(infrastructure: str, tech: str) -> tuple[str, ...]:
    """The adapter module stems a backend package holds. Imports nothing."""
    locations = _search_locations(f"{infrastructure}.{tech}")
    if locations is None:
        return ()
    return tuple(
        sorted(m.name for m in pkgutil.iter_modules(locations) if m.name.endswith("_adapter"))
    )


def ports_in(application: str) -> tuple[type, ...]:
    """Every port Protocol. Imports application modules only, never an adapter."""
    locations = _search_locations(f"{application}.ports")
    if locations is None:
        return ()
    found: list[type] = []
    for entry in sorted(pkgutil.iter_modules(locations), key=lambda m: m.name):
        module = importlib.import_module(f"{application}.ports.{entry.name}")
        found += [value for value in _defined_in(module) if is_port(value)]
    return tuple(found)


def implements(stem: str, core: str) -> bool:
    """Does this adapter module stem implement `core`?

    Matched on the stem, so an adapter class may keep the name of the library it wraps.
    """
    suffix = f"{core}_adapter"
    return stem == suffix or stem.endswith(f"_{suffix}")


def adapter_modules(infrastructure: str, tech: str, core: str) -> tuple[str, ...]:
    return tuple(
        f"{infrastructure}.{tech}.{stem}"
        for stem in adapters_in(infrastructure, tech)
        if implements(stem, core)
    )


def _source_dir(infrastructure: str, *parts: str) -> str:
    return "/".join(("src", *infrastructure.split("."), *parts))


def choose_adapter(settings: BaseSettings, port: type, infrastructure: str) -> tuple[str, str]:
    """Which backend package and module implement `port`. Nothing is imported yet."""
    core = core_of(port)
    field = backend_field(port)
    available = techs(infrastructure)
    chosen = field_value(settings, field)

    if chosen is MISSING:
        return _sole_implementation(settings, port, infrastructure, available)

    if chosen not in available:
        implementing = [tech for tech in available if adapter_modules(infrastructure, tech, core)]
        raise ConfigurationError(
            f"{env_var(settings, field)} is '{chosen}', which is not a backend package in "
            f"{_source_dir(infrastructure)}/. {port.__name__} is implemented by: "
            f"{', '.join(implementing) or 'nothing yet'}."
        )

    modules = adapter_modules(infrastructure, chosen, core)
    if not modules:
        holds = ", ".join(f"{stem}.py" for stem in adapters_in(infrastructure, chosen))
        raise ConfigurationError(
            f"{env_var(settings, field)} is '{chosen}', but that backend has no "
            f"{port.__name__} adapter. Expected a module matching '*_{core}_adapter.py' in "
            f"{_source_dir(infrastructure, chosen)}/, which holds: {holds or 'no adapters'}."
        )
    if len(modules) > 1:
        raise ConfigurationError(
            f"Backend '{chosen}' has {len(modules)} {port.__name__} adapters "
            f"({', '.join(modules)}). One backend implements a port once."
        )
    return chosen, modules[0]


def _sole_implementation(
    settings: BaseSettings, port: type, infrastructure: str, available: tuple[str, ...]
) -> tuple[str, str]:
    """No `<core>_backend` field, so the port must have exactly one implementation."""
    core, field = core_of(port), backend_field(port)
    candidates = [
        (tech, module)
        for tech in available
        for module in adapter_modules(infrastructure, tech, core)
    ]
    if not candidates:
        raise ConfigurationError(
            f"Nothing implements {port.__name__}. Create "
            f"{_source_dir(infrastructure, '<backend>', f'<library>_{core}_adapter.py')} "
            f"with one class ending in '{ADAPTER_SUFFIX}'. Backend packages present: "
            f"{', '.join(available) or 'none'}."
        )
    if len(candidates) > 1:
        raise ConfigurationError(
            f"{port.__name__} has {len(candidates)} implementations "
            f"({', '.join(tech for tech, _ in candidates)}). Add `{field}: str` to Settings "
            f"(env {env_var(settings, field)}) to say which one this application uses."
        )
    return candidates[0]


def load_adapter(module_name: str) -> type:
    """Import the chosen adapter module — and only it."""
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ConfigurationError(
            f"{module_name} could not be imported: {e}. An adapter wrapping an optional "
            f"package must defer that import into __init__ and raise MissingDependencyError, "
            f"so a missing extra names itself instead of failing at import time."
        ) from e

    found = [
        value
        for value in _defined_in(module)
        if isinstance(value, type) and value.__name__.endswith(ADAPTER_SUFFIX)
    ]
    if len(found) != 1:
        raise ConfigurationError(
            f"{module_name} must define exactly one *{ADAPTER_SUFFIX} class; found "
            f"{[c.__name__ for c in found] or 'none'}."
        )
    return found[0]
