from __future__ import annotations

import hashlib
from typing import Any


def _stable_id(parts: list[str]) -> str:
    source = "|".join(part.strip() for part in parts if part and part.strip())
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"candidate-{digest}"


def normalize_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    title = str(raw.get("title") or raw.get("url") or raw.get("source") or "Untitled candidate")
    summary = str(raw.get("summary") or "")
    url = raw.get("url")
    source = raw.get("source")
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    candidate_id = raw.get("id") or _stable_id([title, str(url or ""), summary])

    return {
        "id": str(candidate_id),
        "title": title,
        "summary": summary,
        "url": url,
        "source": source,
        "metadata": metadata,
    }


def normalize_candidates(raw_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_candidate(item) for item in raw_candidates]
