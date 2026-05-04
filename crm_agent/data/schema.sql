-- crm_agent SQLite schema. Single source of truth.
-- Apply via db.connection.init_db() (idempotent: uses CREATE ... IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS stores (
  id INTEGER PRIMARY KEY,
  store_name TEXT NOT NULL,
  project_name TEXT,
  owner_name TEXT,
  primary_contact TEXT,
  phone_raw TEXT,
  phone_e164 TEXT,
  email TEXT,
  city TEXT,
  state TEXT,
  guidecx_project_id TEXT,
  status TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS store_aliases (
  id INTEGER PRIMARY KEY,
  store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  alias_norm TEXT NOT NULL,
  UNIQUE(store_id, alias_norm)
);

CREATE TABLE IF NOT EXISTS store_contacts (
  id INTEGER PRIMARY KEY,
  store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  name TEXT,
  name_norm TEXT,
  phone_raw TEXT,
  phone_e164 TEXT,
  email TEXT,
  role TEXT
);

CREATE INDEX IF NOT EXISTS idx_stores_phone_e164    ON stores(phone_e164);
CREATE INDEX IF NOT EXISTS idx_stores_name          ON stores(store_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_aliases_norm         ON store_aliases(alias_norm);
CREATE INDEX IF NOT EXISTS idx_contacts_phone_e164  ON store_contacts(phone_e164);
CREATE INDEX IF NOT EXISTS idx_contacts_name_norm   ON store_contacts(name_norm);

CREATE TRIGGER IF NOT EXISTS stores_updated_at AFTER UPDATE ON stores
BEGIN
  UPDATE stores SET updated_at = datetime('now') WHERE id = NEW.id;
END;
