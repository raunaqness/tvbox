from pydantic import BaseModel
from typing import Optional

class SearchResult(BaseModel):
    title: str
    magnet: str
    seeders: int
    leechers: int
    size_bytes: int
    resolution: str
    source: str
    info_hash: Optional[str] = None
