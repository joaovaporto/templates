from datetime import UTC, datetime

from app.application.ports.clock_port import ClockPort

FROZEN = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


class FakeClock(ClockPort):
    """A clock that does not move."""

    def __init__(self, instant: datetime = FROZEN) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant
