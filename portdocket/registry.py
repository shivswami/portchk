"""JSON-backed port registry.

Registry path: ~/.config/portdocket/registry.json (per-machine, do not sync).
"""

import json
from pathlib import Path

REGISTRY_PATH = Path.home() / ".config" / "portdocket" / "registry.json"


def load():
    if not REGISTRY_PATH.exists():
        return {"projects": {}}
    try:
        data = json.loads(REGISTRY_PATH.read_text())
        data.setdefault("projects", {})
        return data
    except (json.JSONDecodeError, ValueError):
        return {"projects": {}}


def save(data):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(data, indent=2) + "\n")


def build_port_index(reg):
    """port(int) -> list of project names claiming it."""
    idx = {}
    for name, info in reg["projects"].items():
        for p in info.get("ports", []):
            idx.setdefault(int(p), []).append(name)
    return idx


def find_conflicts(reg):
    """Return list of (port, [names]) for ports claimed by more than one project."""
    idx = build_port_index(reg)
    return [(port, names) for port, names in idx.items() if len(names) > 1]
