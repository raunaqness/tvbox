from abc import ABC, abstractmethod
from typing import List
import asyncio
import httpx
import os
from app.models.search import SearchResult

class SearchStrategy(ABC):
    @abstractmethod
    async def search(self, query: str) -> List[SearchResult]:
        pass

class YTSStrategy(SearchStrategy):
    async def search(self, query: str) -> List[SearchResult]:
        url = "https://yts.mx/api/v2/list_movies.json"
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params={"query_term": query})
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "ok" and "movies" in data.get("data", {}):
                    movies = data["data"]["movies"]
                    if not movies:
                        return results
                        
                    for movie in movies:
                        title = movie.get("title_long", movie.get("title"))
                        for torrent in movie.get("torrents", []):
                            hash_ = torrent.get("hash")
                            if not hash_:
                                continue
                            
                            import urllib.parse
                            dn = urllib.parse.quote(title)
                            magnet = f"magnet:?xt=urn:btih:{hash_}&dn={dn}"
                            
                            results.append(
                                SearchResult(
                                    title=f"{title} [{torrent.get('quality')}]",
                                    magnet=magnet,
                                    seeders=torrent.get("seeds", 0),
                                    leechers=torrent.get("peers", 0),
                                    size_bytes=torrent.get("size_bytes", 0),
                                    resolution=torrent.get("quality", "Unknown"),
                                    source="YTS",
                                    info_hash=hash_
                                )
                            )
        except Exception as e:
            print(f"YTS Search Error: {repr(e)}")
            
        return results

class ProwlarrStrategy(SearchStrategy):
    def __init__(self):
        self.prowlarr_url = os.getenv("PROWLARR_URL", "http://localhost:9696").rstrip("/")
        self.api_key = os.getenv("PROWLARR_API_KEY", "")

    async def search(self, query: str) -> List[SearchResult]:
        if not self.api_key:
            print("Prowlarr API key not configured.")
            return []
            
        url = f"{self.prowlarr_url}/api/v1/search"
        results = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url, 
                    params={"query": query, "type": "search"},
                    headers={"X-Api-Key": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                
                for item in data:
                    magnet = item.get("magnetUrl") or item.get("downloadUrl")
                    if not magnet or not magnet.startswith("magnet:"):
                        continue
                        
                    results.append(
                        SearchResult(
                            title=item.get("title", "Unknown"),
                            magnet=magnet,
                            seeders=item.get("seeders", 0),
                            leechers=item.get("leechers", 0),
                            size_bytes=item.get("size", 0),
                            resolution="Unknown",
                            source=item.get("indexer", "Prowlarr"),
                            info_hash=item.get("infoHash")
                        )
                    )
        except Exception as e:
            print(f"Prowlarr Search Error: {e}")
            
        return results

class PirateBayStrategy(SearchStrategy):
    async def search(self, query: str) -> List[SearchResult]:
        url = "https://apibay.org/q.php"
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params={"q": query})
                response.raise_for_status()
                data = response.json()
                
                # apibay returns [{"id": "0", "name": "No results returned", ...}] if empty
                if not data or (len(data) == 1 and data[0].get("id") == "0"):
                    return results
                    
                for item in data:
                    hash_ = item.get("info_hash")
                    if not hash_:
                        continue
                        
                    title = item.get("name", "Unknown")
                    import urllib.parse
                    dn = urllib.parse.quote(title)
                    magnet = f"magnet:?xt=urn:btih:{hash_}&dn={dn}"
                    
                    results.append(
                        SearchResult(
                            title=title,
                            magnet=magnet,
                            seeders=int(item.get("seeders", 0)),
                            leechers=int(item.get("leechers", 0)),
                            size_bytes=int(item.get("size", 0)),
                            resolution="Unknown",
                            source="ThePirateBay",
                            info_hash=hash_
                        )
                    )
        except Exception as e:
            print(f"TPB Search Error: {repr(e)}")
            
        return results

class SearchAggregator:
    def __init__(self, strategies: List[SearchStrategy]):
        self.strategies = strategies

    async def aggregate_search(self, query: str) -> List[SearchResult]:
        tasks = [strategy.search(query) for strategy in self.strategies]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for result_list in results_lists:
            if isinstance(result_list, Exception):
                # Log exception
                continue
            all_results.extend(result_list)
        
        # Deduplicate by info_hash or magnet
        seen_magnets = set()
        deduped_results = []
        for res in all_results:
            # Filter out torrents with 0 seeders
            if res.seeders > 0 and res.magnet not in seen_magnets:
                seen_magnets.add(res.magnet)
                deduped_results.append(res)
                
        def get_sort_key(res: SearchResult) -> tuple:
            title_lower = res.title.lower()
            res_str = res.resolution.lower()
            
            score = 1
            if "2160p" in title_lower or "4k" in title_lower or "2160p" in res_str or "4k" in res_str:
                score = 4
            elif "1080p" in title_lower or "1080p" in res_str:
                score = 3
            elif "720p" in title_lower or "720p" in res_str:
                score = 2
                
            if res.seeders < 5:
                score -= 1.5
                
            return (score, res.seeders)

        # Rank by resolution descending, then seeders descending
        deduped_results.sort(key=get_sort_key, reverse=True)
        return deduped_results
