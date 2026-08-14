"""Pure-function coverage for `app/tasks/application_tasks.py`'s name
splitting — the rest of `_apply_to_job` is a DB-bound orchestration
function exercised by the integration suite, not unit tests."""

from __future__ import annotations

from types import SimpleNamespace

from app.tasks.application_tasks import _first_name_of, _last_name_of


def test_splits_full_name() -> None:
    profile = SimpleNamespace(full_name="Ada Lovelace")
    assert _first_name_of(profile) == "Ada"
    assert _last_name_of(profile) == "Lovelace"


def test_handles_multi_word_last_name() -> None:
    profile = SimpleNamespace(full_name="Mary Ann Evans")
    assert _first_name_of(profile) == "Mary"
    assert _last_name_of(profile) == "Ann Evans"


def test_single_name_has_no_last_name() -> None:
    profile = SimpleNamespace(full_name="Madonna")
    assert _first_name_of(profile) == "Madonna"
    assert _last_name_of(profile) is None


def test_handles_missing_profile() -> None:
    assert _first_name_of(None) is None
    assert _last_name_of(None) is None
