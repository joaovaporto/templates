import logging

from app.application.dtos.save_note_input_dto import SaveNoteInputDto
from app.application.usecases.list_notes_usecase import ListNotesUseCase
from app.application.usecases.save_note_usecase import SaveNoteUseCase
from app.presentation.composition.resolver import Resolver
from app.presentation.settings import Settings

logger = logging.getLogger(__name__)


class Runner:
    """The application's entry behaviour, asking for each use case where it uses it.

    Suited to an edge that fans out — a CLI dispatcher, a router, a worker loop. An edge
    that drives a single use case should take it through the constructor instead, where
    the dependency stays visible in the signature.
    """

    def __init__(self, resolver: Resolver[Settings]) -> None:
        self._resolver = resolver

    def run(self) -> None:
        saved = self._resolver.get(SaveNoteUseCase).execute(
            SaveNoteInputDto(key="welcome", title="Welcome", body="Your first note.")
        )
        logger.info("save %s -> %s", saved.key, saved.outcome.value)

        listed = self._resolver.get(ListNotesUseCase).execute()
        logger.info("stored %s at %s", listed.keys, listed.listed_at.isoformat())
