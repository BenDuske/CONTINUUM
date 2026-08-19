#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Initialize / upgrade the CONTINUUM ClickHouse schema.

Applies every migration under `src/continuum/schema/migrations/` in filename
order that has NOT already been recorded in `continuum.schema_migrations`.

The tracking table is created on first run. A migration file's basename
(e.g. `001_init.sql`) is its `version` — never rename or renumber an
applied migration; write a new one instead.

Usage:
    python scripts/init_db.py                    # apply all pending
    python scripts/init_db.py --dry-run          # print what would run
    python scripts/init_db.py --list             # list all + applied status
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import clickhouse_connect  # noqa: E402

from continuum.config import config  # noqa: E402

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "continuum" / "schema" / "migrations"
)


def _get_client():
    return clickhouse_connect.get_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.user,
        password=config.clickhouse.password,
        secure=config.clickhouse.secure,
    )


def _split_statements(ddl: str) -> list[str]:
    """Split a DDL file into statements, dropping SQL comments."""
    raw_stmts = ddl.split(";")
    statements = []
    for s in raw_stmts:
        lines = [line for line in s.split("\n") if not line.strip().startswith("--")]
        clean = "\n".join(lines).strip()
        if clean:
            statements.append(clean)
    return statements


def _ensure_tracking_table(client) -> None:
    """Create the schema_migrations tracking table if it doesn't exist."""
    client.command(f"CREATE DATABASE IF NOT EXISTS {config.clickhouse.database}")
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {config.clickhouse.database}.schema_migrations (
            version    String,
            applied_at DateTime DEFAULT now()
        ) ENGINE = MergeTree ORDER BY version
        """
    )


def _applied_versions(client) -> set[str]:
    result = client.query(
        f"SELECT version FROM {config.clickhouse.database}.schema_migrations"
    )
    return {row[0] for row in result.result_rows}


def _discover_migrations() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))


def _record(client, version: str) -> None:
    client.command(
        f"INSERT INTO {config.clickhouse.database}.schema_migrations (version) VALUES ('{version}')"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would run; make no changes."
    )
    parser.add_argument(
        "--list", action="store_true", help="List all migrations with applied status."
    )
    args = parser.parse_args()

    migrations = _discover_migrations()
    if not migrations:
        print(f"No migrations found under {MIGRATIONS_DIR}")
        return 0

    print(
        f"Connecting to ClickHouse at "
        f"{config.clickhouse.host}:{config.clickhouse.port}..."
    )
    client = _get_client()
    _ensure_tracking_table(client)
    applied = _applied_versions(client)

    if args.list:
        print(f"\n{'STATUS':<10} VERSION")
        print("-" * 40)
        for m in migrations:
            status = "APPLIED" if m.name in applied else "PENDING"
            print(f"{status:<10} {m.name}")
        return 0

    pending = [m for m in migrations if m.name not in applied]
    if not pending:
        print("✅ Schema is up to date.")
        return 0

    print(f"Pending migrations: {len(pending)}")
    for m in pending:
        print(f"  - {m.name}")

    if args.dry_run:
        print("\n(dry-run) no changes made.")
        return 0

    for m in pending:
        print(f"\n▶ Applying {m.name}")
        statements = _split_statements(m.read_text())
        for i, stmt in enumerate(statements, 1):
            print(f"  [{i}/{len(statements)}] {stmt[:80]}...")
            try:
                client.command(stmt)
                print("  ✓ OK")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                print(f"\nMigration {m.name} FAILED at statement {i}. Aborting.")
                return 1
        _record(client, m.name)
        print(f"  ✓ recorded {m.name} in schema_migrations")

    print("\n✅ Schema up to date.")
    print(f"   Database: {config.clickhouse.database}")
    print(f"   Host:     {config.clickhouse.host}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
