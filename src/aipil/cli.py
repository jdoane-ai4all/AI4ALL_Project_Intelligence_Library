"""Command-line entry point: python -m aipil.cli <command>."""
from __future__ import annotations

import argparse
import sqlite3
import sys

from aipil import paths


def connect() -> sqlite3.Connection:
    paths.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(paths.DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def cmd_ingest(args):
    from aipil.ingestion.workbook import import_workbook, init_db, load_workbook, validate, write_report
    wb = load_workbook(paths.RAW_WORKBOOK)
    rep = validate(wb)
    con = connect()
    init_db(con)
    import_workbook(wb, con, rep)
    write_report(rep, paths.REPORTS / "import_validation.md")
    print(f"Imported {rep.stats['n_unique_projects']} projects, {rep.stats['n_rationale_rows']} evaluations; "
          f"{len(rep.findings)} findings ({len(rep.errors)} errors). Report: reports/import_validation.md")


def cmd_fetch(args):
    from aipil.sources.retrieve import fetch_all
    fetch_all(kinds=args.kinds, limit=args.limit, force=args.force)


def cmd_build(args):
    from aipil.database.build import build
    build()


def main(argv=None):
    p = argparse.ArgumentParser(prog="aipil")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest").set_defaults(fn=cmd_ingest)
    f = sub.add_parser("fetch")
    f.add_argument("--kinds", nargs="+", default=["text", "pdf"])
    f.add_argument("--limit", type=int)
    f.add_argument("--force", action="store_true")
    f.set_defaults(fn=cmd_fetch)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
