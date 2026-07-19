from app.application.ports.note_repository_port import NoteRepositoryPort
from app.domain.entities.note import Note


class FakeNoteRepository(NoteRepositoryPort):
    """A test double for the repository port.

    It lives under `tests/`, not `infrastructure/`, on purpose: a fake is a testing
    artifact, not a production adapter. Because the use case depends on the port and not
    on any adapter, this is all a unit test needs — no container, no settings, no I/O.
    """

    def __init__(self) -> None:
        self.notes: dict[str, Note] = {}

    def get(self, key: str) -> Note | None:
        return self.notes.get(key)

    def save(self, note: Note) -> None:
        self.notes[note.key] = note

    def delete(self, key: str) -> None:
        self.notes.pop(key, None)

    def all_keys(self) -> list[str]:
        return list(self.notes)
