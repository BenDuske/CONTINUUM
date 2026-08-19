# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""ClickHouse MCP server integration for CONTINUUM.

The official mcp-clickhouse server exposes these tools:
  - run_query: Execute SQL queries on ClickHouse
  - list_databases: List all databases
  - list_tables: List tables in a database (with pagination)

ADK supports MCP tools natively via McpToolset — agents connect to the
mcp-clickhouse stdio server and get query tools automatically.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from mcp import StdioServerParameters

from continuum.config import config


def get_mcp_params() -> StdioServerParameters:
    """Return StdioServerParameters for the mcp-clickhouse MCP server.

    Finds the mcp-clickhouse binary: same dir as python, then PATH, then
    project .venv. Works in venvs, Docker containers, and Cloud Run.
    """
    # 1. Same directory as the running Python interpreter
    venv_bin = Path(sys.executable).parent / "mcp-clickhouse"
    if not venv_bin.exists():
        # 2. Anywhere on PATH (Docker: /usr/local/bin)
        found = shutil.which("mcp-clickhouse")
        if found:
            venv_bin = Path(found)
        else:
            # 3. Fallback: project's .venv
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
