"""
Demo data seeder for BioResearch Assistant.

Populates the system with realistic example data for testing and demonstration.

Usage:
  docker compose -f docker-compose.full.yml \\
    exec backend python scripts/seed_demo_data.py
"""

import asyncio
import json
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Required when run via docker exec so app package is found
sys.path.insert(0, "/app")
# DATABASE_URL is always set in container (docker-compose loads .env)
DATABASE_URL = os.environ["DATABASE_URL"]

# ── Demo Papers (2 echte PubMed Papers) ─────────────
DEMO_PAPERS = [
    {
        "pmid": "33514641",
        "title": "CRISPR-Cas9 for medical genetic screens: applications and future perspectives",
        "abstract": (
            "CRISPR-Cas9 genome editing has revolutionized biomedical research. "
            "Here we review the application of CRISPR-Cas9 screens in human disease "
            "modelling, drug target identification, and therapeutic development. "
            "We discuss the challenges of off-target effects, delivery mechanisms, "
            "and regulatory considerations for clinical translation. "
            "Recent advances in base editing and prime editing offer improved "
            "precision and reduced off-target activity, expanding the therapeutic "
            "potential of CRISPR technologies."
        ),
        "authors": ["Anzalone AV", "Koblan LW", "Liu DR"],
        "year": "2021",
        "journal": "Nature Reviews Genetics",
        "doi": "10.1038/s41576-020-00288-9",
        "user_id": "dev-user",
        "team_id": "domain:synapticfour.de",
    },
    {
        "pmid": "34521899",
        "title": "Metformin and cancer: from molecular mechanisms to clinical use",
        "abstract": (
            "Metformin, the most widely prescribed antidiabetic drug, has demonstrated "
            "anticancer properties in numerous epidemiological and preclinical studies. "
            "The primary mechanism involves activation of AMP-activated protein kinase "
            "(AMPK) and inhibition of mTOR signaling, leading to reduced protein synthesis "
            "and cell proliferation. Clinical evidence suggests metformin may reduce "
            "cancer incidence and improve outcomes in diabetic patients with various "
            "malignancies including breast, colorectal, and pancreatic cancer. "
            "Ongoing clinical trials are evaluating metformin as adjuvant therapy "
            "in non-diabetic cancer patients."
        ),
        "authors": ["Foretz M", "Guigas B", "Bertrand L", "Pollard P", "Viollet B"],
        "year": "2021",
        "journal": "Nature Reviews Cancer",
        "doi": "10.1038/s41568-021-00344-2",
        "user_id": "dev-user",
        "team_id": "domain:synapticfour.de",
    },
]

# ── Demo Phenopacket ─────────────────────────────────
DEMO_PHENOPACKET = {
    "id": "demo-patient-001",
    "subject": {
        "id": "DEMO-P001",
        "sex": "FEMALE",
        "dateOfBirth": "1975-01-01",
    },
    "phenotypicFeatures": [
        {
            "type": {"id": "HP:0001250", "label": "Seizures"},
            "onset": {"age": {"iso8601duration": "P25Y"}},
        },
        {
            "type": {
                "id": "HP:0001263",
                "label": "Global developmental delay",
            },
        },
    ],
    "diseases": [
        {
            "term": {
                "id": "OMIM:613151",
                "label": "CDKL5 deficiency disorder",
            },
        },
    ],
    "metaData": {
        "created": "2026-01-01T00:00:00Z",
        "createdBy": "demo-user",
        "resources": [
            {
                "id": "hp",
                "name": "Human Phenotype Ontology",
                "url": "http://www.human-phenotype-ontology.org",
                "version": "2024-01",
                "namespacePrefix": "HP",
                "iriPrefix": "http://purl.obolibrary.org/obo/HP_",
            },
        ],
        "phenopacketSchemaVersion": "2.0",
    },
}

# ── Demo Notebook ────────────────────────────────────
DEMO_NOTEBOOK_TITLE = "CRISPR Forschungsnotizen — Demo"
DEMO_NOTEBOOK_CONTENT = """# CRISPR Forschungsnotizen

## Hintergrund

Diese Notizen dokumentieren unsere Recherche zu
CRISPR-Cas9 Anwendungen in der Krebstherapie.

## Wichtige Erkenntnisse

### Paper 1: CRISPR-Cas9 Screens
- CRISPR revolutioniert biomedizinische Forschung
- Anwendungen: Drug Target Identification,
  therapeutische Entwicklung
- Herausforderungen: Off-Target Effekte,
  Delivery-Mechanismen

### Paper 2: Metformin und Krebs
- Primärmechanismus: AMPK-Aktivierung, mTOR-Inhibition
- Klinische Evidenz für reduzierte Krebsinzidenz
- Laufende klinische Studien als Adjuvant-Therapie

## Nächste Schritte

1. Literaturrecherche zu BRCA1 CRISPR-Therapien
2. Phenopacket für Fallserie erstellen
3. BLAST-Analyse der Zielsequenzen

## Fragen

- Welche Delivery-Mechanismen sind für
  klinische Anwendung am vielversprechendsten?
- Kann Metformin mit CRISPR-Therapien kombiniert werden?

---
*Erstellt als Demo-Datensatz — BioResearch Assistant v1.0.0*
"""

# ── Demo DRS Files ───────────────────────────────────
DEMO_FASTA = """>Demo_BRCA1_Exon10
ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTTAG
AGTGTCCCATCTGTCTGGAGTTGATCAAGGAACCTGTCTCCACAAAGTGTGACCACATATTTTGCAA
ATTTTGCATGCTGAAACTTCTCAACCAGAAGAAAGGGCCTTCACAGTGTCCTTTATGTAAGAATGAT
"""

DEMO_VCF = """##fileformat=VCFv4.2
##reference=GRCh38
##FILTER=<ID=PASS,Description="All filters passed">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tDEMO_PATIENT
17\t41244429\trs80357713\tA\tT\t100\tPASS\tAF=0.001\tGT\t0/1
17\t41246709\trs28897672\tC\tT\t95\tPASS\tAF=0.0001\tGT\t0/1
"""


async def seed() -> None:
    """Insert demo papers, phenopacket, notebook, and DRS files."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from app.models.notebook import Notebook
        from app.models.paper import Paper
        from app.models.patient_record import PatientRecordModel

        print("🌱 Seeding demo data...")

        # Papers
        for paper_data in DEMO_PAPERS:
            r = await session.execute(select(Paper).where(Paper.pmid == paper_data["pmid"]))
            existing = r.scalar_one_or_none()
            if not existing:
                paper = Paper(
                    pmid=paper_data["pmid"],
                    title=paper_data["title"],
                    abstract=paper_data["abstract"],
                    authors=paper_data["authors"],
                    year=paper_data["year"],
                    journal=paper_data["journal"],
                    doi=paper_data["doi"],
                    user_id=paper_data.get("user_id"),
                    team_id=paper_data.get("team_id"),
                )
                session.add(paper)
                print(f"  ✓ Paper: {paper_data['pmid']}")
            else:
                print(f"  ⏭ Paper already exists: {paper_data['pmid']}")

        # Phenopacket
        r = await session.execute(
            select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == "DEMO-P001")
        )
        existing_pp = r.scalar_one_or_none()
        if not existing_pp:
            pp = PatientRecordModel(
                pseudonym_id="DEMO-P001",
                phenopacket_json=json.dumps(DEMO_PHENOPACKET, ensure_ascii=False),
                user_id="dev-user",
                team_id="domain:synapticfour.de",
            )
            session.add(pp)
            print("  ✓ Phenopacket: DEMO-P001")
        else:
            print("  ⏭ Phenopacket already exists")

        # Notebook (one demo notebook)
        r = await session.execute(
            select(Notebook)
            .where(Notebook.title == DEMO_NOTEBOOK_TITLE)
            .where(Notebook.user_id == "dev-user")
        )
        existing_nb = r.scalar_one_or_none()
        if not existing_nb:
            nb = Notebook(
                title=DEMO_NOTEBOOK_TITLE,
                content=DEMO_NOTEBOOK_CONTENT,
                tags=["demo", "CRISPR", "Onkologie"],
                user_id="dev-user",
                team_id="domain:synapticfour.de",
                linked_pmids=["33514641", "34521899"],
            )
            session.add(nb)
            print("  ✓ Notebook: CRISPR Forschungsnotizen")
        else:
            print("  ⏭ Demo notebook already exists")

        await session.commit()

    # DRS files via DRS Service registrieren (register_object schreibt unter drs_storage_path)
    from app.services.drs_service import register_object

    for filename, content in [
        ("demo_BRCA1_exon10.fasta", DEMO_FASTA),
        ("demo_variants.vcf", DEMO_VCF),
    ]:
        try:
            register_object(filename, content.encode("utf-8"))
            print(f"  ✓ DRS registered: {filename}")
        except ValueError as e:
            print(f"  ⚠ DRS skip {filename}: {e}")

    await engine.dispose()

    print("\n✅ Demo data seeded successfully!")
    print("\nDemo content:")
    print("  📄 2 Papers (CRISPR, Metformin)")
    print("  👤 1 Phenopacket (CDKL5 Patient)")
    print("  📓 1 Notebook (CRISPR Notizen)")
    print("  🧬 2 DRS Files (FASTA, VCF)")
    print("\nRun reembed-all to generate embeddings:")
    print("  curl -X POST http://localhost:8000/api/v1/library/reembed-all")


if __name__ == "__main__":
    asyncio.run(seed())
