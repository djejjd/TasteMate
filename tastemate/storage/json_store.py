from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tastemate.schemas.profile import default_profile, normalize_profile


class CorruptProfileError(ValueError):
    """Raised when the profile file exists but is not valid JSON."""


class JsonProfileStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            profile = default_profile()
            self.save(profile)
            return profile

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CorruptProfileError(f"Profile file is corrupt: {self.path}") from exc

        if not isinstance(raw, dict):
            return default_profile()
        return normalize_profile(raw)

    def save(self, profile: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        normalized = normalize_profile(profile)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
