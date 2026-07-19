from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SaveOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    FAILED = "failed"


class SaveNoteOutput(BaseModel):
    """The result of a save, travelling away from the core.

    The use case never raises to report a routine outcome; it returns one of these.
    Named constructors keep call sites honest about which case they mean.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    outcome: SaveOutcome
    detail: str = ""

    @classmethod
    def created(cls, key: str) -> "SaveNoteOutput":
        return cls(key=key, outcome=SaveOutcome.CREATED)

    @classmethod
    def updated(cls, key: str) -> "SaveNoteOutput":
        return cls(key=key, outcome=SaveOutcome.UPDATED)

    @classmethod
    def failed(cls, key: str, detail: str) -> "SaveNoteOutput":
        return cls(key=key, outcome=SaveOutcome.FAILED, detail=detail)
