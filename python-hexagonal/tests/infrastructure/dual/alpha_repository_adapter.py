from pathlib import Path


class AlphaRepositoryAdapter:
    def __init__(self, path: Path) -> None:
        self.path = path
