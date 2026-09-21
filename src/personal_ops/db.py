from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2

MOVE_COLUMNS = {
    "question": "TEXT",
    "output_contract": "TEXT",
    "done_when": "TEXT",
    "output_result": "TEXT",
    "baseline_json": "TEXT",
    "variant_json": "TEXT",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS objectives (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  year INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  constraints_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS initiatives (
  id TEXT PRIMARY KEY,
  objective_id TEXT NOT NULL REFERENCES objectives(id),
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  advancing INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  closed_at TEXT,
  close_reason TEXT
);

CREATE TABLE IF NOT EXISTS moves (
  id TEXT PRIMARY KEY,
  initiative_id TEXT NOT NULL REFERENCES initiatives(id),
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  hypothesis TEXT,
  question TEXT,
  output_contract TEXT,
  done_when TEXT,
  output_result TEXT,
  baseline_json TEXT,
  variant_json TEXT,
  causal_confidence TEXT,
  decision TEXT,
  created_at TEXT NOT NULL,
  prepared_at TEXT,
  deployed_at TEXT,
  observing_until TEXT,
  closed_at TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  move_id TEXT NOT NULL REFERENCES moves(id),
  source TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  evidence_type TEXT NOT NULL,
  external_reference TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  artifact_reference TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learnings (
  id TEXT PRIMARY KEY,
  initiative_id TEXT NOT NULL REFERENCES initiatives(id),
  move_id TEXT,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    _ensure_move_columns(conn)
    current = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()["v"]
    if current is None:
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    elif current < SCHEMA_VERSION:
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    return conn


def _ensure_move_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(moves)")}
    for name, decl in MOVE_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE moves ADD COLUMN {name} {decl}")
    conn.commit()
