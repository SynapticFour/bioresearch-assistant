# Varianten-Interpretation (optional)

Nicht diagnostisch, keine klinische Entscheidungsunterstützung.

Dieselbe Grenze wie BioResearch Assistant insgesamt: die Ausgabe ist eine strukturierte Gegenüberstellung für die Forschung. Sie ist keine Diagnose, keine Handlungsempfehlung und keine klinische Entscheidungshilfe. Keine formale Zertifizierung. Die Verantwortung bleibt beim Betreiber. Siehe [README](../../README.md) und [docs/COMPLIANCE.md](../../docs/COMPLIANCE.md).

## Wann das Modul aktiv ist

Nur wenn beides gesetzt ist:

- Locus (`LOCUS_ENABLED`)
- `FERRUM_DRS_URL` und `FERRUM_WES_URL`

Fehlt eines davon, bleibt das Modul inaktiv. Das ist kein Fehler und keine Ausnahme.

Locus allein und der Ferrum-Proxy allein bleiben die bestehenden Bausteine. Dieses Modul führt nur ihre schon vorliegenden Ausgaben zusammen.

## Was es tut

Es nimmt eine Locus-RAG-Antwort und Ferrum-Metadaten zu einer Variante entgegen, die der Aufrufer bereits hat. Die Zusammenfassung stellt Literaturbelege (`source_ref`, `title`, `corpus_id`) und technische Metadaten nebeneinander.

Es formuliert keinen Antworttext, keine Empfehlung und keine Diagnose. Der Freitext der Locus-Antwort wird nicht übernommen.

## Was es nicht tut

Kein HTTP-Aufruf, keine Datenbank, kein neues Archiv. Patientendaten, die Ferrum oder Solum nicht schon als technische Metadaten freigegeben haben, werden nicht gelesen und nicht in die Zusammenfassung übernommen. Unbekannte Felder, darunter `patient_id`, `subject_id` und Freitext wie `description`, fallen weg.
