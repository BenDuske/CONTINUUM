# ClickHouse MCP Usage Evidence

**Track:** ClickHouse
**Requirement:** Project must actively use ClickHouse at runtime via the official ClickHouse MCP server (mcp-clickhouse).

## Runtime Integration Points

| Component | ClickHouse Usage | File |
|---|---|---|
| Production Memory | All production events stored/queried via ClickHouse | `src/continuum/tools/clickhouse_tools.py` |
| MCP Server | Official `mcp-clickhouse` server configured for ADK agents | `src/continuum/mcp/clickhouse_mcp.py` |
| Agent Queries | Every agent queries ClickHouse for production data | `src/continuum/agents/*.py` |
| Schema | 8 tables + materialized views for production intelligence | `src/continuum/schema/clickhouse_ddl.sql` |

## ClickHouse Tables

1. `production_events` — Core event stream (every production action)
2. `scenes` — Screenplay structure
3. `shots` — Planned coverage
4. `takes` — Captured footage metadata
5. `props` — Trackable production assets
6. `wardrobe` — Costume tracking per character
7. `continuity_issues` — Detected problems
8. `production_health` — Dashboard metrics
9. `scene_coverage_mv` — Materialized view for coverage analysis

## Package

```
mcp-clickhouse  # Official ClickHouse MCP server
clickhouse-connect  # Direct Python client for data loading
```
