import pytest

from app.application.dtos.save_note_input import SaveNoteInput
from app.application.dtos.save_note_output import SaveOutcome
from app.application.usecases.save_note_usecase import SaveNoteUseCase
from tests.fakes.fake_note_repository import FakeNoteRepository

pytestmark = pytest.mark.unit


def test_saving_an_unknown_key_creates() -> None:
    repository = FakeNoteRepository()
    usecase = SaveNoteUseCase(repository)

    result = usecase.execute(SaveNoteInput(key="a", title="A", body="first"))

    assert result.outcome is SaveOutcome.CREATED
    assert repository.get("a") is not None


def test_saving_an_existing_key_updates() -> None:
    repository = FakeNoteRepository()
    usecase = SaveNoteUseCase(repository)
    usecase.execute(SaveNoteInput(key="a", title="A", body="first"))

    result = usecase.execute(SaveNoteInput(key="a", title="A", body="second"))

    assert result.outcome is SaveOutcome.UPDATED
    note = repository.get("a")
    assert note is not None and note.body == "second"


def test_empty_body_is_rejected_before_the_use_case_runs() -> None:
    with pytest.raises(ValueError):
        SaveNoteInput(key="a", title="A", body="   ")
