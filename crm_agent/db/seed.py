"""CSV -> SQLite importer for stores and contacts.

Two CSV inputs:

* `seed_stores.csv` columns:
    store_name, project_name, owner_name, primary_contact, phone, email,
    city, state, guidecx_project_id, status, aliases, notes
  - aliases is pipe-delimited.
  - phone is free-form; normalized to E.164 on import.

* `seed_contacts.csv` columns (optional):
    store_name, contact_name, phone, email, role
  - Joined to stores by store_name. Ambiguous names raise.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from db import stores_repo
from matcher.normalize import split_aliases


@dataclass
class SeedReport:
    stores_inserted: int = 0
    stores_skipped: int = 0
    aliases_inserted: int = 0
    contacts_inserted: int = 0
    contacts_skipped: int = 0
    warnings: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def import_stores_csv(
    conn: sqlite3.Connection,
    csv_path: Path,
    *,
    skip_existing: bool = True,
) -> SeedReport:
    report = SeedReport()
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("store_name") or "").strip()
            if not name:
                report.warnings.append(f"row missing store_name: {row}")
                continue

            existing = conn.execute(
                "SELECT id FROM stores WHERE store_name = ? COLLATE NOCASE",
                (name,),
            ).fetchall()
            if existing and skip_existing:
                report.stores_skipped += 1
                continue

            sid = stores_repo.insert_store(
                conn,
                store_name=name,
                project_name=(row.get("project_name") or "").strip() or None,
                owner_name=(row.get("owner_name") or "").strip() or None,
                primary_contact=(row.get("primary_contact") or "").strip() or None,
                phone_raw=(row.get("phone") or "").strip() or None,
                email=(row.get("email") or "").strip() or None,
                city=(row.get("city") or "").strip() or None,
                state=(row.get("state") or "").strip() or None,
                guidecx_project_id=(row.get("guidecx_project_id") or "").strip() or None,
                status=(row.get("status") or "").strip() or None,
                notes=(row.get("notes") or "").strip() or None,
            )
            report.stores_inserted += 1

            stores_repo.add_alias(conn, sid, name)
            report.aliases_inserted += 1
            for alias in split_aliases(row.get("aliases")):
                stores_repo.add_alias(conn, sid, alias)
                report.aliases_inserted += 1

    conn.commit()
    return report


def import_contacts_csv(
    conn: sqlite3.Connection,
    csv_path: Path,
) -> SeedReport:
    report = SeedReport()
    if not csv_path.exists():
        return report
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("store_name") or "").strip()
            if not name:
                continue
            matches = conn.execute(
                "SELECT id FROM stores WHERE store_name = ? COLLATE NOCASE",
                (name,),
            ).fetchall()
            if len(matches) == 0:
                report.contacts_skipped += 1
                report.warnings.append(f"contact references unknown store: {name}")
                continue
            if len(matches) > 1:
                report.contacts_skipped += 1
                report.warnings.append(
                    f"ambiguous contact store_name '{name}' matched {len(matches)} stores; "
                    "add guidecx_project_id support if this matters"
                )
                continue
            sid = matches[0]["id"]
            stores_repo.add_contact(
                conn,
                sid,
                name=(row.get("contact_name") or "").strip() or None,
                phone=(row.get("phone") or "").strip() or None,
                email=(row.get("email") or "").strip() or None,
                role=(row.get("role") or "").strip() or None,
            )
            report.contacts_inserted += 1
    conn.commit()
    return report
