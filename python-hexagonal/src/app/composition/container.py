from pathlib import Path

from app.application.errors import ConfigurationError
from app.application.ports.note_repository_port import NoteRepositoryPort
from app.application.usecases.save_note_usecase import SaveNoteUseCase
from app.composition.provider import Container, provider
from app.infrastructure.memory.in_memory_note_repository_adapter import (
    InMemoryNoteRepositoryAdapter,
)
from app.presentation.runner import Runner
from app.presentation.settings import BACKEND_JSONFILE, BACKEND_MEMORY, BACKENDS, Settings


class AppContainer(Container):
    """The application's object graph.

    Every provider is annotated with a *port* or a use case, never an adapter — mypy
    checks that, so a provider leaking a concrete type into a use case's constructor
    fails the type check. Adding a binding costs exactly one method; there is no
    registration table to keep in step.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    @provider
    def repository(self) -> NoteRepositoryPort:
        backend = self.settings.repository_backend
        if backend == BACKEND_MEMORY:
            return InMemoryNoteRepositoryAdapter()
        if backend == BACKEND_JSONFILE:
            # Imported here, lazily, so the `jsonfile` extra is only needed when chosen.
            from app.infrastructure.jsonfile.orjson_note_repository_adapter import (
                OrjsonNoteRepositoryAdapter,
            )

            return OrjsonNoteRepositoryAdapter(Path(self.settings.jsonfile_path))
        raise ConfigurationError(
            f"'{backend}' is not a valid repository backend. Choose one of: {', '.join(BACKENDS)}."
        )

    @provider
    def save_note(self) -> SaveNoteUseCase:
        return SaveNoteUseCase(self.repository())

    @provider
    def runner(self) -> Runner:
        return Runner(save_note=self.save_note())
