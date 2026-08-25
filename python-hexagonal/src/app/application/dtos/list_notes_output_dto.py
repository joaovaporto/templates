from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ListNotesOutputDto(BaseModel):
    """Every stored key and when the answer was taken, travelling away from the core."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    keys: tuple[str, ...]
    listed_at: datetime
