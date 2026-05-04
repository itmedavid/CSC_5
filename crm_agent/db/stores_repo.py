"""Read/write access to stores, aliases, and contacts.

Plain functions over sqlite3 — no ORM. Each function takes an open connection
so callers control transaction boundaries (mostly the seed importer).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from matcher.normalize import normalize_text, to_e164


@dataclass
class Store:
    id: int
    store_name: str
    project_name: Optional[str] = None
    owner_name: Optional[str] = None
    primary_contact: Optional[str] = None
    phone_raw: Optional[str] = None
    phone_e164: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    guidecx_project_id: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    aliases: list[str] = field(default_factory=list)
    contacts: list[dict] = field(default_factory=list)


def _row_to_store(row: sqlite3.Row) -> Store:
    return Store(
        id=row["id"],
        store_name=row["store_name"],
        project_name=row["project_name"],
        owner_name=row["owner_name"],
        primary_contact=row["primary_contact"],
        phone_raw=row["phone_raw"],
        phone_e164=row["phone_e164"],
        email=row["email"],
        city=row["city"],
        state=row["state"],
        guidecx_project_id=row["guidecx_project_id"],
        status=row["status"],
        notes=row["notes"],
    )


def insert_store(conn: sqlite3.Connection, **fields) -> int:
    fields.setdefault("phone_e164", to_e164(fields.get("phone_raw")))
    cols = [
        "store_name", "project_name", "owner_name", "primary_contact",
        "phone_raw", "phone_e164", "email", "city", "state",
        "guidecx_project_id", "status", "notes",
    ]
    values = [fields.get(c) for c in cols]
    placeholders = ", ".join("?" * len(cols))
    cur = conn.execute(
        f"INSERT INTO stores ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )
    return cur.lastrowid


def add_alias(conn: sqlite3.Connection, store_id: int, alias: str) -> None:
    norm = normalize_text(alias)
    if not norm:
        return
    conn.execute(
        "INSERT OR IGNORE INTO store_aliases (store_id, alias, alias_norm) VALUES (?, ?, ?)",
        (store_id, alias.strip(), norm),
    )


def add_contact(
    conn: sqlite3.Connection,
    store_id: int,
    *,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    role: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO store_contacts
            (store_id, name, name_norm, phone_raw, phone_e164, email, role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            store_id,
            name,
            normalize_text(name) if name else None,
            phone,
            to_e164(phone),
            email,
            role,
        ),
    )


def get_store(conn: sqlite3.Connection, store_id: int) -> Store | None:
    row = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
    if not row:
        return None
    store = _row_to_store(row)
    store.aliases = [
        r["alias"]
        for r in conn.execute(
            "SELECT alias FROM store_aliases WHERE store_id = ? ORDER BY alias", (store_id,)
        )
    ]
    store.contacts = [
        dict(r)
        for r in conn.execute(
            "SELECT name, phone_raw, phone_e164, email, role FROM store_contacts "
            "WHERE store_id = ? ORDER BY id",
            (store_id,),
        )
    ]
    return store


def find_by_phone_e164(conn: sqlite3.Connection, e164: str) -> list[int]:
    """Return store_ids whose stores.phone_e164 OR store_contacts.phone_e164 matches."""
    rows = conn.execute(
        """
        SELECT id AS store_id FROM stores WHERE phone_e164 = ?
        UNION
        SELECT store_id FROM store_contacts WHERE phone_e164 = ?
        """,
        (e164, e164),
    ).fetchall()
    return [r["store_id"] for r in rows]


def find_by_alias_norm(conn: sqlite3.Connection, alias_norm: str) -> list[int]:
    rows = conn.execute(
        "SELECT DISTINCT store_id FROM store_aliases WHERE alias_norm = ?",
        (alias_norm,),
    ).fetchall()
    return [r["store_id"] for r in rows]


def all_stores(conn: sqlite3.Connection) -> list[Store]:
    rows = conn.execute("SELECT * FROM stores ORDER BY store_name").fetchall()
    out = []
    for row in rows:
        store = _row_to_store(row)
        store.aliases = [
            r["alias"]
            for r in conn.execute(
                "SELECT alias FROM store_aliases WHERE store_id = ? ORDER BY alias",
                (store.id,),
            )
        ]
        out.append(store)
    return out


def all_aliases_norm(conn: sqlite3.Connection) -> dict[str, list[int]]:
    """Return alias_norm -> [store_id, ...] map. Used by the parser to detect
    store-name cues in raw text and by the matcher's alias-exact signal."""
    out: dict[str, list[int]] = {}
    for row in conn.execute("SELECT alias_norm, store_id FROM store_aliases"):
        out.setdefault(row["alias_norm"], []).append(row["store_id"])
    return out


def create_stub_store(
    conn: sqlite3.Connection,
    *,
    store_name: str,
    phone: str | None = None,
) -> int:
    """Minimal store creation for the unmatched-note flow.

    Adds the store_name as its own alias so subsequent matches find it.
    """
    sid = insert_store(
        conn,
        store_name=store_name.strip(),
        phone_raw=phone,
    )
    add_alias(conn, sid, store_name)
    return sid


def store_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM stores").fetchone()["n"]
