---
name: dune
description: "Dune CLI for querying blockchain and on-chain data via DuneSQL, searching decoded contract tables, managing saved queries, and monitoring credit usage on Dune Analytics. Use when user asks about blockchain data, on-chain analytics, token transfers, DEX trades, smart contract events, wallet balances, Ethereum/EVM chain queries, DuneSQL, or says \"query Dune\", \"search Dune datasets\", or \"run a Dune query\"."
compatibility: Requires network access and the Dune CLI (auto-installed on first use). Works on macOS, Linux, and Windows.
allowed-tools: Bash(dune:*) Bash(curl:*) Read Write Edit
metadata:
  author: duneanalytics
  version: "1.2.0"
  cli_version: "0.1"
  upstream_repo: duneanalytics/skills
  upstream_file: skills/dune/SKILL.md
  upstream_sha: "6e61a3193206efc59d711066f06b4a794fb569fa"
---

## Setup

Run these four checks every time the skill is invoked.

### Step 0 — Upstream CLI update check (once per day)

```bash
mkdir -p ~/.dune
_LAST_CHECK=$(cat ~/.dune/.last-upstream-check 2>/dev/null || echo 0)
_NOW=$(date +%s)
if [ $((_NOW - _LAST_CHECK)) -gt 86400 ]; then
  _LATEST=$(curl -sf --max-time 5 \
    "https://api.github.com/repos/duneanalytics/skills/contents/skills/dune/SKILL.md" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['sha'])" 2>/dev/null || echo "")
  if [ -n "$_LATEST" ]; then
    echo "$_NOW" > ~/.dune/.last-upstream-check
    echo "$_LATEST" > ~/.dune/.upstream-sha-latest
    echo "UPSTREAM_FILE_SHA=$_LATEST"
  else
    echo "UPSTREAM_FILE_SHA=fetch_failed"
  fi
else
  echo "UPSTREAM_FILE_SHA=cached"
fi
_LATEST_CACHED=$(cat ~/.dune/.upstream-sha-latest 2>/dev/null | tr -d '[:space:]')
_ACK_SHA=$(cat ~/.dune/.upstream-ack 2>/dev/null | tr -d '[:space:]')
_BASE_SHA="6e61a3193206efc59d711066f06b4a794fb569fa"
_REF_SHA="${_ACK_SHA:-$_BASE_SHA}"
[ -n "$_LATEST_CACHED" ] && [ "$_LATEST_CACHED" != "$_REF_SHA" ] \
  && echo "UPSTREAM_UPDATE=yes" \
  || echo "UPSTREAM_UPDATE=no"
```

**If `UPSTREAM_UPDATE=yes`:** before proceeding, notify the user:

> The upstream `duneanalytics/skills` dune skill has been updated since you last reviewed.
> Your customized SKILL.md may need updating (new commands, changed flags, new workflows).
>
> Changes: `https://github.com/duneanalytics/skills/commits/main/skills/dune/SKILL.md`
> Current upstream: `https://github.com/duneanalytics/skills/blob/main/skills/dune/SKILL.md`

Then use AskUserQuestion:

> Want to open the upstream changelog now?
>
> A) Open commit history in browser and mark as reviewed
> B) Mark as reviewed without opening
> C) Remind me next time (skip)

- **A**: `open "https://github.com/duneanalytics/skills/commits/main/skills/dune/SKILL.md"` then `echo "$_LATEST_CACHED" > ~/.dune/.upstream-ack`
- **B**: `echo "$_LATEST_CACHED" > ~/.dune/.upstream-ack`
- **C**: continue — will ask again next time the daily check fires

**If `UPSTREAM_UPDATE=no`:** proceed silently.

### Step 1 — CLI detection

```bash
_DUNE_BIN=$(which dune 2>/dev/null || echo "")
[ -z "$_DUNE_BIN" ] && echo "DUNE_CLI=NOT_FOUND" || echo "DUNE_CLI=FOUND: $_DUNE_BIN"
```

**If `DUNE_CLI=FOUND`:** skip to Step 2.

**If `DUNE_CLI=NOT_FOUND`:** install following [Option A in install-and-recovery.md](references/install-and-recovery.md#option-a----automated-install-no-user-interaction):

1. Read the `PATH` environment variable. Look for an existing user-home directory already on PATH: `$HOME/.local/bin`, `$HOME/bin`, `$HOME/go/bin`, `$HOME/.cargo/bin`. Pick the first that exists. If none found, fall back to `$HOME/.local/bin`.
2. Only if using the fallback and the directory doesn't exist: `mkdir -p "$HOME/.local/bin"`
3. Download installer: `curl -sSfL -o /tmp/dune_install.sh https://github.com/duneanalytics/cli/raw/main/install.sh`
4. Run installer: `INSTALL_DIR="<chosen-dir>" bash /tmp/dune_install.sh`
5. Add to PATH for the session: `export PATH="<chosen-dir>:$PATH"`
6. Verify: `command -v dune`

If verification still fails, surface the Option B fallback from [install-and-recovery.md](references/install-and-recovery.md#option-b----user-assisted-install-fallback): ask the user to run the install in a separate terminal (`curl -sSfL https://github.com/duneanalytics/cli/raw/main/install.sh | bash`) and come back when done.

### Step 2 — Key resolution

```bash
_KEY_OK="no"
{ [ -n "${DUNE_API_KEY:-}" ] || [ -n "${DUNE_COMPANY_API_KEY:-}" ]; } && _KEY_OK="yes"
[ "$_KEY_OK" = "no" ] && grep -q "api_key" ~/.config/dune/config.yaml 2>/dev/null && _KEY_OK="yes"
echo "KEY_RESOLVABLE=$_KEY_OK"
```

**If `KEY_RESOLVABLE=yes`:** proceed to Step 3.

**If `KEY_RESOLVABLE=no`:** stop and tell the user:

> No Dune API key found. Set at least one in `.env` or run `dune auth --api-key <key>`:
> ```
> DUNE_API_KEY=your_key           # single key (read + write)
> DUNE_COMPANY_API_KEY=your_key   # optional: separate read key
> ```

### Step 3 — Routing injection check

```bash
_AGENTS_FILE=""
[ -f CLAUDE.md ] && _AGENTS_FILE="CLAUDE.md" || { [ -f AGENTS.md ] && _AGENTS_FILE="AGENTS.md"; }
_HAS_ROUTING="no"
[ -n "$_AGENTS_FILE" ] && grep -q "## Dune Analytics" "$_AGENTS_FILE" 2>/dev/null && _HAS_ROUTING="yes"
_DECLINED=$([ -f ~/.dune/.routing-declined ] && echo "yes" || echo "no")
echo "AGENTS_FILE: ${_AGENTS_FILE:-none}"
echo "HAS_DUNE_ROUTING: $_HAS_ROUTING"
echo "ROUTING_DECLINED: $_DECLINED"
```

**If `HAS_DUNE_ROUTING=yes` or `ROUTING_DECLINED=yes`:** skip — proceed with the user's request.

**If `HAS_DUNE_ROUTING=no` and `ROUTING_DECLINED=no`:** use AskUserQuestion to offer routing injection:

> Would you like to add Dune skill routing rules to your project? This tells Claude Code to
> always use `/dune` and `/dune-query-sync` instead of answering Dune tasks ad-hoc.
> It's a one-time addition (~15 lines) to your CLAUDE.md.
>
> A) Yes, add routing rules to CLAUDE.md
> B) No thanks, I'll invoke skills manually

**If A (accepted):**
- If `_AGENTS_FILE` is empty, create `CLAUDE.md`.
- Re-check that `## Dune Analytics` is not already present (idempotent guard).
- Append the following block exactly:

```markdown

## Dune Analytics

Two skills handle all Dune work. When the user's request matches any row below, ALWAYS
invoke the mapped skill via the Skill tool as your FIRST action. Do NOT answer directly.
Do NOT use other tools first.

Default to `/dune-query-sync` for anything involving local `.sql` files or `queries.yml`.
Use `/dune` for everything else.

| User intent / keywords | Skill |
|---|---|
| "pull", "sync", "get queries", "download SQL" | `/dune-query-sync` |
| "push", "update query on Dune", "deploy SQL changes" | `/dune-query-sync` |
| "add query ID", "track new query", "add to queries.yml" | `/dune-query-sync` |
| "run", "execute", "test query", "check results" | `/dune` |
| "create a new query" | `/dune` (`dune query create`) |
| "search datasets", "find a table", "Dune docs" | `/dune` |
| "credit usage", "how many credits" | `/dune` |
| "chart", "visualization", "dashboard" | `/dune` |
```

**If B (declined):** `mkdir -p ~/.dune && touch ~/.dune/.routing-declined`

---

After setup completes, proceed with the user's request. If a `dune` command fails, inspect the error and follow the recovery steps in [install-and-recovery.md](references/install-and-recovery.md):

- **"command not found"** → CLI not installed. See [CLI Not Found Recovery](references/install-and-recovery.md#cli-not-found-recovery).
- **401 / "unauthorized" / "missing API key"** → Auth failure. See [Authentication Failure Recovery](references/install-and-recovery.md#authentication-failure-recovery).
- **Unknown subcommand or flag / unexpected output** → Possible version mismatch. See [Version Compatibility](references/install-and-recovery.md#version-compatibility).

# Dune CLI

A command-line interface for [Dune](https://dune.com) -- the leading blockchain data platform. Use it to write and execute DuneSQL queries against on-chain data, discover datasets, search documentation, and monitor credit usage.

## Authentication

All commands except `docs search` require authentication via a Dune API key. The key is resolved in this priority order:

```bash
# 1. Flag (highest priority -- overrides everything)
dune query run 12345 --api-key <key>

# 2. Environment variable
export DUNE_API_KEY=<key>
dune query run 12345

# 3. Saved config file (lowest priority)
dune auth --api-key <key>        # saves to ~/.config/dune/config.yaml
dune query run 12345              # uses saved key
```

To save your key interactively (prompted from stdin):

```bash
dune auth
```

Config file location: `~/.config/dune/config.yaml`

### Key Resolution

Before any Dune command, resolve keys:

```bash
READ_KEY="${DUNE_COMPANY_API_KEY:-$DUNE_API_KEY}"
WRITE_KEY="${DUNE_API_KEY:-$DUNE_COMPANY_API_KEY}"
```

| Scenario | READ_KEY | WRITE_KEY |
|----------|----------|-----------|
| Only `DUNE_API_KEY` set | `DUNE_API_KEY` | `DUNE_API_KEY` |
| Only `DUNE_COMPANY_API_KEY` set | `DUNE_COMPANY_API_KEY` | `DUNE_COMPANY_API_KEY` |
| Both set (different) | `DUNE_COMPANY_API_KEY` | `DUNE_API_KEY` |
| Neither set | — | — |

**If both are empty** → stop and tell the user:

> No Dune API key found. Set at least one in `.env`:
> ```
> DUNE_API_KEY=your_key           # single key (read + write)
> DUNE_COMPANY_API_KEY=your_key   # optional: separate read key
> ```

Do not proceed with any `dune` command until a key is resolved.

## Global Flags

| Flag | Description |
|------|-------------|
| `--api-key <KEY>` | Dune API key (overrides `DUNE_API_KEY` env var and saved config) |

### Output Format (per-command flag)

Most commands support `-o, --output <FORMAT>` with values `text` (default, human-readable tables) or `json` (machine-readable).

> **Always use `-o json`** on every command that supports it. JSON output contains more detail than `text` (full API response objects vs. summarized tables) and is unambiguous to parse. The `text` format is for human terminal use and drops fields.

## DuneSQL

Dune uses **DuneSQL**, a Trino-based SQL dialect, as its query engine. Key points:

- All SQL passed to `--sql` flags or saved queries must be valid DuneSQL
- DuneSQL supports standard SQL with extensions for blockchain data types (addresses, hashes, etc.)
- Use `dune docs search --query "DuneSQL functions"` to look up syntax and functions
- Reference docs: [Writing Efficient Queries](https://docs.dune.com/query-engine/writing-efficient-queries), [Functions and Operators](https://docs.dune.com/query-engine/Functions-and-operators)

> **REQUIRED:** Before writing, optimizing, or modifying any DuneSQL query, you MUST read and apply [dunesql-cheatsheet.md](references/dunesql-cheatsheet.md). This covers data types, address handling, partition filters, column selection, CTE patterns, JOIN optimization, and common pitfalls. Do not write SQL without consulting it first.

## Key Concepts

### Performance Tiers

Query execution supports two tiers:

| Tier | Flag Value | Description |
|------|-----------|-------------|
| Medium | `medium` (default) | Standard compute resources. Suitable for most queries. |
| Large | `large` | Higher compute resources. Use for complex queries, large joins, or heavy aggregations. Costs more credits. |

### Execution States

After submitting a query, the execution progresses through these states:

| State | Meaning | Action |
|-------|---------|--------|
| `QUERY_STATE_PENDING` | Queued for execution | Wait |
| `QUERY_STATE_EXECUTING` | Currently running | Wait |
| `QUERY_STATE_COMPLETED` | Results available | Fetch results |
| `QUERY_STATE_FAILED` | Execution failed | Check error message; fix SQL and retry |
| `QUERY_STATE_CANCELLED` | Cancelled by user or system | Re-execute if needed |

### Dataset Categories

| Category | Description |
|----------|-------------|
| `canonical` | Core blockchain data (blocks, transactions, traces, logs) |
| `decoded` | ABI-decoded contract data (events and function calls) |
| `spell` | Dune Spellbook transformations (curated, higher-level tables like `dex.trades`) |
| `community` | Community-contributed datasets |

### Dataset Types

| Type | Description |
|------|-------------|
| `dune_table` | Core Dune-maintained tables |
| `decoded_table` | Contract ABI-decoded tables |
| `spell` | Spellbook transformation tables |
| `uploaded_table` | User-uploaded CSV/data tables |
| `transformation_table` | Materialized transformation tables |
| `transformation_view` | Virtual transformation views |

### Query Parameters

Parameters let you create reusable queries with variable inputs. Pass them as `--param key=value` (repeatable). The API auto-detects the type, but parameters support these types: `text`, `number`, `datetime`, `enum`.

```bash
dune query run 12345 --param wallet=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --param days=30 -o json
```

## Command Overview

| Command | Description | Auth |
|---------|-------------|------|
| `dune auth` | Save API key to config file | No |
| `dune query create` | Create a new saved query | Yes |
| `dune query get <id>` | Fetch a saved query's SQL and metadata | Yes |
| `dune query update <id>` | Update an existing query | Yes |
| `dune query archive <id>` | Archive a saved query | Yes |
| `dune query run <id>` | Execute a saved query and wait for results | Yes |
| `dune query run-sql` | Execute raw DuneSQL directly (no saved query needed) | Yes |
| `dune execution results <id>` | Fetch results of a previous execution | Yes |
| `dune dataset search` | Search the Dune dataset catalog | Yes |
| `dune dataset search-by-contract` | Find decoded tables for a contract address | Yes |
| `dune docs search` | Search Dune documentation | No |
| `dune usage` | Show credit and resource usage | Yes |

## Common Workflows

### Ad-hoc SQL Analysis

```bash
# Run a one-off query directly
dune query run-sql --sql "SELECT block_number, block_time FROM ethereum.blocks ORDER BY block_number DESC LIMIT 5" -o json
```

### Discover Tables, Then Query

```bash
# 1. Find relevant tables with column schemas
dune dataset search --query "uniswap swaps" --categories decoded --include-schema -o json

# 2. Write and execute SQL using discovered table/column names
dune query run-sql --sql "SELECT * FROM uniswap_v3_ethereum.evt_Swap LIMIT 10" -o json
```

### Find Contract Tables, Then Query

```bash
# 1. Find decoded tables for a specific contract
dune dataset search-by-contract --contract-address 0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984 --include-schema -o json

# 2. Query the discovered tables
dune query run-sql --sql "SELECT * FROM uniswap_v3_ethereum.evt_Transfer LIMIT 10" -o json
```

### Save and Execute a Reusable Query

```bash
# 1. Create a saved query with parameters
dune query create --name "Top Wallets" --sql "SELECT address, balance FROM ethereum.balances WHERE balance > {{min_balance}} LIMIT {{row_limit}}" -o json

# 2. Run it with parameter values
dune query run <returned-id> --param min_balance=1000 --param row_limit=50 -o json
```

### Long-Running Query (Submit and Poll)

```bash
# 1. Submit without waiting
dune query run 12345 --no-wait --performance large -o json
# Output: {"execution_id": "01ABC...", "state": "QUERY_STATE_PENDING"}

# 2. Check results later
dune execution results 01ABC... -o json
```

## Dune MCP

The official Dune MCP server (`https://api.dune.com/mcp/v1`) provides 12 tools across four categories. Configure it in Claude Code settings — check availability by looking for tools prefixed `mcp__dune__`.

### MCP tools vs CLI

Use CLI for everything the CLI can do. Use MCP **only** for what CLI cannot do.

| Task | Tool |
|------|------|
| Execute a query, fetch results | CLI (`dune query run`) |
| Create / update / get query | CLI (`dune query create/update/get`) |
| Search tables / find tables for a contract | CLI (`dune dataset search`, `dune dataset search-by-contract`) |
| Search Dune docs | CLI (`dune docs search`) |
| Check credit usage | CLI (`dune usage`) |
| **List all indexed blockchains** | **MCP only** (`listBlockchains`) |
| **Estimate table scan size** | **MCP only** (`getTableSize`) |
| **Create visualization (chart/counter/table)** | **MCP only** (`generateVisualization`) |

### Visualization workflow

`generateVisualization` creates charts, counters, and table widgets from query results.

1. Confirm the query ID
2. Confirm visualization type: `bar_chart`, `line_chart`, `scatter_chart`, `pie_chart`, `counter`, `table`
3. Call `generateVisualization` with query ID and type
4. Always confirm with the user before creating or deleting — changes are immediately live on Dune

### Blockchain listing

`listBlockchains` returns all indexed blockchains with their table counts. Use when the user asks "which chains does Dune support?" or needs to know available chain names for a query.

### Table size estimation

`getTableSize` estimates the data scanned (and credit cost) for a query against one or more tables. Use before running expensive queries on large tables to warn the user about potential credit usage.

## Security

- **Never** output API keys or tokens in responses. Before presenting CLI output to the user, scan for strings that look like API keys (e.g. long alphanumeric tokens, strings prefixed with `dune_`, or values from `DUNE_API_KEY`). Redact them with `[REDACTED]`.
- **Always** confirm with the user before running write commands (`query create`, `query update`, `query archive`)
- **Always** use `-o json` on every command -- JSON output is more detailed and reliably parseable
- Use `--temp` when creating throwaway queries to avoid cluttering the user's saved queries
- **Never** pass `--api-key` on the command line when other users might see the terminal history. Prefer `dune auth` or the `DUNE_API_KEY` environment variable.

## Reference Documents

Load the relevant reference when you need detailed command syntax and flags:

| Task | Reference |
|------|-----------|
| Create, get, update, or archive saved queries | [query-management.md](references/query-management.md) |
| Execute queries (run, run-sql) or fetch execution results | [query-execution.md](references/query-execution.md) |
| Search datasets or find tables for a contract address | [dataset-discovery.md](references/dataset-discovery.md) |
| Search documentation or check account usage | [docs-and-usage.md](references/docs-and-usage.md) |
| DuneSQL types, functions, common patterns, and pitfalls | [dunesql-cheatsheet.md](references/dunesql-cheatsheet.md) |
| CLI install, authentication, and version recovery | [install-and-recovery.md](references/install-and-recovery.md) |
