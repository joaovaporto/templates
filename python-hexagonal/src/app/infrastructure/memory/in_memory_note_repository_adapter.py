from app.application.ports.note_repository_port import NoteRepositoryPort
from app.domain.entities.note import Note


class InMemoryNoteRepositoryAdapter(NoteRepositoryPort):
    """The default backend: a dict. No extra to install, nothing to run.

    Being a real adapter (not a test double) it belongs in `infrastructure/`, satisfies
    the port structurally, and is the one the container builds when settings ask for
    `memory`. Swap it for the JSON-file adapter by changing one env var; no other layer
    changes.
    """

    def __init__(self) -> None:
        self._notes: dict[str, Note] = {}

    def get(self, key: str) -> Note | None:
        return self._notes.get(key)

    def save(self, note: Note) -> None:
        self._notes[note.key] = note

    def delete(self, key: str) -> None:
        self._notes.pop(key, None)

    def all_keys(self) -> list[str]:
        return list(self._notes)
