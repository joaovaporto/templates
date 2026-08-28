from pathlib import Path


class BetaRepositoryAdapter:
    def __init__(self, path: Path) -> None:
        self.path = path
