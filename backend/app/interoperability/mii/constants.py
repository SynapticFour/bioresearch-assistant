"""MII / FHIR defaults (Zielgruppe: deutsche Forschungslabore, FDPG/DIZ, MII).

Entscheidungen (Market + regulatorischer Kontext):
- **FHIR R4**: De-facto-Standard fuer MII und nationale Plattformen; beste Tooling-/Validator-Unterstuetzung.
- **MII-KDS-Release**: Konfigurierbar; Default ein aktuelles Jahres-Release — Profile-URLs folgen dem offiziellen MII-IG.
- **Export v1**: Datei-basierter FHIR-Bundle-Download (kein FHIR-Server-Push), da FDPG/DIZ-Einreichung typischerweise Pakete/Dateien nutzt.
- **Broad Consent**: Max. eine **aktive** Erklaerung pro (pseudonym_id, policy_id); neuere Version **ersetzt** die vorherige (Status inactive/superseded).
- **Genomics**: Aus Phenopacket (Interpretationen/Gen-Symbole) als FHIR-Observations; VCF/DRS optional als DocumentReference-Verweise (wenn Assets vorhanden).
"""

# FHIR
FHIR_VERSION = "4.0.1"

# MII Kerndatensatz — Basis-Canonical (IG-Paket/Version via Settings nachziehen)
MII_FHIR_CANONICAL_BASE = "https://www.medizininformatik-initiative.de/fhir/core"

# Default policy id fuer UI und Seeds
DEFAULT_MII_BROAD_CONSENT_POLICY_ID = "mii-broad-consent"

# Consent category: research (HL7 v3-expanded)
CONSENT_CATEGORY_RESEARCH_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentcategorycodes"
CONSENT_CATEGORY_RESEARCH_CODE = "research"

# Consent scope: patient privacy
CONSENT_SCOPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentscope"
CONSENT_SCOPE_CODE = "patient-privacy"

# ActReason — research
ACT_REASON_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActReason"
ACT_REASON_RESEARCH_CODE = "RES"
