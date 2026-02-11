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

config = configparser.ConfigParser()
if not Path(__file__).parent.parent.parent.joinpath('models.ini').exists():
    config['AGENTS'] = {
        'base_model': 'cerebras/llama3.3-70b',
        'coordinator_model': 'cerebras/llama3.3-70b',
        'image_recognition_model': 'llava',
        'audio_model': 'large-v3',
        'text_tool_model': 'cerebras/llama3.3-70b',
        'translation_model': 'cerebras/llama3.3-70b',
    }
    config['PATHS'] = {
        'json_path': './'
    }

    with open(Path(__file__).parent.parent.parent.joinpath('models.ini'), 'w') as configfile:
        config.write(configfile)
config.read('models.ini')

MODELS = { name: model for name, model in config['AGENTS'].items() }
PATHS = { name: path for name, path in config['PATHS'].items() }
