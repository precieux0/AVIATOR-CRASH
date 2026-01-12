import json
from pathlib import Path

TRANSLATIONS = {}

def load_translations():
    base = Path(__file__).parent / "translations"
    for p in base.glob("*.json"):
        with p.open("r", encoding="utf-8") as f:
            TRANSLATIONS[p.stem] = json.load(f)

def t(lang: str, key: str, **kwargs) -> str:
    if lang not in TRANSLATIONS:
        lang = "en"
    template = TRANSLATIONS.get(lang, {}).get(key, key)
    return template.format(**kwargs)

# load at import
load_translations()
