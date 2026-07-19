from pathlib import Path

from app.application.errors import MissingDependencyError
from app.application.ports.note_repository_port import NoteRepositoryPort
from app.domain.entities.note import Note
from app.domain.value_objects.title import Title


class OrjsonNoteRepositoryAdapter(NoteRepositoryPort):
    """A file-backed repository, behind the `jsonfile` extra.

    It exists to demonstrate one thing: an adapter whose dependency (`orjson`) is
    optional. The import is deferred to construction so that a core install can import
    this module — the architecture tests do — without the package present. Selecting this
    backend without the extra fails at startup with a message naming the extra, never
    with a bare ImportError at first use.
    """

    def __init__(self, path: Path) -> None:
        try:
            import orjson
        except ImportError as e:
            raise MissingDependencyError(
                adapter="OrjsonNoteRepositoryAdapter", package="orjson", extra="jsonfile"
            ) from e
        self._orjson = orjson
        self._path = path
        self._notes: dict[str, Note] = self._load()

    def _load(self) -> dict[str, Note]:
        if not self._path.exists():
            return {}
        raw = self._orjson.loads(self._path.read_bytes())
        return {
            key: Note(
                key=key,
                title=Title.build(item["title"]),
                body=item["body"],
                tags=tuple(item.get("tags", ())),
            )
            for key, item in raw.items()
        }

    def _flush(self) -> None:
        payload = {
            note.key: {"title": str(note.title), "body": note.body, "tags": list(note.tags)}
            for note in self._notes.values()
        }
        self._path.write_bytes(self._orjson.dumps(payload))

    def get(self, key: str) -> Note | None:
        return self._notes.get(key)

    def save(self, note: Note) -> None:
        self._notes[note.key] = note
        self._flush()

    def delete(self, key: str) -> None:
        if self._notes.pop(key, None) is not None:
            self._flush()

    def all_keys(self) -> list[str]:
        return list(self._notes)
