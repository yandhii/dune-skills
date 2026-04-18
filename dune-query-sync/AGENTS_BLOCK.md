
## dune-query-sync — local git ↔ Dune

Requires: `pull.py` and `push.py` in the project root, `.env` with `DUNE_API_KEY`.

| User asks | Action |
|---|---|
| "pull", "sync", "get queries from Dune" | `uv run pull.py` |
| "push", "deploy SQL changes to Dune" | `uv run push.py` (auto-commits + git pushes on success) |
| "preview what would be pushed" | `uv run push.py --dry-run` |
| "force push everything" | `uv run push.py --all` |
| "push to Dune only, skip git" | `uv run push.py --no-auto-commit` |
| "add a query ID", "track a new query" | Add ID to `queries/queries.yml`, then `uv run pull.py` |

Files live at `queries/{slug}___{id}.sql`. Tracked IDs are in `queries/queries.yml`.
