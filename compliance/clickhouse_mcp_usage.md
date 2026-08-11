# ClickHouse MCP Usage Evidence

**Track:** ClickHouse
**Requirement:** Project must actively use ClickHouse at runtime via the official
ClickHouse MCP server (`mcp-clickhouse`), connecting to ClickHouse Cloud.

## Runtime Integration — How mcp-clickhouse Is Called

1. **`src/continuum/mcp/clickhouse_mcp.py`** defines `get_mcp_params()` which returns
   `StdioServerParameters` pointing to the `mcp-clickhouse` binary with ClickHouse
   Cloud connection credentials.

2. **`src/continuum/runner.py`** creates `McpToolset(connection_params=get_mcp_params())`
   at startup. This launches the mcp-clickhouse stdio server as a subprocess.

3. **All 6 ADK agents** receive the `McpToolset` in their `tools=[]` list. When Gemini
   decides to query production data, it calls MCP tools (`run_query`, `list_databases`,
   `list_tables`) which execute against ClickHouse Cloud.

4. **`src/continuum/web/app.py`** endpoints trigger agent runs via the runner, which
   invoke mcp-clickhouse at runtime to answer production queries.

## ClickHouse Cloud Instance

- **Host:** `*.us-central1.gcp.clickhouse.cloud`
- **Provider:** GCP us-central1
- **Database:** `continuum`
- **Version:** 26.2

## ClickHouse Tables (9 total)

1. `production_events` — Core event stream (MergeTree)
2. `scenes` — Screenplay structure (ReplacingMergeTree)
3. `shots` — Planned coverage (ReplacingMergeTree)
4. `takes` — Captured footage metadata (MergeTree)
5. `props` — Trackable production assets (ReplacingMergeTree)
6. `wardrobe` — Costume tracking (ReplacingMergeTree)
7. `continuity_issues` — Detected problems (ReplacingMergeTree)
8. `scene_coverage_mv` — Coverage analysis (SummingMergeTree)
9. `production_health` — Dashboard metrics (ReplacingMergeTree)

## Packages

```
mcp-clickhouse      # Official ClickHouse MCP server (stdio transport)
clickhouse-connect   # Direct Python client (schema init + data loading + dashboard queries)
```

## Verified Runtime Behavior

Agent query → Gemini 3.5 Flash → MCP tool call (`run_query`) → mcp-clickhouse
→ ClickHouse Cloud → SQL result → Gemini → structured production intelligence response.

Tested end-to-end 2026-08-11: `run_query("SELECT * FROM continuum.props WHERE production_id = 'tls-001'")` → 4 rows returned, agent produced contextual analysis.
