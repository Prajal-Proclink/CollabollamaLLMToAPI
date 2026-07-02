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
