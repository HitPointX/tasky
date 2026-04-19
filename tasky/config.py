import json
import os

_CONFIG_PATH = os.path.expanduser('~/.config/tasky/settings.json')


def load():
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data):
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    existing = load()
    existing.update(data)
    with open(_CONFIG_PATH, 'w') as f:
        json.dump(existing, f, indent=2)


def get(key, default=None):
    return load().get(key, default)
