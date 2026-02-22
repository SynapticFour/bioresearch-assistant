# Deployment auf Railway (Demo)

Railway eignet sich für eine schnelle Demo-Installation des BioResearch Assistant. Die folgende Tabelle beschreibt die Einschränkungen im Vergleich zu einer vollständigen Installation.

---

## ⚠️ Railway Demo — Bekannte Einschränkungen

| Feature | Railway Demo | Volle Installation |
|---------|--------------|---------------------|
| Pseudonymisierung Namen | ❌ Nur Regex | ✅ spaCy NLP |
| Semantische Suche | ❌ Deaktiviert | ✅ Embeddings |
| BLAST Suche | ❌ Kein Binary | ✅ Vollständig |
| Nextflow Pipelines | ❌ Nicht installiert | ✅ Vollständig |
| Datum/Email/Tel. Erkennung | ✅ Funktioniert | ✅ Funktioniert |
| Literature Mining PubMed | ✅ Funktioniert | ✅ Funktioniert |
| GA4GH WES/DRS | ✅ Funktioniert | ✅ Funktioniert |
| Phenopackets | ✅ Funktioniert | ✅ Funktioniert |

Für eine vollständige Demo empfehlen wir die lokale Installation oder Hetzner Cloud (ab €4.90/Monat).
