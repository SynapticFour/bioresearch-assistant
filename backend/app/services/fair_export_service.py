"""FAIR Data Export service: build ZIP packages with metadata and compliance check."""

import html
import json
import logging
import tempfile
import zipfile
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.isolation import apply_scope, get_scope_filter
from app.models.notebook import Notebook
from app.models.paper import Paper
from app.models.patient_record import PatientRecordModel
from app.schemas.fair_export import FAIRComplianceReport, FAIRExportOptions

logger = logging.getLogger(__name__)


class FAIRExportService:
    """Build FAIR-compliant export packages and run compliance checks."""

    async def create_export_package(
        self,
        db: AsyncSession,
        current_user: dict,
        options: FAIRExportOptions,
    ) -> bytes:
        """Build a FAIR export ZIP from user/team data.

        Structure:
        export_package.zip
        ├── README.md
        ├── metadata/
        │   ├── datacite.json
        │   ├── dublin_core.xml
        │   └── data_management_plan.md
        ├── literature/
        │   └── papers.json
        ├── phenopackets/
        │   └── *.json
        ├── notebooks/
        │   └── *.md
        └── FAIR_compliance.md
        """
        scope = get_scope_filter(current_user)
        spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        with zipfile.ZipFile(spool, "w", zipfile.ZIP_DEFLATED) as zf:
            # README
            readme = self._build_readme(options)
            zf.writestr("README.md", readme.encode("utf-8"))

            # Metadata
            datacite = await self.generate_datacite_metadata(options)
            zf.writestr(
                "metadata/datacite.json",
                json.dumps(datacite, indent=2, ensure_ascii=False).encode("utf-8"),
            )
            dublin_core = self._build_dublin_core(options)
            zf.writestr("metadata/dublin_core.xml", dublin_core.encode("utf-8"))
            dmp = await self.generate_dmp(options)
            zf.writestr("metadata/data_management_plan.md", dmp.encode("utf-8"))

            # Literature
            if options.include_papers:
                papers_stmt = select(Paper)
                papers_stmt = apply_scope(papers_stmt, Paper, scope)
                result = await db.execute(papers_stmt)
                papers = result.scalars().all()
                papers_data = [
                    {
                        "pmid": p.pmid,
                        "title": p.title,
                        "year": p.year,
                        "journal": p.journal,
                        "doi": p.doi,
                        "authors": list(p.authors) if p.authors else [],
                    }
                    for p in papers
                ]
                zf.writestr(
                    "literature/papers.json",
                    json.dumps(papers_data, indent=2, ensure_ascii=False).encode("utf-8"),
                )

            # Phenopackets
            if options.include_phenopackets:
                pp_stmt = select(PatientRecordModel)
                pp_stmt = apply_scope(pp_stmt, PatientRecordModel, scope)
                result = await db.execute(pp_stmt)
                records = result.scalars().all()
                for rec in records:
                    safe_name = "".join(c for c in rec.pseudonym_id if c.isalnum() or c in "._-")
                    zf.writestr(
                        f"phenopackets/{safe_name or 'phenopacket'}.json",
                        json.dumps(rec.phenopacket_json, indent=2, ensure_ascii=False).encode(
                            "utf-8"
                        ),
                    )

            # Notebooks
            if options.include_notebooks:
                nb_stmt = select(Notebook)
                nb_stmt = apply_scope(nb_stmt, Notebook, scope)
                result = await db.execute(nb_stmt)
                notebooks = result.scalars().all()
                for nb in notebooks:
                    safe_title = (
                        "".join(
                            c for c in (nb.title or "notebook") if c.isalnum() or c in " ._-"
                        ).strip()
                        or "notebook"
                    )
                    content = f"# {nb.title or ''}\n\n{nb.content or ''}"
                    zf.writestr(f"notebooks/{safe_title}.md", content.encode("utf-8"))

            if options.include_drs:
                from app.services.drs_service import list_objects as drs_list_objects

                drs_manifest = drs_list_objects(current_user=current_user)
                zf.writestr(
                    "drs/manifest.json",
                    json.dumps(drs_manifest, indent=2, ensure_ascii=False).encode("utf-8"),
                )

            # FAIR compliance report
            package_summary = {
                "papers": options.include_papers,
                "phenopackets": options.include_phenopackets,
                "notebooks": options.include_notebooks,
                "drs": options.include_drs,
                "license": options.license,
                "title": options.title,
            }
            report = await self.check_fair_compliance(package_summary)
            fair_md = self._fair_report_markdown(report, options)
            zf.writestr("FAIR_compliance.md", fair_md.encode("utf-8"))

        spool.seek(0)
        try:
            return spool.read()
        finally:
            spool.close()

    def _build_readme(self, options: FAIRExportOptions) -> str:
        return f"""# {options.title}

{options.description or "FAIR export from BioResearch Assistant."}

- **Authors:** {", ".join(options.authors) or "—"}
- **License:** {options.license}
- **Export date:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}
"""

    def _build_dublin_core(self, options: FAIRExportOptions) -> str:
        authors = "".join(f"  <dc:creator>{html.escape(a)}</dc:creator>\n" for a in options.authors)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>{html.escape(options.title)}</dc:title>
  <dc:description>{html.escape(options.description or "")}</dc:description>
{authors}
  <dc:rights>{html.escape(options.license)}</dc:rights>
  <dc:date>{datetime.now(UTC).strftime("%Y-%m-%d")}</dc:date>
</metadata>
"""

    def _fair_report_markdown(
        self, report: FAIRComplianceReport, options: FAIRExportOptions
    ) -> str:
        lines = [
            "# FAIR Compliance Report",
            "",
            f"**Score: {report.score}/100**",
            "",
            "| Principle | Status |",
            "|-----------|--------|",
            f"| F Findable | {'✅' if report.findable else '⚠️'} |",
            f"| A Accessible | {'✅' if report.accessible else '⚠️'} |",
            f"| I Interoperable | {'✅' if report.interoperable else '⚠️'} |",
            f"| R Reusable | {'✅' if report.reusable else '⚠️'} |",
            "",
        ]
        if report.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for r in report.recommendations:
                lines.append(f"- {r}")
        return "\n".join(lines)

    async def generate_datacite_metadata(self, options: FAIRExportOptions) -> dict:
        """DataCite JSON for Zenodo/DOI registration."""
        return {
            "titles": [{"title": options.title}],
            "descriptions": [
                {
                    "description": options.description or options.title,
                    "descriptionType": "Abstract",
                }
            ],
            "creators": [{"name": a} for a in options.authors],
            "license": {"id": options.license},
            "keywords": options.keywords,
            "fundingReferences": [{"funderName": options.funding}] if options.funding else [],
            "publicationYear": datetime.now(UTC).year,
        }

    async def generate_dmp(self, options: FAIRExportOptions) -> str:
        """Data Management Plan as Markdown."""
        return f"""# Data Management Plan

## Project
- **Title:** {options.title}
- **Description:** {options.description or "—"}

## Authors
{chr(10).join("- " + a for a in options.authors) or "- —"}

## License
{options.license}

## Funding
{options.funding or "Not specified"}

## FAIR
- Data will be shared under the above license.
- Metadata (DataCite) is included for findability.
- Standard formats (JSON, Markdown) are used for interoperability.
"""

    async def check_fair_compliance(self, package: dict) -> FAIRComplianceReport:
        """Check FAIR principles and return score + recommendations."""
        recommendations: list[str] = []
        findable = bool(package.get("title"))
        if not findable:
            recommendations.append("Add a title for findability.")
        accessible = True  # We describe access via license/README
        interoperable = True  # We use JSON, Markdown
        reusable = bool(package.get("license"))
        if not reusable:
            recommendations.append("Specify a license (e.g. CC-BY-4.0) for reuse.")
        if not package.get("funding") and "funding" not in str(package):
            recommendations.append(
                "Add funding ID for better findability (e.g. DFG project number)."
            )
        score = (
            (25 if findable else 0)
            + (25 if accessible else 0)
            + (25 if interoperable else 0)
            + (25 if reusable else 0)
        )
        return FAIRComplianceReport(
            findable=findable,
            accessible=accessible,
            interoperable=interoperable,
            reusable=reusable,
            score=min(100, score + (0 if recommendations else 10)),
            recommendations=recommendations,
        )
