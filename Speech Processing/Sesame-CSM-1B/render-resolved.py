import json

path = "Sesame_CSM_1B_TTS.ipynb"

with open(path, "r", encoding="utf-8") as f:
    nb = json.load(f)

widgets = nb.get("metadata", {}).get("widgets", {})
key = "application/vnd.jupyter.widget-state+json"

if key in widgets and "state" not in widgets[key]:
    original = widgets[key]
    widgets[key] = {
        "version_major": 2,
        "version_minor": 0,
        "state": original,
    }

with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Fixed widget metadata for:", path)
