#!/usr/bin/env python3
import re
import sqlite3
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except Exception:  # pragma: no cover
    psycopg2 = None


def get_db_backend_name(settings):
    backend = str(settings.get("db_backend", "sqlite")).strip().lower()
    return "postgres" if backend in {"postgres", "postgresql", "psql"} else "sqlite"


def create_db_connection(settings, dict_rows=True):
    backend = get_db_backend_name(settings)
    if backend == "postgres":
        if psycopg2 is None:
            raise RuntimeError("psycopg2 ist nicht installiert, aber db_backend=postgres gesetzt.")
        kwargs = {
            "host": settings["db_host"],
            "dbname": settings["db_name"],
            "user": settings["db_user"],
            "password": settings["db_pass"],
        }
        if dict_rows:
            kwargs["cursor_factory"] = psycopg2.extras.RealDictCursor
        return psycopg2.connect(**kwargs)

    sqlite_path = Path(str(settings.get("sqlite_path") or "./data/simple-storage-core.db")).expanduser()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(sqlite_path))
    connection.row_factory = sqlite3.Row if dict_rows else None
    return SQLiteConnectionWrapper(connection)


class SQLiteConnectionWrapper:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return SQLiteCursorWrapper(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()


class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        normalized = _normalize_sql_for_sqlite(query)
        if params is None:
            self._cursor.execute(normalized)
        else:
            self._cursor.execute(normalized, params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if rows and isinstance(rows[0], sqlite3.Row):
            return [dict(row) for row in rows]
        return rows

    def close(self):
        self._cursor.close()


def _normalize_sql_for_sqlite(query):
    sql = str(query)
    sql = sql.replace("%s", "?")
    sql = re.sub(r"\bGREATEST\s*\(", "MAX(", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bILIKE\b", "LIKE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+NULLS\s+LAST", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+NULLS\s+FIRST", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bTRUE\b", "1", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bFALSE\b", "0", sql, flags=re.IGNORECASE)
    return sql
