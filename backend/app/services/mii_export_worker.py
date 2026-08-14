"""Background processing for queued MII export jobs."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_db_context
from app.services import mii_export_service as mii_svc

logger = logging.getLogger(__name__)


async def run_mii_export_job_task(job_id: UUID) -> None:
    """Run export with retries on transient failures; permanent ValueErrors fail the job."""
    settings = get_settings()
    backoff = float(settings.mii_export_retry_base_seconds)

    while True:
        async with get_db_context() as db:
            job = await mii_svc.load_mii_export_job_for_worker(db, job_id)
            if not job or job.status in ("succeeded", "failed", "dead_letter"):
                return
            if job.status != "queued":
                logger.warning("MII export job %s unexpected status %s", job_id, job.status)
                return

            if job.attempt_count >= job.max_attempts:
                await mii_svc.mark_job_dead_letter(db, job, "max_retries_exceeded")
                return

            job.attempt_count += 1
            job.status = "running"
            job.started_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(job)

            inp = job.input
            scope = job.scope_snapshot
            try:
                bundle, summary, validation_summary = await mii_svc.build_mii_bundle_for_pseudonyms(
                    db,
                    inp["pseudonym_ids"],
                    inp["modules"],
                    inp["policy_id"],
                    inp["research_project_ids"],
                    scope,
                    strict_profile_validation=bool(inp.get("strict_profile_validation")),
                    fail_on_partial_mapping=bool(inp.get("fail_on_partial_mapping")),
                )
            except ValueError as e:
                await mii_svc.mark_job_permanent_failure(db, job, str(e))
                return
            except Exception as e:
                logger.exception("MII export job %s transient error", job_id)
                await mii_svc.mark_job_queued_retry(db, job, f"transient:{type(e).__name__}:{e!s}")
                jittered = backoff * (0.5 + random.random())
                await asyncio.sleep(jittered)
                backoff = min(backoff * 2.0, 300.0)
                continue

            await mii_svc.persist_job_success(db, job, bundle, summary, validation_summary)
            return
