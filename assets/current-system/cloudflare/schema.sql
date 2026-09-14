CREATE TABLE IF NOT EXISTS expenses (
  id TEXT PRIMARY KEY,
  amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
  currency TEXT NOT NULL,
  date TEXT NOT NULL,
  category TEXT NOT NULL,
  payer TEXT NOT NULL,
  method TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1,
  deleted INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS expenses_active ON expenses(deleted, date);
CREATE TABLE IF NOT EXISTS checks (
  id TEXT PRIMARY KEY,
  checked INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS members(id TEXT PRIMARY KEY,name TEXT NOT NULL,avatar TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1);
ALTER TABLE expenses ADD COLUMN split_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE expenses ADD COLUMN kind TEXT NOT NULL DEFAULT 'expense';

CREATE TABLE IF NOT EXISTS tickets (
  id TEXT PRIMARY KEY,
  place_key TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  file_name TEXT,
  object_key TEXT,
  content_type TEXT,
  size INTEGER,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS tickets_place_created ON tickets(place_key, created_at DESC);
