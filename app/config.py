from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


CONFIG_PATH = Path("data/config.json")
MONITORS_PATH = Path("data/monitors.json")


@dataclass
class AppConfig:
    base_url: str = ""
    api_key: str = ""

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "AppConfig":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            return cls(**data)
        except Exception:
            return cls()

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))


@dataclass
class MonitorConfig:
    uuid: str
    interval_seconds: int = 60
    last_status: Optional[str] = None
    last_checked: Optional[str] = None


class MonitorStore:
    def __init__(self, path: Path = MONITORS_PATH):
        self.path = path

    def load(self) -> list[MonitorConfig]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
            return [MonitorConfig(**entry) for entry in raw]
        except Exception:
            return []

    def save(self, monitors: list[MonitorConfig]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(m) for m in monitors]
        self.path.write_text(json.dumps(data, indent=2))
