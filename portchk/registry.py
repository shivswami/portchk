"""JSON-backed port registry.

Registry path: ~/.config/portchk/registry.json (per-machine, do not sync).
"""

import json
from pathlib import Path

REGISTRY_PATH = Path.home() / ".config" / "portchk" / "registry.json"


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


# --------------------------------------------------------------- export formats
def to_env_lines(reg):
    """Return list of 'NAME_PORT=N' lines for env/dotenv export."""
    lines = []
    for name in sorted(reg["projects"]):
        ports = reg["projects"][name].get("ports", [])
        if not ports:
            continue
        var = name.upper().replace("-", "_").replace(" ", "_")
        if len(ports) == 1:
            lines.append(f"{var}_PORT={ports[0]}")
        else:
            for i, p in enumerate(ports, 1):
                lines.append(f"{var}_PORT_{i}={p}")
    return lines


def to_json(reg):
    """Return compact JSON string of the registry."""
    return json.dumps(reg, indent=2)
