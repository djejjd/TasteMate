import json

import pytest

from tastemate.schemas.profile import normalize_profile
from tastemate.storage.json_store import CorruptProfileError, JsonProfileStore


def test_profile_store_initializes_default_profile(tmp_path):
    path = tmp_path / "profile.json"
    store = JsonProfileStore(path)

    profile = store.load()

    assert profile == {
        "stable_preferences": {},
        "negative_preferences": {},
        "current_focus": {},
        "evidence_log": [],
    }
    assert json.loads(path.read_text()) == profile


def test_profile_store_does_not_overwrite_corrupt_file(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{not-json", encoding="utf-8")
    store = JsonProfileStore(path)

    with pytest.raises(CorruptProfileError):
        store.load()

    assert path.read_text(encoding="utf-8") == "{not-json"


def test_normalize_profile_backfills_iteration003_sections():
    profile = normalize_profile(
        {
            "stable_preferences": {
                "local_first": {"weight": 0.4}
            },
            "evidence_log": [{"feature": "local_first"}],
        }
    )

    assert profile["stable_preferences"]["local_first"]["feature"] == "local_first"
    assert profile["stable_preferences"]["local_first"]["evidence_count"] == 0
    assert profile["negative_preferences"] == {}
    assert profile["current_focus"] == {}
