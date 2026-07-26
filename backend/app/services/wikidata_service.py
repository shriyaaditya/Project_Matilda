from datetime import UTC, datetime
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.cache import WikidataCacheModel


class WikidataService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.search_url = "https://www.wikidata.org/w/api.php"
        self.entity_data_url = "https://www.wikidata.org/wiki/Special:EntityData"
        self.headers = {
            "User-Agent": "ProjectMatildaBot/1.0 (https://example.com; contact@example.edu) Python-httpx"
        }

    async def _get_from_cache(self, query_key: str) -> dict[str, Any] | None:
        stmt = select(WikidataCacheModel).where(WikidataCacheModel.query_key == query_key)
        result = await self.db.execute(stmt)
        cache_item = result.scalar_one_or_none()
        if cache_item:
            return cache_item.response_json
        return None

    async def _save_to_cache(self, query_key: str, data: dict[str, Any]) -> None:
        cache_item = WikidataCacheModel(
            query_key=query_key,
            response_json=data,
            updated_at=datetime.now(UTC),
        )
        await self.db.merge(cache_item)
        await self.db.commit()

    async def search_entities(self, name_query: str, limit: int = 5) -> list[dict[str, Any]]:
        clean_query = name_query.strip().lower()
        if not clean_query:
            return []

        cache_key = f"search:{clean_query}:{limit}"
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            return cast(list[dict[str, Any]], cached.get("candidates", []))

        params: dict[str, str | int] = {
            "action": "wbsearchentities",
            "search": name_query,
            "language": "en",
            "format": "json",
            "limit": limit,
            "type": "item",
        }

        candidates: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(self.search_url, params=params, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    search_results = data.get("search", [])
                    for item in search_results:
                        candidates.append({
                            "qid": item.get("id"),
                            "canonical_name": item.get("label", name_query),
                            "description": item.get("description", ""),
                            "aliases": item.get("aliases", []),
                            "birth_year": None,
                            "death_year": None,
                            "occupations": [],
                        })
            await self._save_to_cache(cache_key, {"candidates": candidates})
        except Exception:
            # Fallback on network timeout / offline mode: return empty list without failing pipeline
            return []

        return candidates

    async def get_entity_details(self, qid: str) -> dict[str, Any] | None:
        clean_qid = qid.strip().upper()
        if not clean_qid.startswith("Q"):
            return None

        cache_key = f"entity:{clean_qid}"
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            return cast(dict[str, Any] | None, cached.get("entity"))

        url = f"{self.entity_data_url}/{clean_qid}.json"

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(url, headers=self.headers)
                if res.status_code == 200:
                    data = res.json()
                    entity_dict = data.get("entities", {}).get(clean_qid, {})
                    label = entity_dict.get("labels", {}).get("en", {}).get("value", clean_qid)
                    desc = entity_dict.get("descriptions", {}).get("en", {}).get("value", "")
                    aliases_dict = entity_dict.get("aliases", {}).get("en", [])
                    aliases_list = [a.get("value") for a in aliases_dict if a.get("value")]

                    entity_result = {
                        "qid": clean_qid,
                        "canonical_name": label,
                        "description": desc,
                        "aliases": aliases_list,
                        "birth_year": None,
                        "death_year": None,
                        "occupations": [],
                    }
                    await self._save_to_cache(cache_key, {"entity": entity_result})
                    return entity_result
        except Exception:
            return None

        return None
