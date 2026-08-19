#!/usr/bin/env python3
"""Initialize the CONTINUUM ClickHouse schema.

Reads the DDL from src/continuum/schema/clickhouse_ddl.sql and executes it
against the configured ClickHouse instance.

Usage:
    python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import clickhouse_connect

from continuum.config import config


def main():
    print(f"Connecting to ClickHouse at {config.clickhouse.host}:{config.clickhouse.port}...")

    client = clickhouse_connect.get_client(
        host=config.clickhouse.host,
        port=config.clickhouse.port,
        username=config.clickhouse.user,
        password=config.clickhouse.password,
        secure=config.clickhouse.secure,
    )

    # Read DDL
    ddl_path = Path(__file__).resolve().parents[1] / "src" / "continuum" / "schema" / "clickhouse_ddl.sql"
    ddl = ddl_path.read_text()

    # Split on semicolons, strip comment-only lines, filter blanks
    raw_stmts = ddl.split(";")
    statements = []
    for s in raw_stmts:
        lines = [line for line in s.split("\n") if not line.strip().startswith("--")]
        clean = "\n".join(lines).strip()
        if clean:
            statements.append(clean)

    for i, stmt in enumerate(statements, 1):
        print(f"  [{i}/{len(statements)}] {stmt[:80]}...")
        try:
            client.command(stmt)
            print("  ✓ OK")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

    print("\n✅ Schema initialization complete.")
    print(f"   Database: {config.clickhouse.database}")
    print(f"   Host: {config.clickhouse.host}")


if __name__ == "__main__":
    main()
