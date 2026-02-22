"""Automatische Metadaten-Extraktion.

Quellen (Priorität):
1. DOI → CrossRef API (kostenlos, kein Key nötig)
2. PubMed ID → NCBI API
3. Dateiinhalt → Header-Parsing (FASTA, VCF)
4. LLM Extraktion → Freitext → strukturierte Daten (später)
"""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "BioResearch/1.0 (mailto:info@synapticfour.de)"


class MetadataService:
    """Extract metadata from DOI, PMID, FASTA, VCF."""

    async def extract_from_doi(self, doi: str) -> dict | None:
        """CrossRef API — kostenlos, kein API Key.

        Liefert: Titel, Autoren, Jahr, Journal, Abstract.
        """
        doi = (doi or "").strip()
        if not doi:
            return None
        url = f"https://api.crossref.org/works/{doi}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                if resp.status_code != 200:
                    return None
                data = resp.json().get("message", {})
                title_list = data.get("title", [""])
                title = title_list[0] if title_list else ""
                authors_raw = data.get("author", [])
                authors = [
                    f"{a.get('family', '')} {str(a.get('given', ''))[:1]}".strip()
                    for a in authors_raw
                ]
                published = data.get("published", {}) or {}
                date_parts = published.get("date-parts", [[None]])
                year = date_parts[0][0] if date_parts and date_parts[0] else None
                container = data.get("container-title", [""])
                journal = container[0] if container else ""
                abstract = data.get("abstract", "") or ""
                if isinstance(abstract, str):
                    pass
                else:
                    abstract = ""
                return {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "journal": journal,
                    "doi": doi,
                    "abstract": abstract,
                    "source": "crossref",
                }
            except Exception as e:
                logger.warning("CrossRef lookup failed for %s: %s", doi, e)
                return None

    async def extract_from_pmid(self, pmid: str) -> dict | None:
        """PubMed Lookup via NCBI."""
        from app.services.pubmed_service import PubMedService

        pmid = (pmid or "").strip()
        if not pmid:
            return None
        service = PubMedService()
        try:
            article = await service.fetch_article(pmid)
            return {
                "title": article.title or "",
                "authors": list(article.authors) if article.authors else [],
                "year": article.year,
                "journal": article.journal or "",
                "doi": article.doi,
                "abstract": article.abstract or "",
                "pmid": article.pmid,
                "source": "pubmed",
            }
        except Exception as e:
            logger.warning("PubMed lookup failed for %s: %s", pmid, e)
            return None

    async def extract_from_fasta(self, content: str) -> dict:
        """FASTA Header Parsing.

        >accession description [organism]
        """
        lines = content.strip().split("\n")
        header = lines[0] if lines else ""

        if not header.startswith(">"):
            return {"format": "fasta", "source": "fasta_header"}

        header = header[1:].strip()
        parts = header.split(" ", 1)
        accession = parts[0] if parts else ""
        description = parts[1] if len(parts) > 1 else ""

        organism_match = re.search(r"\[([^\]]+)\]", description)
        organism = organism_match.group(1) if organism_match else ""

        sequence = "".join(line for line in lines[1:] if not line.startswith(">"))
        return {
            "name": accession,
            "description": description,
            "organism": organism,
            "sequence_length": len(sequence),
            "format": "fasta",
            "source": "fasta_header",
        }

    async def extract_from_vcf_header(self, content: str) -> dict:
        """VCF Header Metadaten extrahieren."""
        metadata: dict = {
            "format": "vcf",
            "reference": None,
            "samples": [],
            "contigs": [],
            "source": "vcf_header",
        }
        for line in content.split("\n"):
            if not line.startswith("#"):
                break
            if line.startswith("##reference="):
                metadata["reference"] = line.split("=", 1)[1].strip()
            elif line.startswith("##contig="):
                metadata["contigs"].append(line)
            elif line.startswith("#CHROM"):
                cols = line.split("\t")
                metadata["samples"] = cols[9:] if len(cols) > 9 else []
        return metadata
