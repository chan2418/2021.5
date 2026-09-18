""""""

import sys
from pathlib import Path


class PathManager:
    """"""

    ENV_KEY = "BFSTOOLS_PATHS"

    def __init__(self, env_path=None):
        self.env_path = env_path or Path(__file__).parents[3] / ".env"
        self._env_vars = {}

    def load_env(self):
        if not self.env_path.exists():
            raise FileNotFoundError(f"[BFSTools] .env not found: {self.env_path}")

        with open(self.env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                self._env_vars[key.strip()] = value.strip()

        return self._env_vars

    def register_paths(self):
        self.load_env()
        raw = self._env_vars.get(self.ENV_KEY, "")

        if not raw:
            raise ValueError(f"[BFSTools] '{self.ENV_KEY}' missing in .env")

        added = []
        for path in raw.split(","):
            path = path.strip()
            if path and path not in sys.path:
                sys.path.insert(0, path)
                added.append(path)

        print(f"[BFSTools] {len(added)} paths registered from .env")
        return added
