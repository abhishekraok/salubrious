"""Read-only access to the locally generated decision-quality analysis."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api/decisions", tags=["decisions"])

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTION_QUALITY_PATH = REPO_ROOT / ".private" / "finance" / "action_quality.json"


def load_action_quality(path: Path = ACTION_QUALITY_PATH) -> dict[str, Any]:
    """Load a generated private artifact without leaking its filesystem path."""

    if not path.exists():
        return {
            "schema_version": 1,
            "available": False,
            "message": "Run the private finance-history importer to generate this analysis.",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, JSONDecodeError) as exc:
        raise RuntimeError("Decision-quality data is unavailable") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("Decision-quality data is unavailable")
    return payload


@router.get("/quality")
def decision_quality() -> dict[str, Any]:
    try:
        return load_action_quality()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="Decision-quality data is unavailable") from exc
