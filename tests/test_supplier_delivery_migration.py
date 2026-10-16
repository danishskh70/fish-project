"""PostgreSQL migration checks for the trip-owned supplier delivery slice.

These tests exercise the real Alembic migration history against a disposable
PostgreSQL namespace. They are skipped when no PostgreSQL test database is
reachable so that the SQLite-based unit suite still runs everywhere.

The configured target is taken from ``MIGRATION_TEST_DATABASE_URL``; the default
is the local development database, but every check runs inside a freshly created
schema that is dropped afterwards, so the existing ``public`` schema and data
are never touched.
"""

import contextlib
import os
import subprocess
import sys
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
from sqlalchemy.engine import make_url

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_DATABASE_URL = (
    "postgresql://fish_app:fishapp@localhost:5432/fish_distribution"
)
RAW_DATABASE_URL = os.environ.get(
    "MIGRATION_TEST_DATABASE_URL",
    DEFAULT_DATABASE_URL,
)

PRE_MIGRATION_REVISION = "f1913f2a0353"
NEW_REVISION = "ad99bbaf932e"


def _database_reachable() -> bool:
    try:
        with psycopg.connect(RAW_DATABASE_URL, connect_timeout=3) as connection:
            connection.execute("select 1")
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(
    not _database_reachable(),
    reason="no PostgreSQL test database is reachable",
)


def _alembic_database_url(schema: str) -> str:
    url = make_url(RAW_DATABASE_URL)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    url = url.update_query_dict({"options": f"-csearch_path={schema}"})
    return url.render_as_string(hide_password=False)


@contextlib.contextmanager
def disposable_schema():
    schema = f"verify_{uuid.uuid4().hex[:12]}"

    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'create schema "{schema}"')

    try:
        yield schema
    finally:
        with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
            connection.execute(f'drop schema "{schema}" cascade')


def run_alembic(schema: str, *arguments: str) -> subprocess.CompletedProcess:
    environment = {**os.environ, "DATABASE_URL": _alembic_database_url(schema)}

    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        check=False,
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


def seed_legacy_rows(schema: str) -> None:
    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'set search_path to "{schema}"')

        connection.execute(
            "insert into suppliers (name, phone, address) "
            "values ('Legacy Supplier', '9876500000', 'Pune')"
        )
        connection.execute("insert into fish_types (name) values ('Legacy Rohu')")
        connection.execute(
            "insert into trips (trip_date, supplier_id) "
            "values ('2026-10-15', 1)"
        )
        connection.execute(
            "insert into supplier_lists (trip_id, version_number, status) "
            "values (1, 1, 'FINAL')"
        )
        connection.execute(
            "insert into supplier_deliveries (supplier_list_id) values (1)"
        )
        connection.execute(
            "insert into supplier_delivery_items "
            "(delivery_id, fish_type_id, fish_type_name, planned_bags, "
            "delivered_bags, rejected_bags, damaged_bags) "
            "values (1, 1, 'Legacy Rohu', 10, 8, 1, 0)"
        )


def column_is_nullable(schema: str, table: str, column: str) -> bool:
    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'set search_path to "{schema}"')
        row = connection.execute(
            "select is_nullable from information_schema.columns "
            "where table_schema = %s and table_name = %s "
            "and column_name = %s",
            (schema, table, column),
        ).fetchone()

    assert row is not None, f"{table}.{column} does not exist"
    return row[0] == "YES"


def column_exists(schema: str, table: str, column: str) -> bool:
    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'set search_path to "{schema}"')
        row = connection.execute(
            "select 1 from information_schema.columns "
            "where table_schema = %s and table_name = %s "
            "and column_name = %s",
            (schema, table, column),
        ).fetchone()
    return row is not None


def foreign_key_exists(schema: str, table: str, column: str) -> bool:
    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'set search_path to "{schema}"')
        row = connection.execute(
            "select 1 from information_schema.key_column_usage kcu "
            "join information_schema.table_constraints tc "
            "on tc.constraint_name = kcu.constraint_name "
            "and tc.table_schema = kcu.table_schema "
            "where kcu.table_schema = %s and kcu.table_name = %s "
            "and kcu.column_name = %s "
            "and tc.constraint_type = 'FOREIGN KEY'",
            (schema, table, column),
        ).fetchone()
    return row is not None


def index_exists(schema: str, table: str, column: str) -> bool:
    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'set search_path to "{schema}"')
        rows = connection.execute(
            "select indexdef from pg_indexes "
            "where schemaname = %s and tablename = %s",
            (schema, table),
        ).fetchall()
    return any(f"({column})" in row[0] for row in rows)


def backfilled_trip_id(schema: str) -> int | None:
    with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
        connection.execute(f'set search_path to "{schema}"')
        row = connection.execute(
            "select trip_id from supplier_deliveries order by id limit 1"
        ).fetchone()
    assert row is not None
    return row[0]


def test_upgrade_backfills_trip_id_and_relaxes_constraints() -> None:
    with disposable_schema() as schema:
        first = run_alembic(schema, "upgrade", PRE_MIGRATION_REVISION)
        assert first.returncode == 0, first.stderr

        assert column_is_nullable(
            schema, "supplier_deliveries", "supplier_list_id"
        ) is False

        seed_legacy_rows(schema)

        result = run_alembic(schema, "upgrade", NEW_REVISION)
        assert result.returncode == 0, result.stderr

        # Existing rows are backfilled from their supplier list's trip.
        assert backfilled_trip_id(schema) == 1

        # Required trip ownership, relaxed list dependency and planned bags.
        assert (
            column_is_nullable(schema, "supplier_deliveries", "trip_id")
            is False
        )
        assert (
            column_is_nullable(
                schema, "supplier_deliveries", "supplier_list_id"
            )
            is True
        )
        assert (
            column_is_nullable(
                schema, "supplier_delivery_items", "planned_bags"
            )
            is True
        )

        # Foreign key, index and the new delivery-detail columns.
        assert foreign_key_exists(
            schema, "supplier_deliveries", "trip_id"
        )
        assert index_exists(schema, "supplier_deliveries", "trip_id")
        assert column_exists(schema, "supplier_deliveries", "tub_count")
        assert column_exists(schema, "supplier_deliveries", "vehicle")
        assert column_exists(schema, "supplier_deliveries", "driver")


def test_downgrade_restores_previous_schema_and_data() -> None:
    with disposable_schema() as schema:
        assert (
            run_alembic(schema, "upgrade", PRE_MIGRATION_REVISION).returncode
            == 0
        )

        seed_legacy_rows(schema)

        assert run_alembic(schema, "upgrade", NEW_REVISION).returncode == 0

        downgrade = run_alembic(schema, "downgrade", PRE_MIGRATION_REVISION)
        assert downgrade.returncode == 0, downgrade.stderr

        # The previous schema cannot represent a slip without a supplier list,
        # so trip ownership and the delivery details are gone again.
        assert column_exists(schema, "supplier_deliveries", "trip_id") is False
        assert column_exists(schema, "supplier_deliveries", "tub_count") is False

        assert (
            column_is_nullable(
                schema, "supplier_deliveries", "supplier_list_id"
            )
            is False
        )
        assert (
            column_is_nullable(
                schema, "supplier_delivery_items", "planned_bags"
            )
            is False
        )

        # Existing rows survive the round trip.
        with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
            connection.execute(f'set search_path to "{schema}"')
            row = connection.execute(
                "select supplier_list_id, planned_bags "
                "from supplier_deliveries d "
                "join supplier_delivery_items i on i.delivery_id = d.id"
            ).fetchone()
        assert row == (1, 10)

        # Re-running the upgrade restores the new schema and backfills again.
        assert run_alembic(schema, "upgrade", NEW_REVISION).returncode == 0
        assert backfilled_trip_id(schema) == 1


def test_upgrade_fails_safely_when_a_row_cannot_be_backfilled() -> None:
    with disposable_schema() as schema:
        assert (
            run_alembic(schema, "upgrade", PRE_MIGRATION_REVISION).returncode
            == 0
        )

        seed_legacy_rows(schema)

        # Simulate a corrupted legacy row whose supplier list does not exist.
        with psycopg.connect(RAW_DATABASE_URL, autocommit=True) as connection:
            connection.execute(f'set search_path to "{schema}"')
            connection.execute(
                "alter table supplier_deliveries "
                "drop constraint supplier_deliveries_supplier_list_id_fkey"
            )
            connection.execute(
                "update supplier_deliveries set supplier_list_id = 999999"
            )

        result = run_alembic(schema, "upgrade", NEW_REVISION)

        assert result.returncode != 0
        combined_output = f"{result.stdout}\n{result.stderr}"
        assert "cannot backfill" in combined_output.lower()

        # The failed migration must roll back; trip_id is never left behind.
        assert column_exists(schema, "supplier_deliveries", "trip_id") is False
