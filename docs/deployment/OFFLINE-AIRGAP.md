# Offline / Air-Gapped Deployment

Diese Anleitung deckt Installationen fuer isolierte Hardware ohne Internetzugriff ab.

## Zielbild

- **Build/Export Host (online):** zieht Images/Modelle und erstellt ein Transfer-Bundle.
- **Zielsystem (offline):** importiert Bundle und startet lokal per Compose.

Empfohlener Vorab-Check auf dem Zielsystem:

```bash
./scripts/deployment_preflight.sh --scenario offline
```

## 1) Auf Online-Host Bundle erzeugen

Im Projektroot:

```bash
chmod +x scripts/export_offline_bundle.sh
./scripts/export_offline_bundle.sh \
  --output-dir ./offline-bundle \
  --backend-image ghcr.io/synapticfour/bioresearch-assistant-backend:latest \
  --frontend-image ghcr.io/synapticfour/bioresearch-assistant-frontend:latest \
  --ollama-models "mistral,qwen2.5:7b" \
  --export-ollama-volume
```

Ergebnis:
- `images-*.tar.gz` (Docker images)
- optional `ollama-volume-*.tar.gz` (lokale Ollama Modell-Daten)
- `checksums.sha256`
- optional `ollama-models.txt`

## 2) Bundle auf Offline-Ziel transferieren

Per physischem Datentraeger, interner Spiegelstelle oder freigegebenem Transferprozess.

## 3) Auf Offline-Ziel importieren

```bash
chmod +x scripts/import_offline_bundle.sh
./scripts/import_offline_bundle.sh --bundle-dir ./offline-bundle
# inkl. Ollama Modell-Volume:
./scripts/import_offline_bundle.sh --bundle-dir ./offline-bundle --import-ollama-volume
```

## 4) Deployment starten

`.env` lokal anpassen, danach:

```bash
docker compose -f docker-compose.prod.yml up -d
```

## 5) Optional: grosse Modelle fuer GPU-Server

Beispiele fuer A100/100GB+-Klasse:
- `gpt-oss:120b`
- `deepseek-r1:70b`
- `qwen2.5:72b`

Hinweis: Modellgroessen koennen je nach Quantisierung variieren.

## Sicherheits- und Compliance-Hinweise

- Bundle-Checksummen vor Import verifizieren.
- `.env` nie in Git committen.
- Fuer klinische Umgebungen: internes Freigabeverfahren fuer Artefakte dokumentieren.
- Offline-Updateprozess als SOP (Versionierung, Rollback, Freigabe) festlegen.

## Update- und Bugfix-Delivery (offline)

Empfohlener Ablauf:
1. Auf Online-Buildhost neues Release-Bundle erzeugen (fester Release-Tag).
2. Checksummen/Signaturen intern freigeben.
3. Bundle auf Zielsystem importieren und Smoke-Tests fahren.
4. Erst danach produktiv umschalten.

Rollback:
- Vorheriges Bundle archiviert halten.
- Bei Problemen altes Bundle mit `import_offline_bundle.sh` erneut importieren.

