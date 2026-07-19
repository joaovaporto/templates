import logging
import sys

from pydantic import ValidationError

from app.application.errors import ConfigurationError
from app.composition.container import AppContainer
from app.presentation import logging as log
from app.presentation.settings import Settings

logger = logging.getLogger(__name__)


def main() -> None:
    """Entrypoint for the `app` console script.

    Build the container from settings, hand the finished runner its collaborators, run.
    That is the whole of it — the wiring lives in the container, and the runner has never
    heard of an adapter.
    """
    try:
        settings = Settings()
    except ValidationError as e:
        print(f"Invalid configuration:\n{e}", file=sys.stderr)
        raise SystemExit(2) from e

    log.configure(debug=settings.debug)

    try:
        AppContainer(settings).runner().run()
    except ConfigurationError as e:
        logger.error("%s", e)
        raise SystemExit(2) from e
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
