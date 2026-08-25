from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    """What the core needs from the passage of time."""

    def now(self) -> datetime:
        """The current instant, timezone-aware."""
        ...
