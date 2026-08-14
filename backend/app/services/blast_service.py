"""BLAST search via direct binary (WES workflow_url='blast') and Biopython parsing."""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.isolation import apply_scope, get_scope_filter
from app.models.paper import Paper
from app.schemas.blast import HSP, BLASTHit, BLASTParams, BLASTResults, BLASTStatistics
from app.schemas.wes import RunRequest, State
from app.services.wes_service import create_run as wes_create_run
from app.services.wes_service import get_run as wes_get_run
from app.services.wes_service import resolve_blast_database

logger = logging.getLogger(__name__)

TESTING_MODE = os.environ.get("TESTING") == "1"

if not TESTING_MODE:
    # Biopython BLAST XML parser (imports native extensions); safe only outside sandbox testing.
    from Bio.Blast import NCBIXML


def _query_to_fasta(query: str) -> bytes:
    """Turn query string into FASTA bytes (single sequence). If already FASTA-like, use as-is."""
    raw = query.strip()
    if raw.startswith(">"):
        return raw.encode("utf-8")
    # Single line or multi-line sequence
    lines = raw.splitlines()
    if not lines:
        return b">query\n"
    header = ">query"
    if len(lines) == 1 and len(lines[0]) < 80:
        return f"{header}\n{lines[0]}\n".encode()
    return (header + "\n" + "\n".join(lines) + "\n").encode("utf-8")


async def run_blast_search(
    db: AsyncSession,
    query: str,
    database: str,
    params: BLASTParams,
    *,
    current_user: dict[str, Any],
) -> str:
    """Start a BLAST search via direct binary (WES run with workflow_url='blast'). Returns run_id.

    BLAST runs in the background; use get_blast_results(run_id) after
    the run is COMPLETE (poll GET /api/v1/blast/results/{run_id}).
    Requires BLAST DB to be installed (see docs/TOOLS-SETUP.md).
    """
    fasta_bytes = _query_to_fasta(query)
    program = "blastn"
    db_name = resolve_blast_database(database)

    workflow_params: dict[str, str | float | int | None] = {
        "database": db_name,
        "evalue": params.evalue,
        "max_hits": params.max_hits,
        "program": program,
    }

    request = RunRequest(
        workflow_type="BLAST",
        workflow_type_version="1.0",
        workflow_url="blast",
        workflow_params=workflow_params,
        workflow_engine="blast",
    )
    attachments = [("query.fasta", fasta_bytes)]
    run_id = await wes_create_run(
        db, request, workflow_attachments=attachments, current_user=current_user
    )
    return str(run_id)


def _parse_blast_xml(xml_path: Path) -> BLASTResults:
    """Parse BLAST results.xml into BLASTResults (run_id set by caller).

    In sandboxed TESTING mode we avoid Biopython's BLAST parser (it imports native
    extensions that segfault in this environment) and use a tiny ElementTree
    parser that covers the subset of XML used in unit tests.
    """
    if TESTING_MODE:
        hits: list[BLASTHit] = []
        statistics = BLASTStatistics(num_hits=0, top_hit_ids=[])

        tree = ET.parse(xml_path)
        root = tree.getroot()

        program = root.findtext(".//BlastOutput_program") or ""
        db = root.findtext(".//BlastOutput_db") or ""
        if program:
            statistics.program = program.strip()
        if db:
            statistics.database = db.strip()

        # Iterate over <Hit> elements.
        for hit_el in root.findall(".//Hit"):
            hit_id = hit_el.findtext("Hit_id") or ""
            hit_def = hit_el.findtext("Hit_def") or None
            hit_len_text = hit_el.findtext("Hit_len")
            hit_len = int(hit_len_text) if hit_len_text and hit_len_text.isdigit() else None

            hsps_list: list[HSP] = []
            for hsp_el in hit_el.findall(".//Hsp"):
                score_text = hsp_el.findtext("Hsp_score")
                evalue_text = hsp_el.findtext("Hsp_evalue")
                q_from = hsp_el.findtext("Hsp_query-from")
                q_to = hsp_el.findtext("Hsp_query-to")
                h_from = hsp_el.findtext("Hsp_hit-from")
                h_to = hsp_el.findtext("Hsp_hit-to")

                score = float(score_text) if score_text else 0.0
                expect = float(evalue_text) if evalue_text else None

                hsps_list.append(
                    HSP(
                        score=score,
                        expect=expect,
                        identities=None,
                        align_length=None,
                        query_start=int(q_from) if q_from and q_from.isdigit() else None,
                        query_end=int(q_to) if q_to and q_to.isdigit() else None,
                        hit_start=int(h_from) if h_from and h_from.isdigit() else None,
                        hit_end=int(h_to) if h_to and h_to.isdigit() else None,
                        query=None,
                        match=None,
                        hit=None,
                    )
                )

            hits.append(
                BLASTHit(
                    hit_id=hit_id,
                    hit_def=hit_def,
                    hit_len=hit_len,
                    hsps=hsps_list,
                )
            )

        statistics.num_hits = len(hits)
        statistics.top_hit_ids = [h.hit_id for h in hits[:20]]
        return BLASTResults(run_id="", hits=hits, statistics=statistics)

    # Production path: Biopython NCBIXML.
    hits: list[BLASTHit] = []
    statistics = BLASTStatistics(num_hits=0, top_hit_ids=[])

    with xml_path.open("rb") as f:
        for record in NCBIXML.parse(f):
            if record.application and record.application.strip():
                statistics.program = record.application.strip()
            if record.database and record.database.strip():
                statistics.database = record.database.strip()
            if record.num_sequences is not None:
                statistics.num_sequences = record.num_sequences

            for alignment in record.alignments:
                hsps_list: list[HSP] = []
                for hsp in alignment.hsps:
                    hsps_list.append(
                        HSP(
                            score=float(hsp.score),
                            expect=float(hsp.expect) if hsp.expect is not None else None,
                            identities=getattr(hsp, "identities", None),
                            align_length=getattr(hsp, "align_length", None),
                            query_start=hsp.query_start,
                            query_end=hsp.query_end,
                            hit_start=hsp.hit_start,
                            hit_end=hsp.hit_end,
                            query=getattr(hsp, "query", None),
                            match=getattr(hsp, "match", None),
                            hit=getattr(hsp, "hit", None),
                        )
                    )
                hit_id = getattr(alignment, "hit_id", alignment.accession) or alignment.accession
                hit_def = getattr(alignment, "hit_def", None) or getattr(alignment, "title", None)
                hit_len = getattr(alignment, "length", None)
                hits.append(
                    BLASTHit(
                        hit_id=hit_id,
                        hit_def=hit_def,
                        hit_len=hit_len,
                        hsps=hsps_list,
                    )
                )

    statistics.num_hits = len(hits)
    statistics.top_hit_ids = [h.hit_id for h in hits[:20]]
    return BLASTResults(run_id="", hits=hits, statistics=statistics)


async def get_blast_results(
    db: AsyncSession, run_id: str, *, current_user: dict[str, Any]
) -> BLASTResults:
    """Load BLAST results for a WES run_id: read results.xml from run dir and parse with Biopython.

    Raises:
        ValueError: If run not found or not COMPLETE.
        FileNotFoundError: If results.xml missing.
    """
    run = await wes_get_run(db, run_id, current_user=current_user)
    if not run:
        raise ValueError(f"Run not found: {run_id}")
    if run.state != State.COMPLETE.value:
        raise ValueError(f"Run not complete (state={run.state}); poll status first.")

    settings = get_settings()
    run_dir = Path(settings.wes_work_dir) / run_id
    xml_path = run_dir / "results.xml"
    if not xml_path.exists():
        raise FileNotFoundError(f"BLAST results not found: {xml_path}")

    results = _parse_blast_xml(xml_path)
    results.run_id = run_id
    if run.outputs:
        results.raw_outputs = run.outputs
    return results


async def find_papers_for_hits(
    db: AsyncSession,
    blast_results: BLASTResults,
    max_papers_per_hit: int = 5,
    *,
    current_user: dict[str, Any],
) -> list[Paper]:
    """Find PubMed papers relevant to BLAST hits (Literature Mining ↔ BLAST).

    For each hit, searches PubMed with hit_id and (if present) hit_def terms,
    then returns papers from the local DB that match the resulting PMIDs.

    Returns:
        List of Paper (from DB) deduplicated by pmid.
    """
    from app.services.pubmed_service import PubMedService

    pmids: set[str] = set()
    async with PubMedService() as pubmed:
        for hit in blast_results.hits:
            terms = [hit.hit_id]
            if hit.hit_def:
                # Use first part of definition (e.g. gene name) and accession
                terms.append(hit.hit_def.split()[0] if hit.hit_def.split() else hit.hit_id)
            for term in terms[:2]:  # at most 2 queries per hit
                if not term or len(term) < 2:
                    continue
                try:
                    articles = await pubmed.search_pubmed(term, max_results=max_papers_per_hit)
                    for a in articles:
                        pmids.add(a.pmid)
                except Exception as e:  # noqa: BLE001
                    logger.warning("PubMed search failed for term %r: %s", term, e)

    if not pmids:
        return []

    stmt = select(Paper).where(Paper.pmid.in_(pmids))
    stmt = apply_scope(stmt, Paper, get_scope_filter(current_user))
    r = await db.execute(stmt)
    return list(r.scalars().unique().all())
