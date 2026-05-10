import pytest
from unittest.mock import patch, MagicMock
from app.services.upload import UploadManager
import os

@patch('app.services.upload.os.path.exists')
@patch('app.services.upload.subprocess.run')
def test_upload_file_success(mock_run, mock_exists):
    mock_exists.return_value = True
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_run.return_value = mock_result
    
    manager = UploadManager()
    manager.rclone_remote = "gdrive:/Media"
    
    result = manager.upload_file("./downloads/movie.mkv")
    
    assert result is True
    mock_run.assert_called_once_with([
        "rclone", "move", "./downloads/movie.mkv", "gdrive:/Media",
        "--delete-empty-src-dirs", "--ignore-existing"
    ], capture_output=True, text=True, check=True)

@patch('app.services.upload.os.path.exists')
def test_upload_file_not_found(mock_exists):
    mock_exists.return_value = False
    
    manager = UploadManager()
    result = manager.upload_file("./downloads/missing.mkv")
    
    assert result is False
