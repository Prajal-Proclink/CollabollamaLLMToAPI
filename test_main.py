import os
import json
import pytest
import main
from main import load_config, save_config

def test_load_save_config(tmp_path):
    # Use a temporary config file path
    temp_config = tmp_path / "test_config.json"
    
    # We patch the CONFIG_FILE in main module
    original_config_file = main.CONFIG_FILE
    main.CONFIG_FILE = str(temp_config)
    
    try:
        # Test default config generation when file doesn't exist
        config = load_config()
        assert "OLLAMA_URL" in config
        assert config["DB_CONFIG"]["host"] == "127.0.0.1"
        
        # Test saving config
        config["OLLAMA_URL"] = "http://test-url"
        save_config(config)
        
        # Test loading updated config
        new_config = load_config()
        assert new_config["OLLAMA_URL"] == "http://test-url"
    finally:
        # Restore CONFIG_FILE
        main.CONFIG_FILE = original_config_file

def test_get_prompt_status_success():
    from unittest.mock import MagicMock, patch
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {
        "processState": 2,
        "prompsResponce": "Response generated"
    }
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    with patch("main.get_db_connection", return_value=mock_conn):
        res = main.get_prompt_status(idPrompt=101)
        assert res["status"] == "success"
        assert res["data"]["processState"] == 2
        assert res["data"]["prompsResponce"] == "Response generated"

def test_get_prompt_status_not_found():
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    with patch("main.get_db_connection", return_value=mock_conn):
        with pytest.raises(HTTPException) as exc_info:
            main.get_prompt_status(idPrompt=999)
        assert exc_info.value.status_code == 404
        assert "Prompt ID 999 not found" in exc_info.value.detail

def test_get_home():
    response = main.get_home()
    assert response.status_code == 200
    assert "text/html" in response.media_type
    assert b"CollabOllama" in response.body

def test_get_chat_history():
    from unittest.mock import MagicMock, patch
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # First fetchone is COUNT(*), fetchall is records
    mock_cursor.fetchone.return_value = {"total": 25}
    mock_cursor.fetchall.return_value = [
        {"idPrompt": 10, "prompts": "p10", "processState": 2, "promptdate": "2026-07-02T10:00:00", "prompsResponce": "r10", "IsDeleted": 0},
        {"idPrompt": 9, "prompts": "p9", "processState": 2, "promptdate": "2026-07-02T09:50:00", "prompsResponce": "r9", "IsDeleted": 0}
    ]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    with patch("main.get_db_connection", return_value=mock_conn):
        res = main.get_chat_history(page=2, limit=10)
        assert res["status"] == "success"
        assert res["total"] == 25
        assert res["page"] == 2
        assert res["limit"] == 10
        assert len(res["data"]) == 2
        assert res["data"][0]["idPrompt"] == 10



