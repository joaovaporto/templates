class DomainError(Exception):
    """Base for every error the domain raises."""


class DomainValidationError(DomainError):
    """An invariant was violated, so the object was never created."""
