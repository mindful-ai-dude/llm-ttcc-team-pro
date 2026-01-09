"""Tests for runtime settings persistence (prompts + temperatures)."""

from __future__ import annotations

from pathlib import Path
import pytest


def test_defaults_returned_when_settings_file_missing(tmp_path, monkeypatch):
    from .. import runtime_settings as rs

    monkeypatch.setattr(rs, "SETTINGS_FILE", Path(tmp_path) / "runtime_settings.json")

    settings = rs.get_runtime_settings()

    assert isinstance(settings.council_temperature, float)
    assert settings.stage1_prompt_template, "Default stage1 prompt template should be non-empty"
    assert settings.stage2_prompt_template, "Default stage2 prompt template should be non-empty"
    assert settings.stage3_prompt_template, "Default stage3 prompt template should be non-empty"


def test_update_persists_and_reload(tmp_path, monkeypatch):
    from .. import runtime_settings as rs

    monkeypatch.setattr(rs, "SETTINGS_FILE", Path(tmp_path) / "runtime_settings.json")

    original = rs.get_runtime_settings()
    assert original.council_temperature != pytest.approx(0.77)

    updated = rs.update_runtime_settings(council_temperature=0.77)
    assert updated.council_temperature == pytest.approx(0.77)

    reloaded = rs.get_runtime_settings()
    assert reloaded.council_temperature == pytest.approx(0.77)


def test_reset_restores_defaults(tmp_path, monkeypatch):
    from .. import runtime_settings as rs

    monkeypatch.setattr(rs, "SETTINGS_FILE", Path(tmp_path) / "runtime_settings.json")

    rs.update_runtime_settings(stage2_temperature=0.11)
    assert rs.get_runtime_settings().stage2_temperature == pytest.approx(0.11)

    reset = rs.reset_runtime_settings()
    assert reset.stage2_temperature != pytest.approx(0.11)
