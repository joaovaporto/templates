import pytest

from app.application.dtos.save_note_input_dto import SaveNoteInputDto
from app.application.usecases.list_notes_usecase import ListNotesUseCase
from app.application.usecases.save_note_usecase import SaveNoteUseCase
from tests.fakes.fake_clock import FROZEN, FakeClock
from tests.fakes.fake_note_repository import FakeNoteRepository

pytestmark = pytest.mark.unit


def test_listing_an_empty_repository_returns_no_keys() -> None:
    result = ListNotesUseCase(FakeNoteRepository(), FakeClock()).execute()

    assert result.keys == ()
    assert result.listed_at == FROZEN


def test_listing_reports_every_saved_key() -> None:
    repository = FakeNoteRepository()
    save = SaveNoteUseCase(repository)
    save.execute(SaveNoteInputDto(key="a", title="A", body="first"))
    save.execute(SaveNoteInputDto(key="b", title="B", body="second"))

    result = ListNotesUseCase(repository, FakeClock()).execute()

    assert result.keys == ("a", "b")
