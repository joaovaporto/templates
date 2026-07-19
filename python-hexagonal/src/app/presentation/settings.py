from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_MEMORY = "memory"
BACKEND_JSONFILE = "jsonfile"
BACKENDS = (BACKEND_MEMORY, BACKEND_JSONFILE)


class Settings(BaseSettings):
    """The edge's configuration, read from the environment / .env.

    Presentation owns settings; the composition root reads them to choose adapters. Note
    what selects the backend: a *name* (`APP_REPOSITORY_BACKEND`), not an import. An
    unknown name is rejected by the container at startup, not defaulted silently.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    repository_backend: str = Field(default=BACKEND_MEMORY)
    jsonfile_path: str = Field(default="notes.json")
    debug: bool = Field(default=False)
