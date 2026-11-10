"""SQLite access layer: schema introspection, SQL safety validation, read-only execution."""
import re
import sqlite3
from pathlib import Path
from typing import Any

import config

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex|truncate)\b", re.I
)


class SQLValidationError(ValueError):
    pass


class Database:
    def __init__(self, path: Path | str | None = None, max_rows: int | None = None):
        self.path = Path(path or config.DB_PATH)
        self.max_rows = max_rows or config.MAX_ROWS
        if not self.path.exists():
            raise FileNotFoundError(f"Database not found: {self.path}. Run `python create_sample_db.py` first.")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)  # read-only connection
        conn.row_factory = sqlite3.Row
        return conn

    # ---- schema -------------------------------------------------------
    def table_names(self) -> list[str]:
        with self._connect() as c:
            return [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

    def schema_text(self, sample_rows: int = 2) -> str:
        parts = []
        with self._connect() as c:
            for t in self.table_names():
                cols = c.execute(f"PRAGMA table_info({t})").fetchall()
                fks = c.execute(f"PRAGMA foreign_key_list({t})").fetchall()
                line = f"TABLE {t}(" + ", ".join(f"{col['name']} {col['type']}" for col in cols) + ")"
                for fk in fks:
                    line += f"\n  FK: {t}.{fk['from']} -> {fk['table']}.{fk['to']}"
                samples = c.execute(f"SELECT * FROM {t} LIMIT {sample_rows}").fetchall()
                for s in samples:
                    line += "\n  e.g. " + str(dict(s))
                parts.append(line)
        return "\n".join(parts)

    def table_columns(self) -> dict[str, list[str]]:
        with self._connect() as c:
            return {t: [r["name"] for r in c.execute(f"PRAGMA table_info({t})")] for t in self.table_names()}

    # ---- validation + execution ---------------------------------------
    def validate_sql(self, sql: str) -> str:
        """Static safety checks, then let SQLite itself validate tables/columns via EXPLAIN."""
        s = sql.strip().rstrip(";").strip()
        if not re.match(r"^(select|with)\b", s, re.I):
            raise SQLValidationError("Only SELECT / WITH queries are allowed.")
        if ";" in s:
            raise SQLValidationError("Multiple statements are not allowed.")
        if "--" in s or "/*" in s:
            raise SQLValidationError("SQL comments are not allowed.")
        if FORBIDDEN.search(s):
            raise SQLValidationError("Query contains a forbidden keyword (write/DDL operations are blocked).")
        try:
            with self._connect() as c:
                c.execute(f"EXPLAIN QUERY PLAN {s}")
        except sqlite3.Error as e:
            raise SQLValidationError(f"Schema validation failed: {e}")
        return s

    def execute(self, sql: str) -> tuple[list[str], list[dict[str, Any]], int]:
        s = self.validate_sql(sql)
        try:
            with self._connect() as c:
                cur = c.execute(s)
                cols = [d[0] for d in cur.description]
                fetched = cur.fetchmany(self.max_rows + 1)
        except sqlite3.Error as e:
            raise SQLValidationError(f"Execution failed: {e}")
        truncated = len(fetched) > self.max_rows
        rows = [dict(r) for r in fetched[: self.max_rows]]
        return cols, rows, len(rows) + (1 if truncated else 0)
