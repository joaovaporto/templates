import logging
import sys

from pydantic import ValidationError

from app.infrastructure.errors import MissingDependencyError
from app.presentation import logging as log
from app.presentation.composition.errors import ConfigurationError
from app.presentation.composition.resolver import Resolver
from app.presentation.runner import Runner
from app.presentation.settings import Settings

logger = logging.getLogger(__name__)


def main() -> None:
    """Entrypoint for the `app` console script."""
    try:
        settings = Settings()
    except ValidationError as e:
        print(f"Invalid configuration:\n{e}", file=sys.stderr)
        raise SystemExit(2) from e

    log.configure(debug=settings.debug)

    try:
        Runner(Resolver(settings)).run()
    except (ConfigurationError, MissingDependencyError) as e:
        logger.error("%s", "\n".join([str(e), *getattr(e, "__notes__", [])]))
        raise SystemExit(2) from e
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        raise SystemExit(1) from e


def explain() -> None:
    """Entrypoint for `app-explain`: print the wiring the current settings produce."""
    print(Resolver(Settings()).explain())


if __name__ == "__main__":
    main()
