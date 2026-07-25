"""Tests for portdocket. Run with: python -m pytest tests/ -v"""

import json
import os
from pathlib import Path

import pytest

import portdocket
from portdocket import registry as reg_mod
from portdocket import scanner
from portdocket.registry import build_port_index, find_conflicts, load, save


# ----------------------------------------------------------- fixtures
@pytest.fixture
def tmp_registry(monkeypatch, tmp_path):
    """Redirect the registry to a temp file for isolation."""
    reg_path = tmp_path / "registry.json"
    monkeypatch.setattr(reg_mod, "REGISTRY_PATH", reg_path)
    return reg_path


# ----------------------------------------------------------- registry
class TestRegistry:
    def test_load_empty(self, tmp_registry):
        reg = load()
        assert reg == {"projects": {}}

    def test_save_then_load(self, tmp_registry):
        data = {"projects": {"app": {"ports": [3000], "path": "/tmp/app"}}}
        save(data)
        loaded = load()
        assert loaded == data

    def test_save_creates_parent_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "a" / "b" / "registry.json"
        monkeypatch.setattr(reg_mod, "REGISTRY_PATH", nested)
        save({"projects": {}})
        assert nested.exists()

    def test_load_corrupt_json_returns_empty(self, tmp_registry):
        tmp_registry.write_text("not valid json {{{")
        reg = load()
        assert reg == {"projects": {}}

    def test_build_port_index(self, tmp_registry):
        save({"projects": {
            "app": {"ports": [3000, 8000], "path": ""},
            "db": {"ports": [5432], "path": ""},
        }})
        reg = load()
        idx = build_port_index(reg)
        assert idx[3000] == ["app"]
        assert idx[8000] == ["app"]
        assert idx[5432] == ["db"]

    def test_find_conflicts_clean(self, tmp_registry):
        save({"projects": {
            "app": {"ports": [3000], "path": ""},
            "db": {"ports": [5432], "path": ""},
        }})
        assert find_conflicts(load()) == []

    def test_find_conflicts_double_claim(self, tmp_registry):
        save({"projects": {
            "app": {"ports": [3000], "path": ""},
            "other": {"ports": [3000], "path": ""},
        }})
        conf = find_conflicts(load())
        assert len(conf) == 1
        assert conf[0][0] == 3000
        assert set(conf[0][1]) == {"app", "other"}


# ----------------------------------------------------------- scanner
class TestScanner:
    def test_parse_port_basic(self):
        assert scanner._parse_port("127.0.0.1:5432") == 5432

    def test_parse_port_with_listen_suffix(self):
        assert scanner._parse_port("*:3000 (LISTEN)") == 3000

    def test_parse_port_ipv6(self):
        assert scanner._parse_port("[::1]:3001 (LISTEN)") == 3001

    def test_parse_port_no_port(self):
        assert scanner._parse_port("no colon here") is None

    def test_parse_port_no_digits(self):
        assert scanner._parse_port("addr:") is None

    def test_listening_ports_returns_list(self):
        """Live call - should at least return a list of dicts."""
        ports = scanner.listening_ports()
        assert isinstance(ports, list)
        for entry in ports:
            assert set(entry.keys()) == {"port", "pid", "command", "proto", "addr"}

    def test_dedupe(self):
        results = [
            {"port": 3000, "pid": "1", "command": "a", "proto": "tcp", "addr": "*:3000"},
            {"port": 3000, "pid": "1", "command": "a", "proto": "tcp", "addr": "*:3000"},
            {"port": 8000, "pid": "2", "command": "b", "proto": "tcp", "addr": "*:8000"},
        ]
        assert len(scanner._dedupe(results)) == 2


# ----------------------------------------------------------- version
class TestVersion:
    def test_version_is_string(self):
        assert isinstance(portdocket.__version__, str)
        parts = portdocket.__version__.split(".")
        assert len(parts) >= 2
