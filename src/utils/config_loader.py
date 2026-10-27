import json
import os


def load_config(file_path: str) -> dict:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    absolute_path = os.path.join(base_dir, file_path)

    with open(absolute_path, 'r') as f:
        return json.load(f)


def load_mcp_config() -> dict:
    return load_config('config/mcp_servers.json')


def load_llm_config() -> dict:
    return load_config('config/llm_config.json')
