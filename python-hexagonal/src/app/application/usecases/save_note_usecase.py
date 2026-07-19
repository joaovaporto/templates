import logging

from app.application.dtos.save_note_input import SaveNoteInput
from app.application.dtos.save_note_output import SaveNoteOutput
from app.application.errors import RepositoryUnavailableError
from app.application.ports.note_repository_port import NoteRepositoryPort

logger = logging.getLogger(__name__)


class SaveNoteUseCase:
    """Upsert one note, whatever produced it and wherever it is stored.

    Knows nothing about the backend: collaborators arrive as ports through the
    constructor, and a container in the composition root decides which. This is what
    makes the use case unit-testable with a fake and no infrastructure import.
    """

    def __init__(self, repository: NoteRepositoryPort) -> None:
        self._repository = repository

    def execute(self, request: SaveNoteInput) -> SaveNoteOutput:
        note = request.to_note()

        try:
            existed = self._repository.get(note.key) is not None
            self._repository.save(note)
            if existed:
                logger.info("Updated note %s", note.key)
                return SaveNoteOutput.updated(note.key)
            logger.info("Created note %s", note.key)
            return SaveNoteOutput.created(note.key)

        except RepositoryUnavailableError as e:
            # Returned, not raised: one failed note must not abort a batch of a thousand
            # others. The caller decides what a failure is worth.
            logger.error("Failed to save %s: %s", note.key, e)
            return SaveNoteOutput.failed(note.key, str(e))
