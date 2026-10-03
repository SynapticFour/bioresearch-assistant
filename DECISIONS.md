# Engineering Decisions (ADR-lite)

Track important architectural and operational decisions here.

## Template

### YYYY-MM-DD - Decision title

- **Context:** Why this decision was needed.
- **Decision:** What was chosen.
- **Consequences:** Trade-offs, risks, and follow-up actions.

---

### 2026-10-03 - Resolve Ferrum URLs from the service registry

- **Context:** BRA proxies DRS and WES only when `FERRUM_DRS_URL` and `FERRUM_WES_URL` are set. A registry row is an address chosen by whoever can register. Following it without a host check would let that row point the proxy at loopback, link-local, or a cloud metadata address. An empty host allowlist that also accepted those addresses would make a public deployment an open proxy.
- **Decision:** When `SERVICE_REGISTRY_URL` is set, BRA GETs `/services?type=drsservice` and `/services?type=wes`. A missing `stale` field is fresh. `stale: true` is skipped. One fresh row supplies the URL. Zero fresh rows, or more than one, is an error that names the artifact and does not guess, unless `SERVICE_REGISTRY_SERVICE_ID` or `SERVICE_REGISTRY_ORGANIZATION` narrows the set to one. The service URL must use the same `http` or `https` scheme as the registry URL. Userinfo is rejected. Registry-resolved requests do not follow redirects. `SERVICE_REGISTRY_HOST_ALLOWLIST` empty means ordinary hosts are not restricted, and that is unsafe for a public deployment. Loopback (including the unspecified address), link-local, and cloud metadata addresses (`169.254.169.254`, `169.254.170.2`, `fd00:ec2::254`, `metadata.google.internal`, `metadata.goog`) are refused unless that host is listed in the allowlist. A non-empty allowlist admits only listed hosts, and listing a restricted host is the explicit allow. If the registry URL is unset, the static `FERRUM_DRS_URL` / `FERRUM_WES_URL` values are used. If lookup fails and a static URL is set, BRA logs that path as a static fallback and uses it. Visa verification stays in the existing passport code.
- **Consequences:** A private deployment can leave the allowlist empty and still cannot be pointed at metadata or loopback unless an operator lists that host. A public deployment must set the allowlist. The default when several fresh rows exist is still an error.
- **Alternatives considered:** Treat an empty allowlist as allow-all including metadata (rejected); pick the first fresh row when several exist (rejected); follow redirects after the check (rejected).

---

### 2026-04-10 - Establish cross-repo quality and security baseline

- **Context:** Repositories had uneven governance and CI security posture.
- **Decision:** Standardize governance docs, quality gates, and security scanning workflows.
- **Consequences:** Better consistency and contributor trust; ongoing maintenance required to keep checks aligned with stack changes.
