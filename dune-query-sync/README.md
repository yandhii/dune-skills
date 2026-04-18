# dune-query-sync

Edit your [Dune Analytics](https://dune.com) queries as local `.sql` files, version-control them in git, and sync changes back to Dune with one command.

## Install the skill

**Option 1 — npx** (works for both Claude Code and Codex):
```bash
npx skills add yandhii/dune-skills --skill dune-query-sync
```

**Option 2 — curl** (no Node.js needed, pick your target):

*Claude Code* — copies the skill to `~/.claude/skills/`:
```bash
mkdir -p ~/.claude/skills/dune-query-sync
curl -sf https://raw.githubusercontent.com/yandhii/dune-skills/main/dune-query-sync/SKILL.md \
  > ~/.claude/skills/dune-query-sync/SKILL.md
```

*Codex CLI* — appends the routing block to your project's `AGENTS.md`:
```bash
curl -sf https://raw.githubusercontent.com/yandhii/dune-skills/main/dune-query-sync/AGENTS_BLOCK.md \
  >> AGENTS.md
```

After installing, invoke with `/dune-query-sync` in Claude Code, or just describe what you want in Codex — the routing block handles dispatch automatically.

---

## Setup (one-time)

**1. Download the scripts into your project root:**
```bash
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/pull.py
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/push.py
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/requirements.txt
uv pip install -r requirements.txt
```

**2. Create `.env` (add to `.gitignore`):**
```
DUNE_API_KEY=your_personal_key          # required for push — must own the queries
DUNE_COMPANY_API_KEY=your_company_key   # optional — used for pulls to save personal credits
```

**3. Bootstrap the queries directory:**
```bash
mkdir -p queries
echo "query_ids: []" > queries/queries.yml
echo ".dune_push_ref" >> .gitignore
```

**4. Add query IDs to `queries/queries.yml`:**
```yaml
query_ids:
  - 6280635
  - 6280948
```
Find the ID in any Dune query URL: `dune.com/queries/<id>`.

**5. Pull to create local files:**
```bash
uv run pull.py
```

---

## Daily workflow

```bash
# Pull latest SQL from Dune
uv run pull.py

# Edit a query
$EDITOR queries/my_query___6280635.sql

# Preview what will be pushed
uv run push.py --dry-run

# Push to Dune — auto-commits and git pushes on success
uv run push.py
```

## Commands

| What you want | Command |
|---|---|
| Pull all tracked queries from Dune | `uv run pull.py` |
| Push changed queries + auto-commit + git push | `uv run push.py` |
| Preview what would be pushed | `uv run push.py --dry-run` |
| Force push everything | `uv run push.py --all` |
| Push to Dune only, skip git commit | `uv run push.py --no-auto-commit` |
| Add a new query | Add ID to `queries/queries.yml`, then `uv run pull.py` |

---

## How it works

Files are named `{slug}___{id}.sql` in `queries/`. Tracked IDs live in `queries/queries.yml`.

After each successful push, `push.py` records the current git SHA in `.dune_push_ref` and auto-commits + pushes to git. Next run it diffs against that SHA — so only modified queries are sent to Dune, not everything.

- **First run** (no `.dune_push_ref`): pushes all tracked queries
- **Partial failure**: ref is not advanced, all changed files retry next run
- **After rebase/reset**: `rm .dune_push_ref` then re-run to reset the baseline

## API keys

| Variable | Used for | Notes |
|---|---|---|
| `DUNE_API_KEY` | Push (writes) | Must belong to the account that owns the queries |
| `DUNE_COMPANY_API_KEY` | Pull (reads) | Optional — cheaper shared key to save personal credits |

Ownership is permanent — the key used to *create* a query owns it forever. Transfer only via Dune web UI.
