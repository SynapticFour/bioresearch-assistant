"""Backfill DRS ACL entries and NULL paper/WES owners.

After isolation was added, objects without owners are hidden in user/team mode.
Run this once against the production database after Alembic 009/010.

Usage (from backend/, with DATABASE_URL set):

  python scripts/backfill_tenancy.py --user-id USER [--team-id TEAM] [--dry-run]
  python scripts/backfill_tenancy.py --user-id USER --drs-only
  python scripts/backfill_tenancy.py --user-id USER --sql-only

Assigns the given user (and optional team) to:
- DRS files under drs_storage_path that have no .drs-acl.json entry
- papers.user_id / workflow_runs.user_id that are NULL

Does not overwrite existing ACL owners or non-NULL SQL owner columns.
If two NULL-owner papers share a pmid, only the first is assigned (partial unique).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import sys
from pathlib import Path

# Allow `python scripts/backfill_tenancy.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.database import get_db_context
from app.models.paper import Paper
from app.models.workflow_run import WorkflowRun
from app.services import drs_service

logger = logging.getLogger("backfill_tenancy")


def _checksum_md5(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def backfill_drs(user_id: str, team_id: str | None, dry_run: bool) -> int:
    root = Path(get_settings().drs_storage_path).resolve()
    if not root.is_dir():
        logger.warning("DRS storage path does not exist: %s", root)
        return 0
    acl = drs_service._load_acl()
    assigned = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == drs_service._ACL_NAME or path.name.endswith(".tmp"):
            continue
        try:
            object_id = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue
        if object_id in acl and (acl[object_id] or {}).get("user_id"):
            continue
        assigned += 1
        if dry_run:
            logger.info("DRY-RUN DRS %s -> user_id=%s team_id=%s", object_id, user_id, team_id)
            continue
        drs_service._record_acl(
            object_id,
            user_id=user_id,
            team_id=team_id,
            md5=_checksum_md5(path),
            size=path.stat().st_size,
        )
        logger.info("DRS %s assigned to user_id=%s", object_id, user_id)
    return assigned


async def backfill_sql(user_id: str, team_id: str | None, dry_run: bool) -> tuple[int, int]:
    papers_n = 0
    runs_n = 0
    async with get_db_context() as db:
        paper_rows = list(
            (await db.execute(select(Paper).where(Paper.user_id.is_(None)))).scalars().all()
        )
        seen_pmid: set[str] = set()
        for paper in paper_rows:
            if paper.pmid in seen_pmid:
                logger.warning(
                    "Skipping paper id=%s pmid=%s (duplicate NULL-owner pmid)",
                    paper.id,
                    paper.pmid,
                )
                continue
            seen_pmid.add(paper.pmid)
            papers_n += 1
            if dry_run:
                logger.info("DRY-RUN paper id=%s pmid=%s", paper.id, paper.pmid)
                continue
            paper.user_id = user_id
            if team_id is not None:
                paper.team_id = team_id

        run_stmt = (
            update(WorkflowRun)
            .where(WorkflowRun.user_id.is_(None))
            .values(user_id=user_id, **({"team_id": team_id} if team_id is not None else {}))
        )
        if dry_run:
            runs_n = len(
                list(
                    (
                        await db.execute(select(WorkflowRun).where(WorkflowRun.user_id.is_(None)))
                    ).scalars().all()
                )
            )
            logger.info("DRY-RUN would assign %s workflow_runs", runs_n)
        else:
            result = await db.execute(run_stmt)
            runs_n = result.rowcount or 0
    return papers_n, runs_n


async def _amain(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    drs_n = 0
    papers_n = 0
    runs_n = 0
    if not args.sql_only:
        drs_n = backfill_drs(args.user_id, args.team_id, args.dry_run)
    if not args.drs_only:
        papers_n, runs_n = await backfill_sql(args.user_id, args.team_id, args.dry_run)
    logger.info(
        "Done. DRS=%s papers=%s workflow_runs=%s dry_run=%s",
        drs_n,
        papers_n,
        runs_n,
        args.dry_run,
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill DRS ACL and NULL tenancy columns")
    parser.add_argument("--user-id", required=True, help="Owner user_id (token sub) to assign")
    parser.add_argument("--team-id", default=None, help="Optional team_id to assign")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without writing")
    parser.add_argument("--drs-only", action="store_true", help="Only backfill DRS ACL")
    parser.add_argument("--sql-only", action="store_true", help="Only backfill papers/WES rows")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
