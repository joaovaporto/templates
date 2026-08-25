"""The resolver's own behaviour: what it builds, what it reuses, and how it fails.

The failure tests assert on the message, not only the exception type: a broken convention
must say which file, field, or environment variable would fix it.
"""

from datetime import datetime
from pathlib import Path
from typing import Protocol

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.application.dtos.save_note_input_dto import SaveNoteInputDto
from app.application.ports.note_repository_port import NoteRepositoryPort
from app.application.usecases.list_notes_usecase import ListNotesUseCase
from app.application.usecases.save_note_usecase import SaveNoteUseCase
from app.presentation.composition.errors import ConfigurationError
from app.presentation.composition.resolver import Resolver, provider
from app.presentation.runner import Runner
from app.presentation.settings import Settings
from tests.fakes.fake_note_repository import FakeNoteRepository
from tests.support import build_settings as settings

pytestmark = pytest.mark.unit


# `package = "tests"` points a resolver at this file, so a synthetic port can exercise
# the failure paths without adding anything to src/.


class LocalResolver(Resolver[Settings]):
    package = "tests"


class WidgetPort(Protocol):
    def spin(self) -> None: ...


class NeedsWidgetUseCase:
    def __init__(self, widget: WidgetPort) -> None:
        self.widget = widget


class NeedsLimitUseCase:
    def __init__(self, limit: int) -> None:
        self.limit = limit


class PingUseCase:
    def __init__(self, pong: "PongUseCase") -> None:
        self.pong = pong


class PongUseCase:
    def __init__(self, ping: PingUseCase) -> None:
        self.ping = ping


class TestResolution:
    def test_a_use_case_is_built_from_its_annotations(self) -> None:
        assert isinstance(Resolver(settings()).get(SaveNoteUseCase), SaveNoteUseCase)

    def test_each_type_is_built_once(self) -> None:
        resolver = Resolver(settings())
        assert resolver.get(SaveNoteUseCase) is resolver.get(SaveNoteUseCase)

    def test_collaborators_are_shared_across_the_graph(self) -> None:
        resolver = Resolver(settings())
        assert resolver.get(SaveNoteUseCase)._repository is (
            resolver.get(ListNotesUseCase)._repository
        )

    def test_two_use_cases_receive_the_same_adapter(self) -> None:
        resolver = Resolver(settings())
        assert resolver.get(SaveNoteUseCase)._repository is (
            resolver.get(ListNotesUseCase)._repository
        )

    def test_a_port_with_one_implementation_needs_no_setting(self) -> None:
        clock = Resolver(settings()).get(ListNotesUseCase)._clock
        assert isinstance(clock.now(), datetime)

    def test_an_adapter_argument_comes_from_settings(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.json"
        resolver = Resolver(settings(note_repository_backend="jsonfile", jsonfile_path=path))
        resolver.get(SaveNoteUseCase).execute(SaveNoteInputDto(key="a", title="A", body="b"))
        assert path.exists()


# --- Providers as overrides --------------------------------------------------------


class OverridingResolver(Resolver[Settings]):
    @provider
    def note_repository(self) -> NoteRepositoryPort:
        return FakeNoteRepository()


class TestProviderOverrides:
    def test_a_provider_wins_over_the_convention(self) -> None:
        resolver = OverridingResolver(settings())
        resolver.get(SaveNoteUseCase).execute(SaveNoteInputDto(key="a", title="A", body="b"))

        repository = resolver.get(SaveNoteUseCase)._repository
        assert isinstance(repository, FakeNoteRepository)
        assert repository.notes["a"].body == "b"

    def test_an_override_is_shared_like_any_other_binding(self) -> None:
        resolver = OverridingResolver(settings())
        assert resolver.get(SaveNoteUseCase)._repository is (
            resolver.get(ListNotesUseCase)._repository
        )

    def test_a_resolver_declares_no_bindings_by_default(self) -> None:
        assert Resolver.provides() == {}


# --- Failures ----------------------------------------------------------------------


class BareSettings(BaseSettings):
    """Declares no `note_repository_backend`, so that port becomes ambiguous."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    jsonfile_path: Path = Path("notes.json")


class BareResolver(Resolver[BareSettings]):
    pass


class TestFailures:
    def test_unknown_backend_lists_the_real_ones(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            Resolver(settings(note_repository_backend="nonsense")).get(SaveNoteUseCase)

        message = str(caught.value)
        assert "APP_NOTE_REPOSITORY_BACKEND is 'nonsense'" in message
        assert "NoteRepositoryPort is implemented by: jsonfile, memory" in message
        assert "system" not in message, "only backends implementing the port are worth listing"

    def test_backend_without_that_port_names_the_expected_file(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            Resolver(settings(note_repository_backend="system")).get(SaveNoteUseCase)

        message = str(caught.value)
        assert "*_note_repository_adapter.py" in message
        assert "src/app/infrastructure/system/" in message

    def test_ambiguous_port_names_the_setting_to_add(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            BareResolver(BareSettings()).get(SaveNoteUseCase)

        message = str(caught.value)
        assert "NoteRepositoryPort has 2 implementations" in message
        assert "`note_repository_backend: str`" in message
        assert "APP_NOTE_REPOSITORY_BACKEND" in message

    def test_a_port_nobody_implements_names_the_file_to_create(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            LocalResolver(settings()).get(NeedsWidgetUseCase)

        message = str(caught.value)
        assert "Nothing implements WidgetPort" in message
        assert "<library>_widget_adapter.py" in message

    def test_an_unsuppliable_parameter_names_its_env_var(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            LocalResolver(settings()).get(NeedsLimitUseCase)

        message = str(caught.value)
        assert "NeedsLimitUseCase(limit: int)" in message
        assert "APP_NEEDS_LIMIT_LIMIT" in message

    def test_a_cycle_is_named_rather_than_overflowing_the_stack(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            LocalResolver(settings()).get(PingUseCase)

        assert "Dependency cycle: PingUseCase -> PongUseCase -> PingUseCase" in str(caught.value)

    def test_a_failure_carries_the_resolution_trail(self) -> None:
        resolver = Resolver(settings(note_repository_backend="nonsense"))

        with pytest.raises(ConfigurationError) as caught:
            resolver.get(ListNotesUseCase)

        notes = getattr(caught.value, "__notes__", [])
        assert notes == ["while resolving: ListNotesUseCase -> NoteRepositoryPort"]

    def test_on_demand_resolution_defers_a_wiring_failure_to_first_use(self) -> None:
        """Building the edge does not touch its use cases, so a bad backend surfaces
        when a method runs rather than at startup."""
        runner = Runner(Resolver(settings(note_repository_backend="nonsense")))

        with pytest.raises(ConfigurationError):
            runner.run()

    def test_a_top_level_failure_carries_no_redundant_trail(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            LocalResolver(settings()).get(NeedsLimitUseCase)

        assert getattr(caught.value, "__notes__", []) == []


class TestOnDemandUseCases:
    """An edge resolving use cases where it uses them."""

    def test_the_lookup_is_typed(self) -> None:
        # The annotation is the assertion; `make typecheck` covers tests/.
        resolved: SaveNoteUseCase = Resolver(settings()).get(SaveNoteUseCase)
        assert isinstance(resolved, SaveNoteUseCase)

    def test_an_edge_shares_the_graph_with_everyone_else(self) -> None:
        resolver = Resolver(settings())
        assert Runner(resolver)._resolver.get(SaveNoteUseCase) is (resolver.get(SaveNoteUseCase))

    def test_an_edge_runs_against_fakes_when_a_provider_is_overridden(self) -> None:
        resolver = OverridingResolver(settings())
        Runner(resolver).run()

        repository = resolver.get(SaveNoteUseCase)._repository
        assert isinstance(repository, FakeNoteRepository)
        assert "welcome" in repository.notes


class TestExplain:
    def test_it_names_the_adapter_behind_each_port(self) -> None:
        lines = Resolver(settings(note_repository_backend="jsonfile")).explain().splitlines()

        assert any("ClockPort" in line and "system" in line for line in lines)
        assert any(
            "NoteRepositoryPort" in line and "orjson_note_repository_adapter" in line
            for line in lines
        )

    def test_a_misconfigured_port_reports_rather_than_raises(self) -> None:
        explained = Resolver(settings(note_repository_backend="nonsense")).explain()

        assert "NoteRepositoryPort" in explained
        assert "is implemented by: jsonfile, memory" in explained
