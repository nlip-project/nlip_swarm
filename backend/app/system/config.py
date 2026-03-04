import configparser
from pathlib import Path

MOUNT_URLS = {
    "coord": "http://0.0.0.0:8024/",
    "basic": "mem://basic/",
    "translate": "mem://translate/",
    "text": "mem://text/",
    "sound": "mem://sound/",
    "image": "mem://image/",
}

COORDINATOR_URL = MOUNT_URLS["coord"]

# All non-coordinator endpoints derived from MOUNT_URLS
DEFAULT_AGENT_ENDPOINTS = [
    url.rstrip("/")
    for name, url in MOUNT_URLS.items()
    if name != "coord"
]

ROOT_DIR = Path(__file__).resolve().parents[2]
MODELS_INI_PATH = ROOT_DIR / "models.ini"

DEFAULT_AGENT_MODELS = {
    'ollama_model': 'cerebras/llama3.3-70b',
    'base_model': 'cerebras/llama3.3-70b',
    'coordinator_model': 'cerebras/llama3.3-70b',
    'image_recognition_model': 'llava',
    'audio_model': 'large-v3',
    'text_tool_model': 'cerebras/llama3.3-70b',
    'translation_model': 'cerebras/llama3.3-70b',
}

DEFAULT_PATHS = {
    'json_path': './'
}

DEFAULT_URLS = {
    'ollama_url': None,
    'image_url': None,
    'audio_url': None,
    'translation_url': None,
}

config = configparser.ConfigParser()
if not MODELS_INI_PATH.exists():
    config['AGENTS'] = DEFAULT_AGENT_MODELS
    config['PATHS'] = DEFAULT_PATHS
    with open(MODELS_INI_PATH, 'w') as configfile:
        config.write(configfile)
config.read(MODELS_INI_PATH)
if 'AGENTS' not in config:
    config['AGENTS'] = DEFAULT_AGENT_MODELS
if 'PATHS' not in config:
    config['PATHS'] = DEFAULT_PATHS
if 'URLS' not in config:
    config['URLS'] = DEFAULT_URLS
MODELS = { name: model for name, model in config['AGENTS'].items() }
PATHS = { name: path for name, path in config['PATHS'].items() }
URLS = { name: url for name, url in config['URLS'].items() }
