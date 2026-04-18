# dune-skills

Claude Code and Codex CLI skills for [Dune Analytics](https://dune.com). Two skills in one repo:

| Skill | What it does |
|---|---|
| `dune` | Query execution, dataset discovery, DuneSQL writing, credit monitoring via the `dune` CLI |
| `dune-query-sync` | Sync queries between local `.sql` files in git and Dune UI |

---

## Claude Code

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code/getting-started) and Node.js (for `npx`).

### Install

```bash
npx skills add yandhii/dune-skills --skill dune
npx skills add yandhii/dune-skills --skill dune-query-sync
```

Invoke with `/dune` or `/dune-query-sync` in any Claude Code session.

### CLAUDE.md routing block

The first time you invoke `/dune`, it checks whether routing rules already exist in your `CLAUDE.md` and offers to add them automatically. If you prefer to add them manually, use the block below.

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

### Dune CLI setup (required for `dune`)

```bash
# macOS / Linux
curl -sSfL -o /tmp/dune_install.sh https://github.com/duneanalytics/cli/raw/main/install.sh
INSTALL_DIR="$HOME/.local/bin" bash /tmp/dune_install.sh

# Windows (PowerShell)
$env:INSTALL_DIR = "$env:USERPROFILE\.local\bin"; irm https://github.com/duneanalytics/cli/raw/main/install.ps1 | iex
```

Authenticate:

```bash
dune auth --api-key your_key
# or: export DUNE_API_KEY=your_key
```

### Query sync setup (required for `dune-query-sync`)

Copy the template scripts into your project root:

```bash
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/pull.py
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/push.py
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/requirements.txt
pip install -r requirements.txt
```

Create `.env` in your project root (add to `.gitignore`):

```
DUNE_API_KEY=your_personal_key          # required for push — must own the queries
DUNE_COMPANY_API_KEY=your_company_key   # optional — used for pull to save personal credits
```

Bootstrap the queries directory:

```bash
mkdir -p queries
echo "query_ids: []" > queries/queries.yml
echo ".dune_push_ref" >> .gitignore
```

Add Dune query IDs to `queries/queries.yml`, then run `python pull.py` to fetch them as local `.sql` files.

---

## Codex CLI

Codex uses `AGENTS.md` for instructions. No skill installation needed.

### Prerequisites

Before adding the routing block, complete this setup in your project:

1. **Install Dune CLI** — same steps as the [Dune CLI setup](#dune-cli-setup-required-for-dune) section above
2. **Copy template scripts** into your project root:
   ```bash
   curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/pull.py
   curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/push.py
   curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/requirements.txt
   pip install -r requirements.txt
   ```
3. **Create `.env`** in your project root (add to `.gitignore`):
   ```
   DUNE_API_KEY=your_personal_key
   DUNE_COMPANY_API_KEY=your_company_key   # optional
   ```
4. **Bootstrap** the queries directory:
   ```bash
   mkdir -p queries
   echo "query_ids: []" > queries/queries.yml
   echo ".dune_push_ref" >> .gitignore
   ```
5. **Initialize git** if not already a repo — `push.py` uses `git diff` for change detection

### AGENTS.md block

Copy this into your `AGENTS.md`:

````markdown
## Dune Analytics

Two workflows handle Dune work. Default to the query-sync workflow for anything involving
local `.sql` files or `queries.yml`. Use the `dune` CLI for everything else.

### dune CLI — query execution and discovery

Requires: `dune` CLI installed and authenticated (`dune auth --api-key <key>` or `DUNE_API_KEY` env var).

| User asks | Command |
|---|---|
| Run / test a query | `dune query run <id> -o json` |
| Write ad-hoc SQL | `dune query run-sql --sql "..." -o json` |
| Find a table or dataset | `dune dataset search --query "..." -o json` |
| Check credit usage | `dune usage -o json` |
| Create a new query | `dune query create --name "..." --sql "..." -o json` |

Always pass `-o json`. Before writing DuneSQL, look up syntax with `dune docs search --query "..."`.

### dune-query-sync — local git ↔ Dune

Requires: `pull.py` and `push.py` in the project root, `.env` with `DUNE_API_KEY`.

| User asks | Action |
|---|---|
| "pull", "sync", "get queries from Dune" | `python pull.py` |
| "push", "deploy SQL changes to Dune" | `python push.py` |
| "preview what would be pushed" | `python push.py --dry-run` |
| "force push everything" | `python push.py --all` |
| "add a query ID", "track a new query" | Add ID to `queries/queries.yml`, then `python pull.py` |

Files live at `queries/{slug}___{id}.sql`. Tracked IDs are in `queries/queries.yml`.
````

---

## API keys

| Variable | Used by | Notes |
|---|---|---|
| `DUNE_API_KEY` | `push.py` (primary), `pull.py` (fallback), `dune` CLI | Must belong to the account that owns the queries |
| `DUNE_COMPANY_API_KEY` | `pull.py` (primary), `push.py` (fallback) | Optional — cheaper shared key for reads |

Key resolution in both scripts: if `DUNE_COMPANY_API_KEY` is set, reads use it; writes prefer `DUNE_API_KEY`. If only one key is set, both scripts use it for everything. If neither is set, both scripts exit with an error.

Note: `dune auth` stores the CLI key separately in `~/.config/dune/config.yaml` — it is not read from `.env`. If you run `dune` commands directly, authenticate with `dune auth --api-key your_key` in addition to setting the env vars.

**Ownership is permanent.** The key used to *create* a query on Dune owns it forever. Ownership cannot be transferred via API or CLI — only via the Dune web UI. Always create new queries with the personal key of the intended owner.

---

## templates/

`templates/pull.py` and `templates/push.py` are standalone scripts. No Dune SDK required — only `requests`, `pyyaml`, and `python-dotenv`.

| File | What it does |
|---|---|
| `pull.py` | Fetches SQL for every ID in `queries/queries.yml`, writes `queries/{slug}___{id}.sql` |
| `push.py` | Pushes `.sql` files changed since the last push (git-diff based); supports `--dry-run` and `--all` |
| `requirements.txt` | Pinned Python dependencies |

Copy them into your project root. They require the bootstrap steps above (git repo, `queries/queries.yml`, `.env`).

**How `push.py` detects changes:** after each fully successful push it writes the current git SHA to `.dune_push_ref`. On the next run it diffs against that SHA to find changed `.sql` files. First run (no ref file) pushes everything. If a push partially fails, the ref is not advanced — all changed files retry next run. After a rebase or hard reset, delete `.dune_push_ref` and re-run to reset the baseline.
