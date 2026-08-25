from app.application.dtos.list_notes_output_dto import ListNotesOutputDto
from app.application.ports.clock_port import ClockPort
from app.application.ports.note_repository_port import NoteRepositoryPort


class ListNotesUseCase:
    """Report what is stored, and when."""

    def __init__(self, repository: NoteRepositoryPort, clock: ClockPort) -> None:
        self._repository = repository
        self._clock = clock

    def execute(self) -> ListNotesOutputDto:
        return ListNotesOutputDto(
            keys=tuple(self._repository.all_keys()), listed_at=self._clock.now()
        )
