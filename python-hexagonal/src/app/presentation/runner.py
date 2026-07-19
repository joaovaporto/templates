import logging

from app.application.dtos.save_note_input import SaveNoteInput
from app.application.usecases.save_note_usecase import SaveNoteUseCase

logger = logging.getLogger(__name__)


class Runner:
    """The application's entry behaviour, handed its collaborators.

    Note what this module does not contain: any mention of a dict, a file, or `orjson`.
    It receives use cases. A concrete adapter is named exactly once in the runtime path —
    in `composition/container.py` — and importing one here would fail the architecture
    check. Replace this demo `run()` with your CLI loop, HTTP app, or worker.
    """

    def __init__(self, save_note: SaveNoteUseCase) -> None:
        self._save_note = save_note

    def run(self) -> None:
        result = self._save_note.execute(
            SaveNoteInput(key="welcome", title="Welcome", body="Your first note.")
        )
        logger.info("save %s -> %s", result.key, result.outcome.value)
