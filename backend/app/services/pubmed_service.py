"""PubMed search and fetch via NCBI E-utilities (esearch + efetch)."""

import asyncio
import logging
import re
import time
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

import httpx

from app.schemas.pubmed import PubMedArticle

logger = logging.getLogger(__name__)

NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUESTS_PER_SECOND = 3
MIN_INTERVAL = 1.0 / REQUESTS_PER_SECOND


def _strip_ns(tag: str) -> str:
    """Remove XML namespace from tag name."""
    return re.sub(r"^\{[^}]+\}", "", tag) if "}" in tag else tag


def _find_text(el: Element | None, default: str = "") -> str:
    if el is None:
        return default
    return (el.text or "").strip() + "".join(
        (child.tail or "").strip() for child in el
    ).strip() or default


def _first(el: Element | None, tag: str) -> Element | None:
    """First descendant with local tag name (namespace-agnostic, C-level search)."""
    if el is None:
        return None
    return el.find(f".//{{*}}{tag}")


def _parse_article(article_elem: Element) -> PubMedArticle:
    """Build PubMedArticle from one <PubmedArticle> XML element."""
    pmid_el = _first(article_elem, "PMID")
    pmid = _find_text(pmid_el)

    medline = _first(article_elem, "MedlineCitation")
    article = _first(medline, "Article") if medline is not None else None

    title = _find_text(_first(article, "ArticleTitle")) if article is not None else ""

    abstract_parts: list[str] = []
    if article is not None:
        abstract_el = _first(article, "Abstract")
        if abstract_el is not None:
            for abst in abstract_el:
                if _strip_ns(abst.tag) == "AbstractText":
                    abstract_parts.append(_find_text(abst))

    authors: list[str] = []
    if article is not None:
        author_list = _first(article, "AuthorList")
        if author_list is not None:
            for author in author_list:
                if _strip_ns(author.tag) != "Author":
                    continue
                last = _find_text(_first(author, "LastName"))
                fore = _find_text(_first(author, "ForeName"))
                init = _find_text(_first(author, "Initials"))
                if fore:
                    name = f"{last} {fore}".strip()
                elif init:
                    name = f"{last} {init}".strip()
                else:
                    name = last
                if name:
                    authors.append(name)

    journal = ""
    year: str | None = None
    if article is not None:
        journal_el = _first(article, "Journal")
        if journal_el is not None:
            journal = _find_text(_first(journal_el, "Title")) or _find_text(
                _first(journal_el, "ISOAbbreviation")
            )
            year_el = _first(journal_el, "Year")
            year = _find_text(year_el) or None

    doi: str | None = None
    if article is not None:
        eloc = _first(article, "ELocationID")
        if eloc is not None and (eloc.get("EIdType") or "").lower() == "doi":
            doi = _find_text(eloc) or None
    if not doi:
        article_id_list = _first(article_elem, "ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list:
                if _strip_ns(aid.tag) == "ArticleId" and (aid.get("IdType") or "").lower() == "doi":
                    doi = _find_text(aid) or None
                    break

    keywords: list[str] = []
    kw_list = _first(medline, "KeywordList") if medline is not None else None
    if kw_list is not None:
        for kw in kw_list:
            if _strip_ns(kw.tag) == "Keyword":
                text_kw = _find_text(kw)
                if text_kw:
                    keywords.append(text_kw)

    if not year and article is not None:
        pub_date = _first(article, "PubDate")
        if pub_date is None:
            pub_date = _first(article, "ArticleDate")
        year = _find_text(_first(pub_date, "Year")) or None

    year_int: int | None = None
    if year and str(year).strip().isdigit():
        year_int = int(str(year).strip())
    return PubMedArticle(
        pmid=pmid,
        title=title,
        abstract=" ".join(abstract_parts).strip(),
        authors=authors,
        journal=journal,
        year=year_int,
        doi=doi,
        keywords=keywords,
    )


class RateLimiter:
    """Enforces at most REQUESTS_PER_SECOND requests (NCBI limit)."""

    def __init__(self) -> None:
        self._times: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            wait = 0.0
            async with self._lock:
                now = time.monotonic()
                self._times = [t for t in self._times if now - t < 1.0]
                if len(self._times) >= REQUESTS_PER_SECOND:
                    wait = 1.0 - (now - self._times[0])
                    if wait <= 0:
                        self._times = self._times[1:]
                        self._times.append(now)
                        return
                else:
                    self._times.append(now)
                    return
            await asyncio.sleep(wait)


class PubMedServiceError(Exception):
    """Raised when NCBI E-utilities request or parsing fails."""

    pass


class PubMedService:
    """Async PubMed search and fetch using NCBI E-utilities with rate limiting."""

    def __init__(
        self,
        *,
        base_url: str = NCBI_EUTILS_BASE,
        client: httpx.AsyncClient | None = None,
        rate_limiter: RateLimiter | None = None,
        tool: str = "BioResearchAssistant",
        email: str | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._own_client = client is None
        self._limiter = rate_limiter or RateLimiter()
        self._params_common: dict[str, str] = {"tool": tool}
        if email:
            self._params_common["email"] = email

    async def close(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def __aenter__(self) -> "PubMedService":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def _esearch_ids(self, query: str, max_results: int) -> list[str]:
        await self._limiter.acquire()
        params: dict[str, str] = {
            **self._params_common,
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
        }
        try:
            resp = await self._client.get(
                f"{self._base}/esearch.fcgi",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("NCBI esearch HTTP error: %s", e)
            raise PubMedServiceError(f"NCBI esearch error: {e}") from e
        except (httpx.RequestError, ValueError) as e:
            logger.warning("NCBI esearch request/parse error: %s", e)
            raise PubMedServiceError(f"NCBI esearch failed: {e}") from e

        result = data.get("esearchresult") or data
        id_list = result.get("idlist") or []
        return list(id_list)

    async def _efetch_xml(self, pmids: list[str]) -> str:
        if not pmids:
            return '<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>'
        await self._limiter.acquire()
        params: dict[str, str] = {
            **self._params_common,
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }
        try:
            resp = await self._client.get(
                f"{self._base}/efetch.fcgi",
                params=params,
            )
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPStatusError as e:
            logger.warning("NCBI efetch HTTP error: %s", e)
            raise PubMedServiceError(f"NCBI efetch error: {e}") from e
        except httpx.RequestError as e:
            logger.warning("NCBI efetch request error: %s", e)
            raise PubMedServiceError(f"NCBI efetch failed: {e}") from e

    def _parse_articles_xml(self, xml_text: str) -> list[PubMedArticle]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.warning("PubMed XML parse error: %s", e)
            raise PubMedServiceError("Invalid PubMed XML response") from e
        articles: list[PubMedArticle] = []
        for child in root:
            if _strip_ns(child.tag) == "PubmedArticle":
                articles.append(_parse_article(child))
        return articles

    async def search_pubmed(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[PubMedArticle]:
        """Search PubMed and return article metadata.

        Uses esearch to get PMIDs then efetch to retrieve full records.
        Respects NCBI rate limit (max 3 requests/second).

        Args:
            query: Search term (e.g. "cancer immunotherapy").
            max_results: Maximum number of articles to return (default 20).

        Returns:
            List of PubMedArticle with pmid, title, abstract, authors, journal, year, doi, keywords.

        Raises:
            PubMedServiceError: On API or parsing errors.
        """
        if max_results <= 0:
            return []
        query = query.strip()
        if not query:
            return []
        ids = await self._esearch_ids(query, max_results)
        if not ids:
            return []
        xml_text = await self._efetch_xml(ids)
        return self._parse_articles_xml(xml_text)

    async def fetch_article(self, pmid: str) -> PubMedArticle:
        """Fetch full metadata for a single PMID.

        Args:
            pmid: PubMed ID (e.g. "41714870").

        Returns:
            PubMedArticle with all available fields.

        Raises:
            PubMedServiceError: On API or parsing errors.
        """
        pmid = str(pmid).strip()
        if not pmid:
            raise PubMedServiceError("Empty PMID")
        xml_text = await self._efetch_xml([pmid])
        articles = self._parse_articles_xml(xml_text)
        if not articles:
            raise PubMedServiceError(f"No article found for PMID {pmid}")
        return articles[0]
