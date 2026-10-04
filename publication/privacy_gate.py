"""Fail closed when a public FPS surface contains an identity from the private source.

The private DuckDB remains local input to this audit and is never copied into a
publication artifact.  The gate checks the application database and every tracked
text file.  Git history is audited separately because rewriting published ancestry
requires a coordinated force-push decision; it is reported, never silently changed.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DB = ROOT / "data" / "football_performance.duckdb"
PUBLIC_DB = ROOT / "data" / "football_performance_synthetic_demo.duckdb"
EXCLUDED = {"data/football_performance.duckdb"}


def _run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, encoding="utf-8", errors="replace")


def _identities(db: Path) -> set[str]:
    with duckdb.connect(str(db), read_only=True) as con:
        rows = con.execute(
            """
            SELECT display_name FROM players
            WHERE lower(coalesce(source_name, '')) <> 'collector'
            UNION SELECT display_name FROM teams
            WHERE lower(coalesce(source_name, '')) <> 'collector'
            UNION SELECT source_name FROM players
            WHERE source_name IS NOT NULL AND lower(source_name) <> 'collector'
            UNION SELECT source_name FROM teams
            WHERE source_name IS NOT NULL AND lower(source_name) <> 'collector'
            """
        ).fetchall()
    return {str(row[0]).strip() for row in rows if row[0] and len(str(row[0]).strip()) >= 4}


def _tracked_files() -> list[Path]:
    return [ROOT / p for p in _run("git", "ls-files").splitlines() if p and p not in EXCLUDED]


def _text_hits(identities: set[str]) -> list[str]:
    hits: list[str] = []
    for path in _tracked_files():
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".png", ".jpg", ".jpeg", ".pdf"}:
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore").casefold()
        found = sorted(name for name in identities if name.casefold() in text)
        if found:
            hits.append(f"{path.relative_to(ROOT)}: {', '.join(found[:3])}")
    return hits


def _public_db_hits(public_db: Path, identities: set[str]) -> list[str]:
    with duckdb.connect(str(public_db), read_only=True) as con:
        names = [str(x[0]) for x in con.execute("SELECT display_name FROM players UNION SELECT display_name FROM teams").fetchall()]
    return sorted(name for name in names if name in identities)


def _history_audit(identities: set[str]) -> list[str]:
    commits: list[str] = []
    for name in sorted(identities):
        out = _run("git", "log", "--all", "-S", name, "--format=%H")
        for commit in out.splitlines():
            if commit and commit not in commits:
                commits.append(commit)
    return commits


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate public anonymization boundaries")
    parser.add_argument("--private-db", type=Path, default=PRIVATE_DB)
    parser.add_argument("--public-db", type=Path, default=PUBLIC_DB)
    parser.add_argument("--history-audit", action="store_true")
    args = parser.parse_args()
    private_db = args.private_db.expanduser().resolve()
    public_db = args.public_db.expanduser().resolve()
    if not private_db.exists() or not public_db.exists():
        raise SystemExit("PRIVACY GATE: FAIL — private or public database is missing")
    identities = _identities(private_db)
    text_hits = _text_hits(identities)
    db_hits = _public_db_hits(public_db, identities)
    if text_hits or db_hits:
        for item in text_hits:
            print("TEXT LEAK: " + item)
        for item in db_hits:
            print("PUBLIC DB LEAK: " + item)
        raise SystemExit("PRIVACY GATE: FAIL")
    print(f"private_identifiers_checked={len(identities)}")
    print("public_db_identity_check=PASS")
    print("tracked_text_identity_check=PASS")
    if args.history_audit:
        commits = _history_audit(identities)
        print(f"history_commits_with_identity_introductions={len(commits)}")
        for commit in commits[:20]:
            print("HISTORY: " + commit)
    print("PRIVACY GATE: PASS")


if __name__ == "__main__":
    main()
