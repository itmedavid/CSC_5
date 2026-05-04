"""Smoke tests for the store repository and CSV seeder."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import settings
from db import seed, stores_repo
from db.connection import get_conn, init_db


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    c = get_conn(db_path)
    yield c
    c.close()


def test_init_db_creates_tables(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    assert {r["name"] for r in rows} >= {"stores", "store_aliases", "store_contacts"}


def test_seed_imports_stores_and_aliases(conn: sqlite3.Connection) -> None:
    report = seed.import_stores_csv(conn, settings.SEED_STORES_CSV)
    assert report.stores_inserted == 5
    # 5 stores * (1 self-alias + 2 or 3 listed aliases) -> at least 5 + 12 = 17
    assert report.aliases_inserted >= 17
    assert stores_repo.store_count(conn) == 5


def test_find_by_phone_e164(conn: sqlite3.Connection) -> None:
    seed.import_stores_csv(conn, settings.SEED_STORES_CSV)
    # Joe's Market phone (415) 555-1212 -> +14155551212
    matches = stores_repo.find_by_phone_e164(conn, "+14155551212")
    assert len(matches) == 1
    store = stores_repo.get_store(conn, matches[0])
    assert store is not None
    assert store.store_name == "Joe's Market"


def test_find_by_alias_norm(conn: sqlite3.Connection) -> None:
    seed.import_stores_csv(conn, settings.SEED_STORES_CSV)
    from matcher.normalize import normalize_text

    matches = stores_repo.find_by_alias_norm(conn, normalize_text("JM Downtown"))
    assert len(matches) == 1
    matches = stores_repo.find_by_alias_norm(conn, normalize_text("Pioneer Coffee"))
    assert len(matches) == 1


def test_contacts_import_joins_by_name(conn: sqlite3.Connection) -> None:
    seed.import_stores_csv(conn, settings.SEED_STORES_CSV)
    report = seed.import_contacts_csv(conn, settings.SEED_CONTACTS_CSV)
    assert report.contacts_inserted == 3
    assert report.contacts_skipped == 0
    westside = next(
        s for s in stores_repo.all_stores(conn) if s.store_name == "Westside Hardware"
    )
    detail = stores_repo.get_store(conn, westside.id)
    assert detail is not None
    assert len(detail.contacts) == 2


def test_create_stub_store(conn: sqlite3.Connection) -> None:
    sid = stores_repo.create_stub_store(
        conn, store_name="New Place", phone="(555) 010-2030"
    )
    store = stores_repo.get_store(conn, sid)
    assert store is not None
    assert store.store_name == "New Place"
    assert "New Place" in store.aliases
