"""Push local .sql changes back to Dune Analytics."""

import os
import re
import subprocess
import sys
import time
from pathlib import Path
import yaml
import requests
from dotenv import load_dotenv

QUERIES_DIR = Path("queries")
QUERIES_YML = QUERIES_DIR / "queries.yml"
PUSH_REF_FILE = Path(".dune_push_ref")
DUNE_API_BASE = "https://api.dune.com/api/v1"


def resolve_write_key() -> str:
    personal_key = os.getenv("DUNE_API_KEY")
    company_key = os.getenv("DUNE_COMPANY_API_KEY")
    if personal_key:
        return personal_key
    if company_key:
        return company_key
    print("Error: set DUNE_API_KEY in .env (must own the queries)", file=sys.stderr)
    sys.exit(1)


def update_query(api_key: str, query_id: int, sql: str) -> None:
    for attempt in range(3):
        resp = requests.patch(
            f"{DUNE_API_BASE}/query/{query_id}",
            headers={"X-DUNE-API-KEY": api_key, "Content-Type": "application/json"},
            json={"query_sql": sql},
            timeout=30,
        )
        if resp.status_code == 429:
            wait = 60 * (attempt + 1)
            print(f"  ⏳ rate limited, waiting {wait}s before retry {attempt + 1}/3...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return
    resp.raise_for_status()


def current_git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def changed_sql_files(ref_sha: str | None) -> list[Path]:
    if ref_sha is None:
        return list(QUERIES_DIR.glob("*.sql"))

    found: set[Path] = set()

    # Committed changes since last push ref
    r = subprocess.run(
        ["git", "diff", "--name-only", ref_sha, "--", str(QUERIES_DIR)],
        capture_output=True, text=True, check=True,
    )
    found.update(Path(p) for p in r.stdout.splitlines() if p.endswith(".sql"))

    # Uncommitted changes: staged, unstaged, and untracked files in queries/
    r = subprocess.run(
        ["git", "status", "--porcelain", "--", str(QUERIES_DIR)],
        capture_output=True, text=True, check=True,
    )
    for line in r.stdout.splitlines():
        path = line[3:].strip()
        if path.endswith(".sql"):
            found.add(Path(path))

    return list(found)


def extract_id_from_filename(path: Path) -> int | None:
    match = re.search(r"___(\d+)\.sql$", path.name)
    return int(match.group(1)) if match else None


def strip_header(content: str) -> str:
    lines = content.splitlines(keepends=True)
    body_lines = []
    in_header = True
    for line in lines:
        if in_header and (line.startswith("-- ") or line.strip() == ""):
            continue
        in_header = False
        body_lines.append(line)
    return "".join(body_lines)


def load_tracked_ids() -> set[int]:
    if not QUERIES_YML.exists():
        print(f"Error: {QUERIES_YML} not found", file=sys.stderr)
        sys.exit(1)
    with QUERIES_YML.open() as f:
        data = yaml.safe_load(f)
    return {int(qid) for qid in (data.get("query_ids") or [])}


def git_commit_and_push(pushed: list[tuple[Path, int]]) -> None:
    subprocess.run(["git", "add", str(QUERIES_DIR)], check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if staged.returncode != 0:
        n = len(pushed)
        msg = f"sync: push {n} quer{'y' if n == 1 else 'ies'} to Dune"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        print(f"Git: committed — {msg}")
    else:
        print("Git: nothing new to commit.")
    subprocess.run(["git", "push"], check=True)
    print("Git: pushed to remote.")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Push SQL changes to Dune")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--all", dest="force_all", action="store_true", help="Push all tracked queries")
    parser.add_argument("--no-auto-commit", action="store_true", help="Skip git commit + push after Dune push")
    args = parser.parse_args()

    load_dotenv()
    api_key = resolve_write_key()
    tracked_ids = load_tracked_ids()

    ref_sha: str | None = None
    if not args.force_all:
        if PUSH_REF_FILE.exists():
            ref_sha = PUSH_REF_FILE.read_text().strip() or None

    changed = changed_sql_files(ref_sha)

    to_push: list[tuple[Path, int]] = []
    for path in changed:
        qid = extract_id_from_filename(path)
        if qid is None or qid not in tracked_ids:
            continue
        if not path.exists():
            print(f"  ⚠  skipping deleted file: {path}")
            continue
        to_push.append((path, qid))

    if not to_push:
        print("Nothing changed — nothing to push.")
        return

    if args.dry_run:
        print("Dry run — would push:")
        for path, qid in to_push:
            print(f"  {path}  (query {qid})")
        return

    errors = 0
    for path, qid in to_push:
        sql = strip_header(path.read_text())
        try:
            update_query(api_key, qid, sql)
            print(f"  ✅ pushed  {path.name}")
        except Exception as exc:
            print(f"  ✗  {path.name}: {exc}")
            errors += 1
        time.sleep(4)  # Dune write API: 15 rpm on Free plan — need >= 4s between requests

    if errors == 0:
        if not args.no_auto_commit:
            git_commit_and_push(to_push)
        sha = current_git_sha()
        PUSH_REF_FILE.write_text(sha + "\n")
        print(f"Ref advanced to {sha[:8]}")
    else:
        print(f"\n{errors} error(s) — ref NOT advanced; all changed files will retry next run.")


if __name__ == "__main__":
    main()
