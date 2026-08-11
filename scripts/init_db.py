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

    # Split on semicolons and execute each statement
    statements = [s.strip() for s in ddl.split(";") if s.strip() and not s.strip().startswith("--")]

    for i, stmt in enumerate(statements, 1):
        # Skip pure comments
        lines = [l for l in stmt.split("\n") if not l.strip().startswith("--")]
        clean = "\n".join(lines).strip()
        if not clean:
            continue

        print(f"  [{i}/{len(statements)}] {clean[:80]}...")
        try:
            client.command(clean)
            print(f"  ✓ OK")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

    print("\n✅ Schema initialization complete.")
    print(f"   Database: {config.clickhouse.database}")
    print(f"   Host: {config.clickhouse.host}")


if __name__ == "__main__":
    main()
