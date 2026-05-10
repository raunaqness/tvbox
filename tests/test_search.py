import pytest
from typing import List
from app.models.search import SearchResult
from app.services.search import SearchStrategy, SearchAggregator

class MockStrategy1(SearchStrategy):
    async def search(self, query: str) -> List[SearchResult]:
        return [
            SearchResult(title="Movie 1", magnet="magnet:?xt=urn:btih:1", seeders=10, leechers=2, size_bytes=1000, resolution="1080p", source="Mock1"),
            SearchResult(title="Movie 2", magnet="magnet:?xt=urn:btih:2", seeders=50, leechers=5, size_bytes=2000, resolution="1080p", source="Mock1"),
        ]

class MockStrategy2(SearchStrategy):
    async def search(self, query: str) -> List[SearchResult]:
        return [
            # Duplicate magnet but more seeders, should deduplicate but keep one. The current logic just keeps the first seen magnet.
            # Let's adjust mock so it's a real duplicate scenario.
            SearchResult(title="Movie 1 (Mock2)", magnet="magnet:?xt=urn:btih:1", seeders=100, leechers=20, size_bytes=1000, resolution="1080p", source="Mock2"),
            SearchResult(title="Movie 3", magnet="magnet:?xt=urn:btih:3", seeders=30, leechers=3, size_bytes=1500, resolution="1080p", source="Mock2"),
        ]

class MockFailingStrategy(SearchStrategy):
    async def search(self, query: str) -> List[SearchResult]:
        raise ValueError("API Offline")

@pytest.mark.asyncio
async def test_aggregator():
    aggregator = SearchAggregator([MockStrategy1(), MockStrategy2(), MockFailingStrategy()])
    results = await aggregator.aggregate_search("Movie")
    
    # Expected: 3 unique magnets (1, 2, 3)
    assert len(results) == 3
    
    # Magnet 1 should be present, Magnet 2, Magnet 3
    magnets = [r.magnet for r in results]
    assert "magnet:?xt=urn:btih:1" in magnets
    assert "magnet:?xt=urn:btih:2" in magnets
    assert "magnet:?xt=urn:btih:3" in magnets
    
    # Rank check (descending seeders)
    assert results[0].seeders >= results[1].seeders
    assert results[1].seeders >= results[2].seeders

from unittest.mock import patch, AsyncMock, MagicMock
from app.services.search import YTSStrategy

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_yts_strategy(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "ok",
        "data": {
            "movies": [
                {
                    "title": "Inception",
                    "title_long": "Inception (2010)",
                    "torrents": [
                        {
                            "hash": "12345ABCDE",
                            "quality": "1080p",
                            "seeds": 150,
                            "peers": 20,
                            "size_bytes": 2000000000
                        }
                    ]
                }
            ]
        }
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    strategy = YTSStrategy()
    results = await strategy.search("Inception")
    
    assert len(results) == 1
    assert results[0].title == "Inception (2010) [1080p]"
    assert results[0].info_hash == "12345ABCDE"
    assert results[0].seeders == 150
    assert "magnet:?xt=urn:btih:12345ABCDE" in results[0].magnet

from app.services.search import ProwlarrStrategy
import os

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_prowlarr_strategy(mock_get):
    os.environ["PROWLARR_API_KEY"] = "fake_key"
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "title": "Inception 2010 1080p",
            "magnetUrl": "magnet:?xt=urn:btih:ABC123XYZ",
            "seeders": 300,
            "leechers": 50,
            "size": 5000000000,
            "indexer": "1337x",
            "infoHash": "ABC123XYZ"
        }
    ]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    strategy = ProwlarrStrategy()
    results = await strategy.search("Inception")
    
    assert len(results) == 1
    assert results[0].title == "Inception 2010 1080p"
    assert results[0].info_hash == "ABC123XYZ"
    assert results[0].seeders == 300
    assert results[0].source == "1337x"
