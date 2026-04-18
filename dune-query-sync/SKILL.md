---
name: dune-query-sync
description: "Sync Dune Analytics queries between a local git repo and Dune. Use when the user wants to pull queries from Dune, edit SQL locally, push changes back, or manage tracked query IDs."
compatibility: Requires Python 3.11+, a git repo with pull.py / push.py scripts (templates at yandhii/dune-skills).
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
metadata:
  author: yandhii
  version: "1.2.0"
---

# Dune Query Sync

A workflow for managing Dune Analytics queries as local `.sql` files in git. Pull queries down, edit them, commit, then push only the changed ones back to Dune.

## Environment Check

Run these checks at invocation before doing anything else:

```bash
[ -f pull.py ] && [ -f push.py ] || echo "MISSING_SCRIPTS: copy from yandhii/dune-skills/templates/ (pull.py, push.py, requirements.txt)"
[ -f queries/queries.yml ] || echo "MISSING_YML: run: mkdir -p queries && echo 'query_ids: []' > queries/queries.yml"
[ -n "${DUNE_API_KEY:-}${DUNE_COMPANY_API_KEY:-}" ] || echo "MISSING_KEY: set DUNE_API_KEY in .env (and optionally DUNE_COMPANY_API_KEY)"
git rev-parse --git-dir >/dev/null 2>&1 || echo "NOT_A_GIT_REPO: push.py requires git — run: git init"
python3 -c "import requests, yaml, dotenv" 2>/dev/null || echo "MISSING_DEPS: run: uv pip install -r requirements.txt"
```

For each `MISSING_*` or `NOT_A_GIT_REPO` line printed, surface the fix command to the user and stop — do not proceed until prerequisites are met.

## Project Structure

```
repo/
├── pull.py                  # Pull SQL from Dune → local files
├── push.py                  # Push local changes → Dune
├── queries/
│   ├── queries.yml          # Tracked query IDs
│   └── {slug}___{id}.sql    # One file per query (named by your scripts, not Dune)
└── .dune_push_ref           # Local: git SHA of last successful push (gitignored)
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A git repo (`.dune_push_ref` uses `git diff` — must be a git repo)
- `queries/` directory and `queries/queries.yml` file (create if missing)
- `.dune_push_ref` in `.gitignore`

Bootstrap a fresh repo:

```bash
mkdir -p queries
echo "query_ids: []" > queries/queries.yml
echo ".dune_push_ref" >> .gitignore
git init  # if not already a git repo
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` must include (always pin exact versions — `==` only, never `>=`, `^`, `~`):

```
requests==2.32.5
pyyaml==6.0.3
python-dotenv==1.2.2
```

> To update a pin: check the latest version, test it, then update the `==` constraint. Unpinned deps risk silent breakage.

### 3. Configure `.env`

Both scripts call `load_dotenv()` automatically — place a `.env` file in the repo root:

```
DUNE_API_KEY=your_personal_key          # required for push (must own the queries)
DUNE_COMPANY_API_KEY=your_company_key   # optional, used for pull (cheaper/shared)
```

### Key Resolution

| Env vars set | READ (pull.py) | WRITE (push.py) |
|---|---|---|
| Only `DUNE_API_KEY` | `DUNE_API_KEY` | `DUNE_API_KEY` |
| Only `DUNE_COMPANY_API_KEY` | `DUNE_COMPANY_API_KEY` | `DUNE_COMPANY_API_KEY` |
| Both set | `DUNE_COMPANY_API_KEY` | `DUNE_API_KEY` |
| Neither set | error — exit 1 | error — exit 1 |

**Push requires ownership**: `DUNE_API_KEY` must belong to the account that owns the queries on Dune. If the key is missing, `push.py` exits with an error — it does not fall back silently.

**Ownership is permanent**: the key used to *create* a query determines its owner. Ownership cannot be transferred via API, CLI, or MCP — only via Dune web UI. Always create new queries with the personal key of the intended owner.

---

## Tracking Queries (`queries.yml`)

List the Dune query IDs you want to sync:

```yaml
query_ids:
  - 6280635
  - 6280948
  - 6301755
```

To **add** a query: append its ID, then run `pull.py` to fetch it.

To **remove** a query: delete the ID from the list. The local `.sql` file is **not** deleted automatically — remove it manually if you want a clean state.

> Removing an ID from `queries.yml` prevents future pulls/pushes, but the stale `.sql` file stays on disk. It won't be pushed (not in tracked IDs), but it may cause confusion.

---

## Pulling Queries from Dune

> **Warning:** `pull.py` overwrites local `.sql` files if the remote SQL has changed. Commit or stash any local edits before pulling.

```bash
uv run pull.py
```

- Fetches SQL for every ID in `queries.yml` via the Dune REST API
- Saves as `queries/{slug}___{id}.sql` with a `--` comment header
- **Skips** files whose SQL hasn't changed (idempotent)
- Prints `✅ new`, `📝 updated`, or `—  unchanged` per file

Run after adding a new query ID, or to pick up edits made directly on Dune.

### Query Renames

If a query is renamed on Dune, `pull.py` creates a **new file** with the updated slug and leaves the old file in place. Delete the old file manually to avoid confusion.

---

## Editing Queries

Edit `.sql` files directly. Only the leading `--` comment lines in the header are stripped before pushing — any `--` comments inside the SQL body are preserved.

```sql
-- part of a query repo        ← stripped before push
-- query name: HIP-3           ← stripped before push
-- query link: https://...     ← stripped before push

SELECT
  coin,          -- this comment is kept
  SUM(volume)
FROM ...
```

Commit your changes to git before pushing:

```bash
git add queries/hip_3___6280635.sql
git commit -m "Add Paragon support to HIP-3 classification"
```

---

## Pushing Changes to Dune

```bash
# 1. Preview what would be pushed (always check first)
uv run push.py --dry-run

# 2. Push changed queries to Dune, then auto-commit + git push
uv run push.py

# 3. Force push all tracked queries (bypasses change detection)
uv run push.py --all

# 4. Push to Dune only, skip git commit + push
uv run push.py --no-auto-commit
```

### Auto-commit

After a fully successful Dune push, `push.py` automatically runs:
1. `git add queries/`
2. `git commit -m "sync: push N quer[y/ies] to Dune"` (skipped if nothing new to stage)
3. `git push`

Pass `--no-auto-commit` to skip this step.

### How Change Detection Works

After each **fully successful** push (zero errors), `push.py` records the current git SHA in `.dune_push_ref`. On the next run it combines:
- `git diff <ref> -- queries/` — committed changes since last push
- `git status --porcelain -- queries/` — staged, unstaged, and untracked changes

This means you can run `push.py` directly on uncommitted edits — no manual `git commit` needed first.

- **First run** (no `.dune_push_ref`): pushes all tracked queries and creates the ref
- **Subsequent runs**: only pushes files changed since the last push
- **Partial failure**: if any query fails, the ref is **not** advanced — all changed files will be retried next run
- **`--all`**: bypasses the ref, pushes everything regardless
- **`--dry-run`**: applies the same filter as a normal run, no writes to Dune

`.dune_push_ref` is local-only — keep it in `.gitignore`.

### Caveats

- **Rebase / reset / branch switch**: `git diff` is run against the SHA stored in `.dune_push_ref`. After a rebase or hard reset, that SHA may point to a different tree, causing incorrect diff output. If you rebase, delete `.dune_push_ref` and re-run to baseline: `rm .dune_push_ref && uv run push.py`
- **Non-linear history**: the ref assumes you're on a single linear branch. Merges and branch switches can produce unexpected diffs.

---

## Typical Workflow

```bash
# 1. Pull latest from Dune
uv run pull.py

# 2. Edit SQL locally
$EDITOR queries/hip_3___6280635.sql

# 3. Preview what will be pushed
uv run push.py --dry-run

# 4. Push to Dune + auto-commit + git push
uv run push.py
```

---

## File Naming Convention

Your scripts name files as `{slug}___{id}.sql` (three underscores, ID at end). Dune itself has no concept of local filenames — this is a local convention only.

```
hip_3___6280635.sql
hip_3_vs_others___6280948.sql
hip_3_metaandassetctxs___6301755.sql
```

The slug is derived from the query name on Dune (lowercased, spaces → underscores, special chars stripped) at pull time.

---

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `404 Not Found` on pull | Query private, deleted, or wrong ID | Check query visibility on Dune; confirm ID |
| `401 Unauthorized` on push | Wrong key or key lacks write access | Ensure `DUNE_API_KEY` belongs to the account that owns the query |
| `403 Forbidden` on push | Key valid but account doesn't own the query | Use the personal key of the query owner |
| `429 Too Many Requests` | Dune write API: 15 rpm (Free) / 70 rpm (Plus) | push.py retries automatically: 3 attempts, 60s × attempt backoff. If it still fails, wait ~5 min and re-run. On Free plan with large batches, increase `time.sleep(4)` in push.py further. |
| `push.py` shows "Nothing changed" | No SQL files changed since last push | Edit a file, or use `--all` to force |
| `git push` fails after Dune push | Remote rejected (not up to date) | Run `git pull --rebase` then `uv run push.py --no-auto-commit` |
| Unexpected files pushed after rebase | `.dune_push_ref` points to wrong commit | `rm .dune_push_ref` then re-run `push.py` |
| Duplicate `.sql` files after rename | Query renamed on Dune; pull created new slug | Delete the old file manually |
| Pull overwrites local edits | Pulled without committing first | Always commit before pulling |
| `yaml.YAMLError` | Malformed `queries.yml` | Validate YAML; ensure `query_ids:` is a list |
| `rm` not available (Windows) | Unix-only command | Use `del .dune_push_ref` in cmd, or `Remove-Item` in PowerShell |
