from dataclasses import dataclass, field

from app.domain.errors import DomainValidationError
from app.domain.value_objects.title import Title


@dataclass(frozen=True, slots=True, eq=False)
class Note:
    """One unit the application stores and retrieves — the example entity.

    Identity is the `key`: two Notes with the same key are the same note, so storing a
    changed body updates it rather than creating a second. Replace `Note` with your own
    entity; the surrounding layers do not care what it is, only that the domain owns it.
    """

    key: str
    title: Title
    body: str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise DomainValidationError("A note needs a key.")
        if not self.body or not self.body.strip():
            raise DomainValidationError(f"Note {self.key} has no body.")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Note):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)
