from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """The edge's configuration, read from the environment / .env.

    Two conventions connect a name here to a class under `infrastructure/`:

        <port>_backend    names the subpackage implementing that port, and is needed only
                          once a port has more than one implementation.
        <backend>_<arg>   supplies one constructor argument of that backend's adapters.

    When one backend implements two ports whose adapters take an argument of the same
    name, scope that argument to its port as `<port>_<backend>_<arg>`, which is read in
    preference to the plain form. Declaring it is what selects it, so the plain field
    stops feeding that adapter even if the scoped one is left at its default.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    note_repository_backend: str = "memory"
    jsonfile_path: Path = Path("notes.json")
    debug: bool = False
