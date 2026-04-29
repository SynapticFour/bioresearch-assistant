# Externe Tools — Installation & Konfiguration

## BLAST

### BLAST Datenbank einrichten

BLAST ist im System installiert, braucht aber eine lokale Datenbank zum Suchen.

#### Schnellstart
```bash
./setup-blast-db.sh
# Wähle 1 für 16S (~1 GB, gut für Tests)
```

#### Produktionsdatenbank
```bash
./setup-blast-db.sh
# Wähle 2 für nt (~100 GB, Standard)
# ⚠️ Benötigt ~100 GB Speicherplatz
#    und mehrere Stunden Download
```

#### Speicherübersicht
| Datenbank | Größe | Verwendung |
|-----------|-------|------------|
| 16S_ribosomal_RNA | ~1 GB | Bakterien-ID, Tests |
| nt | ~100 GB | Standard Nukleotid |
| nr | ~300 GB | Protein |

### Lokal (macOS)
brew install blast
# Verify:
blastn -version

### Lokal (Ubuntu/Debian)
sudo apt install ncbi-blast+
blastn -version

### Datenbanken herunterladen
# Kleines Testset (nt_prok, ~15GB):
mkdir -p ~/blast-db
cd ~/blast-db
update_blastdb.pl --decompress nt_prok

# In .env eintragen:
BLAST_DB_PATH=/Users/DEINNAME/blast-db

### Docker / Backend-Container

BLAST läuft als Binary im Backend-Container (kein Nextflow für BLAST nötig). **Ohne Datenbank schlägt BLAST fehl** — die Fehlermeldung in der BLAST-Seite zeigt dann die Anleitung.

**Datenbank im Backend-Container einrichten:**

```bash
cd ~/bioresearch   # oder Ihr Installationsverzeichnis
docker compose -f docker-compose.full.yml exec backend bash

# Im Container:
mkdir -p /blast/db
cd /blast/db
# NCBI nt-Datenbank (⚠️ ~100GB):
update_blastdb.pl --decompress nt

# Alternativ kleine Test-Datenbank:
echo ">testseq
ATCGATCGATCG" > /tmp/test.fasta
makeblastdb -in /tmp/test.fasta -dbtype nucl -out /blast/db/test
# Dann in der UI Datenbank "test" wählen
```

Ohne Datenbank liefert BLAST einen Fehler (z. B. "BLAST database not found"). Die BLAST-UI zeigt in diesem Fall eine Anleitung an.

---

## Nextflow

### Lokal (macOS/Linux)
# Voraussetzung: Java 11+
java -version

# Nextflow installieren:
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
nextflow -version

### Workflows verfügbar
Das System unterstützt folgende vordefinierten Workflows:
- RNA-Seq (STAR + featureCounts)
- Variant Calling (GATK4)
- Custom Nextflow DSL2

### Workflow-Dateien Speicherort
Lege eigene .nf Dateien ab in:
workflows/
├── rna-seq.nf
├── variant-calling.nf
└── custom/
    └── mein-workflow.nf

In .env eintragen:
NEXTFLOW_WORK_DIR=/tmp/nextflow-work
WORKFLOWS_DIR=/pfad/zu/workflows/

---

## Ollama (lokales LLM)

### Lokal (macOS)
brew install ollama
ollama serve &
ollama pull mistral
# Alternativen:
# ollama pull llama3.2:3b
# ollama pull gemma3:4b
# ollama pull qwen2.5:7b
# ollama pull deepseek-r1:8b
# ollama pull gpt-oss:20b

### Docker
Ollama ist im `docker-compose.yml` mit **Profil** `ollama` definiert (startet nicht bei `docker compose up` ohne Profil):
```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull mistral
```
Für Locus + Backend in Docker: im `.env` z. B. `OLLAMA_URL=http://ollama:11434` setzen, Backend und Ollama gemeinsam starten (`--profile ollama` plus `backend`) und `LOCUS_ENABLED=1` nach Index-Seed.

In .env eintragen:
OLLAMA_URL=http://localhost:11434
# oder für Docker:
OLLAMA_URL=http://ollama:11434

---

## Railway Demo — Einschränkungen
Auf Railway sind folgende Tools NICHT installiert:
- BLAST (kein Binary)
- Nextflow (kein Java)
- Ollama (zu viel RAM)
Für vollständige Funktionalität: lokale Installation
oder Hetzner Cloud (ab €4.90/Monat).
