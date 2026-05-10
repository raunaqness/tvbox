import httpx
import os
from typing import List, Dict, Any

class TMDBClient:
    def __init__(self):
        self.api_key = os.getenv("TMDB_API_KEY", "")
        self.base_url = "https://api.themoviedb.org/3"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        if not self.api_key:
            print("TMDB API key not configured.")
            return []
            
        url = f"{self.base_url}/search/multi"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    params={"api_key": self.api_key, "query": query, "include_adult": "false"}
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    # We only care about movies and tv shows
                    if item.get("media_type") not in ["movie", "tv"]:
                        continue
                        
                    # Format standard response
                    title = item.get("title") or item.get("name")
                    release_date = item.get("release_date") or item.get("first_air_date", "")
                    year = release_date.split("-")[0] if release_date else ""
                    
                    results.append({
                        "id": item.get("id"),
                        "title": title,
                        "year": year,
                        "media_type": item.get("media_type"),
                        "poster_path": item.get("poster_path"),
                        "overview": item.get("overview")
                    })
                    
                return results
        except Exception as e:
            print(f"TMDB Search Error: {e}")
            return []
