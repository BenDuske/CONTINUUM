"""ClickHouse MCP server integration for CONTINUUM.

The official mcp-clickhouse server exposes these tools:
  - run_query: Execute SQL queries on ClickHouse
  - list_databases: List all databases
  - list_tables: List tables in a database (with pagination)

ADK supports MCP tools natively via McpToolset — agents connect to the
mcp-clickhouse stdio server and get query tools automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp import StdioServerParameters

from continuum.config import config


def get_mcp_params() -> StdioServerParameters:
    """Return StdioServerParameters for the mcp-clickhouse MCP server.

    The binary is at .venv/bin/mcp-clickhouse (installed via pip).
    Environment variables configure the ClickHouse connection.
    """
    # Find the mcp-clickhouse binary in the same venv as this process
    venv_bin = Path(sys.executable).parent / "mcp-clickhouse"
    if not venv_bin.exists():
        # Fallback: try the project's venv
        project_root = Path(__file__).resolve().parents[3]
        venv_bin = project_root / ".venv" / "bin" / "mcp-clickhouse"

    return StdioServerParameters(
        command=str(venv_bin),
        args=[],
        env={
            "CLICKHOUSE_HOST": config.clickhouse.host,
            "CLICKHOUSE_PORT": str(config.clickhouse.port),
            "CLICKHOUSE_USER": config.clickhouse.user,
            "CLICKHOUSE_PASSWORD": config.clickhouse.password,
            "CLICKHOUSE_SECURE": str(config.clickhouse.secure).lower(),
            "CLICKHOUSE_VERIFY": "true",
            "CLICKHOUSE_CONNECT_TIMEOUT": "30",
            "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": "30",
            "CLICKHOUSE_ALLOW_WRITE_ACCESS": "true",
        },
    )
