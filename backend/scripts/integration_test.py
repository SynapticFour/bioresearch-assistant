"""
Integration test script for BioResearch Assistant.
Tests all major functionality against a running instance.

Usage:
  python scripts/integration_test.py
  python scripts/integration_test.py --base-url http://localhost:8000
"""
# ruff: noqa: ANN202

import argparse
import asyncio
import sys
from collections.abc import Awaitable
from datetime import datetime

import httpx

BASE_URL = "http://localhost:8000"
PASS = "✅"
FAIL = "❌"

results: list = []


async def test(name: str, coro: Awaitable[None]) -> None:
    try:
        await coro
        results.append((PASS, name))
        print(f"  {PASS} {name}")
    except AssertionError as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL} {name}: {e}")
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL} {name}: {e}")


async def run_all(base_url: str) -> bool:
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as c:
        print("\n🔍 BioResearch Assistant — Integration Tests")
        print(f"   Target: {base_url}")
        print(f"   Time: {datetime.now().isoformat()}")
        print("─" * 50)

        # ── Health ────────────────────────────────────
        print("\n📊 Health & System")

        async def test_health():
            r = await c.get("/api/v1/health")
            assert r.status_code == 200
            assert r.json().get("status") == "healthy"

        await test("Health endpoint", test_health())

        async def test_health_ready():
            r = await c.get("/api/v1/health/ready")
            assert r.status_code == 200

        await test("Health ready", test_health_ready())

        async def test_gaia_x():
            r = await c.get("/api/v1/gaia-x/self-description")
            assert r.status_code in (200, 503)

        await test("GAIA-X self-description", test_gaia_x())

        # ── Auth ──────────────────────────────────────
        print("\n🔐 Auth")

        async def test_auth_status():
            r = await c.get("/api/v1/auth/status")
            assert r.status_code == 200

        await test("Auth status", test_auth_status())

        async def test_auth_me():
            r = await c.get("/api/v1/auth/me")
            assert r.status_code == 200

        await test("Auth me (dev mode)", test_auth_me())

        # ── Library ───────────────────────────────────
        print("\n📚 Library")

        async def test_list_papers():
            r = await c.get("/api/v1/library/papers")
            assert r.status_code == 200
            assert isinstance(r.json(), list)

        await test("List papers", test_list_papers())

        async def test_add_paper():
            r = await c.post(
                "/api/v1/library/papers",
                json={
                    "pmid": "99999999",
                    "title": "Integration Test Paper",
                    "abstract": "This is a test abstract for integration testing.",
                    "authors": ["Test Author"],
                    "year": "2026",
                    "journal": "Test Journal",
                },
            )
            assert r.status_code in (200, 201, 409)

        await test("Add paper", test_add_paper())

        async def test_semantic_search():
            r = await c.post(
                "/api/v1/library/semantic",
                json={
                    "query": "test abstract",
                    "threshold": 1.5,
                    "limit": 5,
                },
            )
            assert r.status_code == 200

        await test("Semantic search", test_semantic_search())

        async def test_rag():
            r = await c.post(
                "/api/v1/library/rag",
                json={
                    "question": "What is this paper about?",
                    "top_k": 3,
                    "language": "en",
                },
                timeout=120,
            )
            assert r.status_code in (200, 404, 502)

        await test("RAG endpoint", test_rag())

        # ── Literature ────────────────────────────────
        print("\n🔬 Literature")

        async def test_lit_validate():
            r = await c.post(
                "/api/v1/literature/search/validate-query",
                json={"query": "CRISPR cancer therapy"},
            )
            assert r.status_code == 200

        await test("Validate query", test_lit_validate())

        async def test_lit_search():
            r = await c.post(
                "/api/v1/literature/search",
                json={"query": "CRISPR", "max_results": 3},
            )
            assert r.status_code == 200
            assert isinstance(r.json(), list)

        await test("PubMed search", test_lit_search())

        # ── Pseudonymization ──────────────────────────
        print("\n🔒 Pseudonymization")

        async def test_pseudonymize():
            r = await c.post(
                "/api/v1/pseudonymize",
                json={"text": "Patient Max Mustermann, born 01.01.1980, LANR 123456789"},
            )
            assert r.status_code == 200
            data = r.json()
            assert "pseudonymized_text" in data

        await test("Pseudonymize text", test_pseudonymize())

        async def test_audit_log():
            r = await c.get("/api/v1/pseudonymize/audit-log")
            assert r.status_code == 200
            assert isinstance(r.json(), list)

        await test("Audit log", test_audit_log())

        # ── Phenopackets ──────────────────────────────
        print("\n👤 Phenopackets")

        async def test_create_phenopacket():
            r = await c.post(
                "/api/v1/phenopackets",
                json={
                    "pseudonym_id": "TEST-INT-001",
                    "phenotypes": [],
                    "diseases": [],
                    "genes_of_interest": [],
                },
            )
            assert r.status_code in (200, 201, 409)

        await test("Create phenopacket", test_create_phenopacket())

        async def test_list_phenopackets():
            r = await c.get("/api/v1/phenopackets")
            assert r.status_code == 200
            assert isinstance(r.json(), list)

        await test("List phenopackets", test_list_phenopackets())

        # ── DRS ───────────────────────────────────────
        print("\n🗄️  DRS")

        async def test_drs_service_info():
            r = await c.get("/ga4gh/drs/v1/service-info")
            assert r.status_code == 200

        await test("DRS service info", test_drs_service_info())

        async def test_drs_upload():
            content = b">Test_seq\nATCGATCGATCG\n"
            r = await c.post(
                "/ga4gh/drs/v1/objects",
                data={"name": "integration_test.fasta"},
                files={"file": ("integration_test.fasta", content, "text/plain")},
            )
            assert r.status_code in (200, 201)

        await test("DRS upload", test_drs_upload())

        async def test_drs_list():
            r = await c.get("/ga4gh/drs/v1/objects")
            assert r.status_code == 200

        await test("DRS list objects", test_drs_list())

        # ── Notebooks ─────────────────────────────────
        print("\n📓 Notebooks")

        nb_id = None

        async def test_create_notebook():
            nonlocal nb_id
            r = await c.post(
                "/api/v1/notebooks",
                json={
                    "title": "Integration Test Notebook",
                    "content": "# Test\n\nThis is a test.",
                    "tags": ["integration-test"],
                },
            )
            assert r.status_code in (200, 201), f"Got {r.status_code}: {r.text}"
            nb_id = r.json().get("id")

        await test("Create notebook", test_create_notebook())

        async def test_list_notebooks():
            r = await c.get("/api/v1/notebooks")
            assert r.status_code == 200
            data = r.json()
            assert "items" in data
            assert isinstance(data["items"], list)

        await test("List notebooks", test_list_notebooks())

        async def test_update_notebook():
            if not nb_id:
                return
            r = await c.put(
                f"/api/v1/notebooks/{nb_id}",
                json={"content": "# Updated\n\nUpdated content."},
            )
            assert r.status_code == 200

        await test("Update notebook", test_update_notebook())

        # ── WES ───────────────────────────────────────
        print("\n⚙️  WES")

        async def test_wes_service_info():
            r = await c.get("/ga4gh/wes/v1/service-info")
            assert r.status_code in (200, 404, 503)

        await test("WES service info", test_wes_service_info())

        async def test_wes_list_runs():
            r = await c.get("/ga4gh/wes/v1/runs")
            assert r.status_code in (200, 404, 503)

        await test("WES list runs", test_wes_list_runs())

        # ── FAIR Export ───────────────────────────────
        print("\n📦 FAIR Export")

        async def test_fair_preview():
            r = await c.post(
                "/api/v1/fair-export/preview",
                json={
                    "title": "Integration Test Dataset",
                    "description": "Test",
                    "authors": ["Test Author"],
                    "license": "CC-BY-4.0",
                    "include_papers": True,
                    "include_phenopackets": False,
                    "include_notebooks": False,
                },
            )
            assert r.status_code in (200, 404, 501)

        await test("FAIR preview", test_fair_preview())

        # ── Cleanup ───────────────────────────────────
        print("\n🧹 Cleanup")

        async def test_delete_notebook():
            if not nb_id:
                return
            r = await c.delete(f"/api/v1/notebooks/{nb_id}")
            assert r.status_code == 204

        await test("Delete notebook", test_delete_notebook())

        async def test_delete_paper():
            r = await c.delete("/api/v1/library/papers/99999999")
            assert r.status_code in (200, 204, 404)

        await test("Delete test paper", test_delete_paper())

        # ── Summary ───────────────────────────────────
        print("\n" + "─" * 50)
        passed = sum(1 for r in results if r[0] == PASS)
        failed = sum(1 for r in results if r[0] == FAIL)
        total = len(results)
        print(f"\n📊 Results: {passed}/{total} passed")
        if failed:
            print(f"\n{FAIL} Failed tests:")
            for r in results:
                if r[0] == FAIL:
                    print(f"   • {r[1]}: {r[2]}")
        print()
        return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    success = asyncio.run(run_all(args.base_url))
    sys.exit(0 if success else 1)
