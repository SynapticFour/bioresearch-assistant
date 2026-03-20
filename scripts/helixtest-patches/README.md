# HelixTest CI patches

The `bioresearch-assistant` GitHub Actions job **`helixtest-ga4gh`** clones
[SynapticFour/HelixTest](https://github.com/SynapticFour/HelixTest.git) and applies:

- **`0001-default-bearer-for-confidential-drs-wes.patch`**

## Why this patch exists

The `bioresearch-assistant` profile enables **OIDC-backed Bearer auth** on GA4GH
routes. HelixTest’s DRS/WES contract tests use plain `GET`/`POST` without a token,
while the profile’s **token-only** auth checks intentionally omit the Bearer header
for negative cases.

Setting **`HELIXTEST_DEFAULT_BEARER`** (same value as **`TEST_BEARER`**) makes the
shared `HttpClient` attach a Bearer token to DRS/WES requests that use
`get_json` / `post_json` / `get_builder`, without changing auth-negative tests that
still call `client.inner()` directly.

**Preferred long-term fix:** merge equivalent logic into upstream HelixTest so this
patch can be dropped.

## Upstreaming

Consider adding optional env `HELIXTEST_DEFAULT_BEARER` to HelixTest’s
`crates/common/src/http.rs` and switching DRS/WES framework tests to a
`get_builder` helper (see patch).
