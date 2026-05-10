import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.tmdb import TMDBClient
import os

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get', new_callable=AsyncMock)
async def test_tmdb_search(mock_get):
    os.environ["TMDB_API_KEY"] = "fake_tmdb_key"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "media_type": "movie",
                "id": 27205,
                "title": "Inception",
                "release_date": "2010-07-15",
                "poster_path": "/poster.jpg",
                "overview": "A thief who steals corporate secrets..."
            },
            {
                "media_type": "person",
                "id": 123,
                "name": "Christopher Nolan"
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    client = TMDBClient()
    results = await client.search("Inception")
    
    # Should ignore the person result
    assert len(results) == 1
    assert results[0]["title"] == "Inception"
    assert results[0]["year"] == "2010"
    assert results[0]["media_type"] == "movie"
