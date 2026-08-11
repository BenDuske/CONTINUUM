"""ClickHouse MCP server integration for CONTINUUM.

The official mcp-clickhouse server exposes these tools:
  - run_query: Execute SQL queries on ClickHouse
  - list_databases: List all databases
  - list_tables: List tables in a database (with pagination)

ADK supports MCP tools natively — agents can connect to any MCP-compatible
server as a tool source without custom adapter code.

This module configures the MCP connection for use with ADK agents.
"""

from __future__ import annotations

import os


def get_mcp_server_config() -> dict:
    """Return the MCP server configuration for ClickHouse.

    This config can be passed to ADK's MCP tool integration.
    The mcp-clickhouse server runs as a subprocess (stdio transport)
    or as an HTTP server (for production deployments).
    """
    return {
        "mcp-clickhouse": {
            "command": "uv",
            "args": [
                "run",
                "--with", "mcp-clickhouse",
                "--python", "3.10",
                "mcp-clickhouse",
            ],
            "env": {
                "CLICKHOUSE_HOST": os.environ.get("CLICKHOUSE_HOST", "localhost"),
                "CLICKHOUSE_PORT": os.environ.get("CLICKHOUSE_PORT", "8443"),
                "CLICKHOUSE_USER": os.environ.get("CLICKHOUSE_USER", "default"),
                "CLICKHOUSE_PASSWORD": os.environ.get("CLICKHOUSE_PASSWORD", ""),
                "CLICKHOUSE_SECURE": os.environ.get("CLICKHOUSE_SECURE", "true"),
                "CLICKHOUSE_VERIFY": os.environ.get("CLICKHOUSE_VERIFY", "true"),
                "CLICKHOUSE_CONNECT_TIMEOUT": "30",
                "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": "30",
                "CLICKHOUSE_ALLOW_WRITE_ACCESS": os.environ.get(
                    "CLICKHOUSE_ALLOW_WRITE_ACCESS", "true"
                ),
            },
        }
    }
