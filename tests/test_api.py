import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app

client = TestClient(app)

@patch('app.routers.api.tmdb_client.search', new_callable=AsyncMock)
def test_search_tmdb(mock_search):
    mock_search.return_value = [{"title": "Inception"}]
    
    response = client.get("/api/search?q=Inception")
    assert response.status_code == 200
    assert response.json() == [{"title": "Inception"}]

@patch('app.routers.api.search_aggregator.aggregate_search', new_callable=AsyncMock)
@patch('app.routers.api.download_manager.add_magnet')
def test_fetch_torrent(mock_add_magnet, mock_aggregate):
    mock_result = MagicMock()
    mock_result.title = "Inception 1080p"
    mock_result.magnet = "magnet:?"
    mock_result.model_dump.return_value = {"title": "Inception 1080p"}
    
    mock_aggregate.return_value = [mock_result]
    mock_add_magnet.return_value = "1234abcd"
    
    response = client.post("/api/fetch", json={"query": "Inception", "year": "2010"})
    
    assert response.status_code == 200
    assert response.json()["task_id"] == "task_1234abcd"
    assert mock_add_magnet.called
