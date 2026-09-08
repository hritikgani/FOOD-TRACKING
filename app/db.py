from pathlib import Path

import click
import psycopg2
import psycopg2.extras
from flask import current_app, g


class PGConnection:
    """Wraps a psycopg2 connection with the sqlite3.Connection-shaped
    convenience API (db.execute(...) returning a cursor directly, no
    separate db.cursor() step) that the rest of the app is written against,
    so the service layer needed no rewrite beyond the SQL dialect itself.
    Rows come back as dict-like RealDictRow objects, matching the old
    sqlite3.Row behaviour (supports both row['col'] and dict(row)).
    """

    def __init__(self, dsn):
        self._conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        # The service layer is written with SQLite's "?" placeholders;
        # psycopg2 needs "%s". None of this app's queries put a literal "?"
        # in the SQL text itself (only ever in bound parameter values), so
        # a plain replace is safe.
        pg_sql = sql.replace("?", "%s")
        if params:
            cur.execute(pg_sql, tuple(params))
        else:
            cur.execute(pg_sql)
        return cur

    def executescript(self, sql):
        cur = self._conn.cursor()
        cur.execute(sql)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


_local_pg_server = None


def _local_pg_dsn(app):
    """Lazily starts (or reuses) an embedded local Postgres via `pgserver`
    for development, so there's nothing to install/configure locally. Only
    imported here -- never needed, and never installed, in production where
    DATABASE_URL is always set.
    """
    global _local_pg_server
    if _local_pg_server is None:
        try:
            import pgserver
        except ImportError as e:
            raise RuntimeError(
                "DATABASE_URL is not set and the local dev Postgres package "
                "isn't installed. Run: pip install -r requirements-dev.txt"
            ) from e
        pgdata = Path(app.config["LOCAL_PGDATA_DIR"])
        pgdata.parent.mkdir(parents=True, exist_ok=True)
        _local_pg_server = pgserver.get_server(pgdata)
    return _local_pg_server.get_uri("postgres")


def _resolve_dsn():
    dsn = current_app.config["DATABASE_URL"]
    if not dsn:
        dsn = _local_pg_dsn(current_app)
    return dsn


def get_db():
    if "db" not in g:
        g.db = PGConnection(_resolve_dsn())
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        db.executescript(f.read())
    db.commit()


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    with app.app_context():
        init_db()
