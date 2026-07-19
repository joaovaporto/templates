from dataclasses import dataclass

from app.domain.errors import DomainValidationError

MAX_LENGTH = 255

FALLBACK = "Untitled"


@dataclass(frozen=True, slots=True)
class Title:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise DomainValidationError("A title cannot be empty.")
        if len(self.value) > MAX_LENGTH:
            raise DomainValidationError(
                f"A title cannot exceed {MAX_LENGTH} characters (got {len(self.value)}). "
                f"Build it with Title.build(), which truncates."
            )

    @classmethod
    def build(cls, raw: str) -> "Title":
        """Coerce arbitrary text into a valid title, truncating and falling back."""
        cleaned = (raw or "").strip()
        if not cleaned:
            return cls(FALLBACK)
        return cls(cleaned[:MAX_LENGTH])

    def __str__(self) -> str:
        return self.value
