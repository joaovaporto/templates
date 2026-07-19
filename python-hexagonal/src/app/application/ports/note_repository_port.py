from typing import Protocol, runtime_checkable

from app.domain.entities.note import Note


@runtime_checkable
class NoteRepositoryPort(Protocol):
    """What the core needs from a store of notes.

    Expressed in domain terms only: no SQL, no HTTP, no file paths. The in-memory and
    JSON-file adapters are two implementations; nothing here assumes either. This is the
    seam: use cases depend on this Protocol, and the composition root decides which
    adapter satisfies it.
    """

    def get(self, key: str) -> Note | None:
        """Return the stored note, or None when the key is unknown."""
        ...

    def save(self, note: Note) -> None:
        """Insert or overwrite the note under its key."""
        ...

    def delete(self, key: str) -> None:
        """Remove the note. A no-op when the key is unknown."""
        ...

    def all_keys(self) -> list[str]:
        """Every stored key."""
        ...
