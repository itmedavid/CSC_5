"""Tests for the GuideCX paste integration.

Live (Playwright) mode is not testable without a real browser + GuideCX
login; we only verify it raises NotImplementedError as documented. The
dry-run client is fully covered, including the action-log row shape.
"""

from __future__ import annotations

import importlib

import pytest

import settings
from integrations.guidecx_browser import (
    DryRunClient,
    GuideCXClient,
    PasteRequest,
    PasteResult,
    PlaywrightClient,
    build_project_url,
    get_client,
)


def _request(**overrides) -> PasteRequest:
    base = dict(
        store_id=42,
        store_name="Joe's Market",
        guidecx_project_id="J-1042",
        note_text=(
            "5/2 #DB |\n"
            "Spoke with Anita about the hardware delivery slip.\n"
            "Outstanding: Send updated install schedule by Friday.\n"
            "Risk/Blocker: None.\n"
            "Next step: Send the updated install schedule."
        ),
        raw_note_id="abcd-1234",
        session_id="sess-test",
    )
    base.update(overrides)
    return PasteRequest(**base)


def test_build_project_url_uses_template() -> None:
    url = build_project_url("J-1042")
    assert url == "https://app.guidecx.com/projects/J-1042"


def test_build_project_url_returns_none_for_missing_id() -> None:
    assert build_project_url(None) is None
    assert build_project_url("") is None


def test_dry_run_happy_path() -> None:
    result = DryRunClient().paste(_request())
    assert result.ok is True
    assert result.mode == "dry_run"
    assert result.project_url == "https://app.guidecx.com/projects/J-1042"
    assert "Dry-run" in result.message
    assert result.ts  # populated


def test_dry_run_no_project_id_fails_safely() -> None:
    result = DryRunClient().paste(_request(guidecx_project_id=None))
    assert result.ok is False
    assert result.project_url is None
    assert "No GuideCX project URL" in result.message


def test_dry_run_empty_note_text_fails_safely() -> None:
    result = DryRunClient().paste(_request(note_text="   \n  "))
    assert result.ok is False
    assert "empty" in result.message.lower()


def test_log_row_shape_for_dry_run_success() -> None:
    result = DryRunClient().paste(_request())
    row = result.as_log_row()
    assert row["decision"] == "dry_run_pasted"
    assert row["ok"] is True
    assert row["mode"] == "dry_run"
    assert row["store_id"] == 42
    assert row["store_name_snapshot"] == "Joe's Market"
    assert row["guidecx_project_id"] == "J-1042"
    assert row["project_url"] == "https://app.guidecx.com/projects/J-1042"
    assert "Outstanding:" in row["formatted_text"]


def test_log_row_shape_for_dry_run_failure() -> None:
    result = DryRunClient().paste(_request(guidecx_project_id=None))
    row = result.as_log_row()
    assert row["decision"] == "dry_run_pasted"  # never tagged "pasted" if !ok
    assert row["ok"] is False
    assert row["project_url"] is None


def test_factory_default_is_dry_run() -> None:
    assert isinstance(get_client(), DryRunClient)
    assert isinstance(get_client("dry_run"), DryRunClient)


def test_factory_returns_live_skeleton() -> None:
    assert isinstance(get_client("live"), PlaywrightClient)


def test_factory_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        get_client("bogus")


def test_live_client_skeleton_raises_until_implemented() -> None:
    with pytest.raises(NotImplementedError):
        PlaywrightClient().paste(_request())


def test_live_log_row_uses_pasted_decision_when_ok_true() -> None:
    """Synthesize a successful live result and confirm the log row tags it
    `pasted` (not `dry_run_pasted`). Verifies the discriminator the user will
    grep their action_log for."""
    req = _request()
    result = PasteResult(
        ok=True,
        mode="live",
        project_url="https://app.guidecx.com/projects/J-1042",
        message="filled textarea",
        ts="2026-05-02T20:00:00Z",
        request=req,
    )
    row = result.as_log_row()
    assert row["decision"] == "pasted"
    assert row["mode"] == "live"


def test_subclassing_contract() -> None:
    assert issubclass(DryRunClient, GuideCXClient)
    assert issubclass(PlaywrightClient, GuideCXClient)


def test_project_url_template_is_configurable(monkeypatch) -> None:
    """If the user customizes GUIDECX_PROJECT_URL_TEMPLATE, build_project_url
    must reflect it. settings is module-level so we patch in place."""
    monkeypatch.setattr(
        settings,
        "GUIDECX_PROJECT_URL_TEMPLATE",
        "https://my-tenant.guidecx.com/p/{project_id}/notes",
    )
    # Re-import to pick up patch? No — build_project_url reads settings at call
    # time, so the patch is effective immediately.
    importlib.reload(importlib.import_module("integrations.guidecx_browser"))
    from integrations.guidecx_browser import build_project_url as build
    assert build("J-1042") == "https://my-tenant.guidecx.com/p/J-1042/notes"
