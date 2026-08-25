from datetime import UTC, datetime

from app.application.ports.clock_port import ClockPort


class SystemClockAdapter(ClockPort):
    """The wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)
