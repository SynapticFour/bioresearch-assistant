# API Versionierung & Deprecation Policy

## Aktuell

Aktuelle API Version: v1
Basis-URL: /api/v1/
GA4GH Endpunkte: /ga4gh/wes/v1/, /ga4gh/drs/v1/

## Semantic Versioning

MAJOR.MINOR.PATCH

- MAJOR: Breaking API Changes — neue Version (/api/v2/)
- MINOR: Neue Features, rückwärtskompatibel
- PATCH: Bug Fixes

## Deprecation Policy

- Breaking Changes nur in neuen Major Versionen
- Alte Versionen mindestens 12 Monate supported
- Deprecation Ankündigung mind. 3 Monate vorher
- Deprecated Endpunkte geben Deprecation Header zurück

## Stabilität der Endpunkte

| Endpunkt | Status | Stabil seit |
|----------|--------|-------------|
| /api/v1/literature/* | Stable | v0.1.0 |
| /api/v1/pseudonymize/* | Stable | v0.1.0 |
| /api/v1/library/* | Stable | v0.2.0 |
| /api/v1/phenopackets/* | Stable | v0.2.0 |
| /ga4gh/wes/v1/* | Stable | v0.1.0 |
| /ga4gh/drs/v1/* | Stable | v0.1.0 |
| /api/v1/auth/* | Stable | v0.2.0 |
