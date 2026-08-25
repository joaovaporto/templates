class ApplicationError(Exception):
    """Base for every error the application layer raises."""


class RepositoryUnavailableError(ApplicationError):
    """The repository could not be reached or refused the request."""
