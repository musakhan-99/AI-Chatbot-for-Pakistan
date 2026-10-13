from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import httpx


@dataclass
class WikiPage:
    title: str
    url: str
    extract: str
    language: str


LANGUAGE_WIKIS = {
    "en": "en",
    "ur": "ur",
    "ps": "ps",
    "roman-ur": "en",
    "auto": "en",
}


class WikipediaRetriever:
    def __init__(self, results: int = 3, chars_per_page: int = 3200):
        self.results = results
        self.chars_per_page = chars_per_page
        self.headers = {
            "User-Agent": "PakistanAI-MVP/1.0 (educational Pakistan knowledge assistant)"
        }

    async def search(self, query: str, language: str = "auto") -> list[WikiPage]:
        primary = LANGUAGE_WIKIS.get(language, "en")
        languages = [primary]
        if primary != "en":
            languages.append("en")

        pages: list[WikiPage] = []
        seen: set[str] = set()
        for lang in languages:
            found = await self._search_wiki(query, lang)
            for page in found:
                key = f"{page.language}:{page.title.casefold()}"
                if key not in seen:
                    seen.add(key)
                    pages.append(page)
                if len(pages) >= self.results:
                    return pages
        return pages

    async def _search_wiki(self, query: str, lang: str) -> list[WikiPage]:
        endpoint = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": str(self.results),
            "gsrnamespace": "0",
            "prop": "extracts|info",
            "explaintext": "1",
            "exchars": str(self.chars_per_page),
            "inprop": "url",
        }

        try:
            async with httpx.AsyncClient(timeout=12.0, headers=self.headers) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        raw_pages = data.get("query", {}).get("pages", [])
        output: list[WikiPage] = []
        for item in raw_pages:
            title = item.get("title")
            extract = (item.get("extract") or "").strip()
            if not title or not extract:
                continue
            url = item.get("fullurl") or f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
            output.append(WikiPage(title=title, url=url, extract=extract, language=lang))

        return output
