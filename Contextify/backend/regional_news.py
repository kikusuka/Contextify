"""Mock-first regional news lookup for the Contextify hackathon.

This module intentionally makes no network requests. The default provider returns
clearly labeled fixture data; a future SerpApi adapter can implement the same
``search`` interface without changing the response contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


MAX_RESULTS_PER_REGION = 5
MOCK_LABEL = "MOCK DATA — NOT REAL EVIDENCE"


@dataclass(frozen=True)
class Region:
    name: str
    gl: str


REGIONS = (
    Region("India", "in"),
    Region("USA", "us"),
    Region("UK", "gb"),
)


class SearchProvider(Protocol):
    """Provider boundary. Implementations return SerpApi-like organic results."""

    def search(self, query: str, *, gl: str) -> list[dict[str, Any]]: ...


class MockSerpApi:
    """Offline SerpApi stand-in with obviously synthetic, non-citable results."""

    def search(self, query: str, *, gl: str) -> list[dict[str, Any]]:
        region = next((r.name for r in REGIONS if r.gl == gl), "Unknown region")
        # Deliberately generic fixture content: it exercises the integration
        # contract without asserting anything about the claim being researched.
        return [
            {
                "title": f"[MOCK] Sample result {i} for {region}",
                "link": f"https://{gl}.mock-search.example/result-{i}",
                "source": f"Mock source {i}",
                "date": "MOCK DATE",
                "snippet": (
                    f"Synthetic fixture for query {query!r}; this is not a news "
                    "article and must not be treated as evidence."
                ),
            }
            for i in range(1, MAX_RESULTS_PER_REGION + 1)
        ]


def _normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Map common SerpApi keys and fixture keys onto the public item schema."""
    return {
        "title": result.get("title") or "",
        "link": result.get("link") or result.get("url") or "",
        "source_name": result.get("source") or result.get("source_name") or "",
        "date": result.get("date") or result.get("published_date") or "",
        "snippet": result.get("snippet") or result.get("snippet_highlighted_words") or "",
        "is_mock": True,
    }


def get_regional_news(
    claim: str,
    *,
    provider: SearchProvider | None = None,
) -> dict[str, Any]:
    """Return offline mock news results grouped by India, USA, and UK.

    Each region is searched independently, so a provider failure for one region
    does not prevent results from the others. Empty/whitespace claims skip all
    searches. Every returned item is explicitly marked as mock data.
    """
    results: dict[str, list[dict[str, Any]]] = {r.name: [] for r in REGIONS}
    errors: dict[str, str] = {}
    cleaned_claim = claim.strip() if isinstance(claim, str) else ""

    if cleaned_claim:
        search_provider = provider if provider is not None else MockSerpApi()
        for region in REGIONS:
            query = f'"{cleaned_claim}" news'
            try:
                raw_results = search_provider.search(query, gl=region.gl)
                results[region.name] = [
                    _normalize_result(item)
                    for item in (raw_results or [])[:MAX_RESULTS_PER_REGION]
                ]
            except Exception as exc:  # isolate a regional provider failure
                errors[region.name] = f"{type(exc).__name__}: {exc}"

    return {
        "data_mode": MOCK_LABEL,
        "is_mock": True,
        "regions": results,
        "errors": errors,
    }
