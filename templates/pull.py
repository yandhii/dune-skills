"""Pull Dune queries from queries/queries.yml to local .sql files."""

import os
import re
import sys
import yaml
import requests
from pathlib import Path
from dotenv import load_dotenv

QUERIES_DIR = Path("queries")
QUERIES_YML = QUERIES_DIR / "queries.yml"
DUNE_API_BASE = "https://api.dune.com/api/v1"


def resolve_read_key() -> str:
    company_key = os.getenv("DUNE_COMPANY_API_KEY")
    personal_key = os.getenv("DUNE_API_KEY")
    if company_key:
        return company_key
    if personal_key:
        return personal_key
    print("Error: set DUNE_API_KEY or DUNE_COMPANY_API_KEY in .env", file=sys.stderr)
    sys.exit(1)


def get_query(api_key: str, query_id: int) -> dict:
    resp = requests.get(
        f"{DUNE_API_BASE}/query/{query_id}",
        headers={"X-DUNE-API-KEY": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug.strip("_")


def make_header(name: str, query_id: int) -> str:
    return (
        f"-- part of a query repo\n"
        f"-- query name: {name}\n"
        f"-- query link: https://dune.com/queries/{query_id}\n\n"
    )


def main() -> None:
    load_dotenv()
    api_key = resolve_read_key()

    if not QUERIES_YML.exists():
        print(f"Error: {QUERIES_YML} not found", file=sys.stderr)
        sys.exit(1)

    with QUERIES_YML.open() as f:
        data = yaml.safe_load(f)
    query_ids: list[int] = [int(qid) for qid in (data.get("query_ids") or [])]

    if not query_ids:
        print("No query IDs in queries.yml — nothing to pull.")
        return

    QUERIES_DIR.mkdir(exist_ok=True)

    for qid in query_ids:
        try:
            info = get_query(api_key, qid)
        except Exception as exc:
            print(f"  ✗  {qid}: {exc}")
            continue

        name = info.get("name", str(qid))
        sql = info.get("query_sql", "")
        slug = slugify(name)
        filepath = QUERIES_DIR / f"{slug}___{qid}.sql"
        content = make_header(name, qid) + sql

        if filepath.exists():
            existing = filepath.read_text()
            existing_sql = "\n".join(
                line for line in existing.splitlines()
                if not line.startswith("-- ")
            ).strip()
            if existing_sql == sql.strip():
                print(f"  —  unchanged  {filepath.name}")
                continue
            filepath.write_text(content)
            print(f"  📝 updated   {filepath.name}")
        else:
            filepath.write_text(content)
            print(f"  ✅ new        {filepath.name}")


if __name__ == "__main__":
    main()
