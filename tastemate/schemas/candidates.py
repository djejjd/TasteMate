from __future__ import annotations

import hashlib
from typing import Any

REQUIRED_FIELDS = ("id", "title", "summary", "metadata")


def _stable_id(parts: list[str]) -> str:
    source = "|".join(part.strip() for part in parts if part and part.strip())
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"candidate-{digest}"


def validate_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    missing_fields = [field for field in ("id", "title", "summary") if not raw.get(field)]
    if "metadata" not in raw or raw.get("metadata") is None or not isinstance(raw.get("metadata"), dict):
        missing_fields.append("metadata")
    return {
        "valid": not missing_fields,
        "candidate_id": raw.get("id"),
        "missing_fields": missing_fields,
        "candidate": {
            "id": raw.get("id"),
            "title": raw.get("title"),
            "summary": raw.get("summary"),
            "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
            "url": raw.get("url"),
            "source": raw.get("source"),
        },
    }


def validate_candidates(raw_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for raw in raw_candidates:
        result = validate_candidate(raw)
        if result["valid"]:
            valid.append(result["candidate"])
        else:
            invalid.append(
                {
                    "candidate_index": len(invalid) + len(valid),
                    "candidate_id": result["candidate_id"],
                    "missing_fields": result["missing_fields"],
                }
            )
    return {"valid_candidates": valid, "invalid_candidates": invalid}


def normalize_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    title = str(raw.get("title") or "Untitled candidate")
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
