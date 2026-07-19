class ApplicationError(Exception):
    """Base for every error the application layer raises."""


class ConfigurationError(ApplicationError):
    """The wiring or settings are wrong. Raised at startup, never at first use."""


class MissingDependencyError(ConfigurationError):
    """An adapter was selected whose optional extra is not installed."""

    def __init__(self, adapter: str, package: str, extra: str) -> None:
        super().__init__(
            f"{adapter} needs the '{package}' package, which is not installed. "
            f"It ships in the '{extra}' extra: uv sync --extra {extra}"
        )
        self.adapter = adapter
        self.package = package
        self.extra = extra


class RepositoryUnavailableError(ApplicationError):
    """The repository could not be reached or refused the request."""
