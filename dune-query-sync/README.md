# dune-query-sync

Manage your [Dune Analytics](https://dune.com) queries as local `.sql` files in git. Pull queries down from Dune, edit SQL in your editor, commit, then push only what changed back up — with rate limiting and change detection handled automatically.

## Why

- Edit SQL with your editor and version control instead of the Dune web UI
- Review query changes in pull requests before pushing live
- Keep a backup of all your queries in git

## Install

```bash
npx skills add yandhii/dune-skills --skill dune-query-sync
```

Invoke with `/dune-query-sync` in any Claude Code session.

## Setup (one-time)

**1. Copy template scripts into your project root:**

```bash
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/pull.py
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/push.py
curl -O https://raw.githubusercontent.com/yandhii/dune-skills/main/templates/requirements.txt
pip install -r requirements.txt
```

**2. Create `.env` in your project root** (add to `.gitignore`):

```
DUNE_API_KEY=your_personal_key          # required — must own the queries you want to push
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

Find the ID in the URL of any Dune query: `dune.com/queries/<id>`.

**5. Pull to create local files:**

```bash
python pull.py
```

## Daily workflow

```bash
# Pull latest SQL from Dune (commit local edits first)
python pull.py

# Edit a query
$EDITOR queries/my_query___6280635.sql

# Commit to git
git add queries/ && git commit -m "update query"

# Preview what will be pushed
python push.py --dry-run

# Push changed queries to Dune
python push.py
```

## Commands

| What you want | Command |
|---|---|
| Pull all tracked queries from Dune | `python pull.py` |
| Push changed queries to Dune | `python push.py` |
| Preview what would be pushed | `python push.py --dry-run` |
| Force push everything | `python push.py --all` |
| Add a new query | Add ID to `queries/queries.yml`, then `python pull.py` |

## How change detection works

After each successful push, `push.py` records the current git SHA in `.dune_push_ref`. Next run it diffs against that SHA to find changed `.sql` files — so only modified queries are pushed, not everything.

- First run (no `.dune_push_ref`): pushes all tracked queries
- Partial failure: ref is not advanced, all changed files retry next run
- After rebase/reset: delete `.dune_push_ref` and re-run to reset the baseline

## API keys

| Variable | Used for | Notes |
|---|---|---|
| `DUNE_API_KEY` | Push (writes) | Must belong to the account that owns the queries |
| `DUNE_COMPANY_API_KEY` | Pull (reads) | Optional — cheaper shared key to save personal credits |

**Ownership is permanent.** The key used to *create* a query owns it forever — only transferable via Dune web UI, not via API.
