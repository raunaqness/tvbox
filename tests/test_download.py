import pytest
from unittest.mock import patch, MagicMock
from app.services.download import DownloadManager

@pytest.fixture
def mock_aria2p_api():
    with patch('app.services.download.aria2p.API') as mock_api:
        yield mock_api

def test_add_magnet(mock_aria2p_api):
    # Setup mock
    mock_instance = mock_aria2p_api.return_value
    mock_download = MagicMock()
    mock_download.gid = "1234abcd"
    mock_instance.add_magnet.return_value = mock_download
    
    manager = DownloadManager()
    gid = manager.add_magnet("magnet:?xt=urn:btih:fake")
    
    assert gid == "1234abcd"
    mock_instance.add_magnet.assert_called_once_with("magnet:?xt=urn:btih:fake")

def test_get_progress(mock_aria2p_api):
    # Setup mock
    mock_instance = mock_aria2p_api.return_value
    mock_download = MagicMock()
    mock_download.gid = "1234abcd"
    mock_download.name = "Inception"
    mock_download.status = "active"
    mock_download.progress_string.return_value = "50.00%"
    mock_download.download_speed_string.return_value = "1.2 MiB/s"
    mock_download.is_complete = False
    mock_instance.get_download.return_value = mock_download
    
    manager = DownloadManager()
    progress = manager.get_progress("1234abcd")
    
    assert progress is not None
    assert progress["gid"] == "1234abcd"
    assert progress["status"] == "active"
    assert progress["progress_string"] == "50.00%"
    assert progress["is_complete"] is False

def test_remove_download(mock_aria2p_api):
    mock_instance = mock_aria2p_api.return_value
    mock_download = MagicMock()
    mock_instance.get_download.return_value = mock_download
    
    manager = DownloadManager()
    result = manager.remove_download("1234abcd")
    
    assert result is True
    mock_instance.remove.assert_called_once()
