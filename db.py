import os
import json
import pymysql


CONFIG_FILE = "config.json"


def load_config() -> dict:
    """
    Reads the configuration file. Creates a default config.json if not present.
    """
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "OLLAMA_URL": "http://localhost:11434/api/generate",
            "DB_CONFIG": {
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "Proc@12345",
                "database": "collab"
            }
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config_data: dict) -> None:
    """
    Saves the dictionary configuration back to config.json.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)


def get_db_connection() -> pymysql.Connection:
    """
    Reads current DB_CONFIG from config.json and opens a connection.
    """
    config = load_config()
    db_params = config.get("DB_CONFIG", {}).copy()
    db_params["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**db_params)
