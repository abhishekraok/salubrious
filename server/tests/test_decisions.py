import json

import pytest

from app.routers.decisions import load_action_quality


def test_missing_private_artifact_returns_friendly_unavailable_payload(tmp_path):
    result = load_action_quality(tmp_path / "missing.json")

    assert result["available"] is False
    assert ".private" not in result["message"]
    assert str(tmp_path) not in result["message"]


def test_valid_private_artifact_is_returned(tmp_path):
    path = tmp_path / "action_quality.json"
    payload = {"schema_version": 1, "available": True, "actions": []}
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_action_quality(path) == payload


@pytest.mark.parametrize("content", ["not json", '{"schema_version": 2}'])
def test_malformed_or_unknown_private_artifact_is_generic(tmp_path, content):
    path = tmp_path / "action_quality.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(RuntimeError, match="data is unavailable"):
        load_action_quality(path)
