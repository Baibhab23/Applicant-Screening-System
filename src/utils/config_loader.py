import json
import os

def load_config(file_path: str) -> dict:
    # Get absolute path relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    absolute_path = os.path.join(base_dir, file_path)
    
    with open(absolute_path, 'r') as file:
        config = json.load(file)
    
    return config

def load_mcp_config() -> dict:
    return load_config('config/mcp_servers.json')

def load_aicore_config() -> dict:
    return load_config('config/aicore_config.json')