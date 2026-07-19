from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.entities.note import Note
from app.domain.value_objects.title import Title


class SaveNoteInput(BaseModel):
    """One note, travelling toward the core.

    This DTO is the use case's precondition made into a type: it validates on
    construction and is frozen, so a successfully built instance is durable proof that
    the use case may run. The use case reads every field without re-checking presence or
    emptiness, because it cannot have been handed anything else.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    title: str
    body: str
    tags: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("key", "body")
    @classmethod
    def _must_be_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v

    def to_note(self) -> Note:
        """Build the entity. Total: the invariants already hold, so this cannot fail."""
        return Note(
            key=self.key,
            title=Title.build(self.title),
            body=self.body,
            tags=self.tags,
        )
