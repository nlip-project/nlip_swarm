#!/usr/bin/env python3
"""Read models.ini and output environment variables for shell sourcing."""
import configparser
from pathlib import Path

# Find models.ini relative to project root
SCRIPT_DIR = Path(__file__).resolve().parent
MODELS_INI_PATH = SCRIPT_DIR.parent / "backend" / "models.ini"

if not MODELS_INI_PATH.exists():
    print(f"# Warning: {MODELS_INI_PATH} not found")
    exit(1)

config = configparser.ConfigParser()
config.read(MODELS_INI_PATH)

# Map models.ini keys to environment variable names
KEY_MAPPING = {
    # 'base_model': 'LLM_MODEL',
    # 'translation_model': 'TRANSLATION_MODEL',
}

if 'AGENTS' in config:
    for key in config['AGENTS']:
        env_var = key.upper()
        KEY_MAPPING[key] = env_var

for ini_key, env_var in KEY_MAPPING.items():
    if ini_key in config['AGENTS']:
        value = config['AGENTS'][ini_key]
        print(f"{env_var}={value}")
