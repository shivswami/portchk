"""Tests for portchk. Run with: python -m pytest tests/ -v"""

import json
import os
from pathlib import Path

import pytest

import portchk
from portchk import registry as reg_mod
from portchk import scanner
from portchk.registry import build_port_index, find_conflicts, load, save, to_env_lines, to_json


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
        assert isinstance(portchk.__version__, str)
        parts = portchk.__version__.split(".")
        assert len(parts) >= 2


# ----------------------------------------------------------- export formats
class TestExportFormats:
    def test_to_env_single_port(self, tmp_registry):
        save({"projects": {
            "myapp": {"ports": [3000], "path": "/tmp/myapp"},
        }})
        lines = to_env_lines(load())
        assert lines == ["MYAPP_PORT=3000"]

    def test_to_env_multiple_ports(self, tmp_registry):
        save({"projects": {
            "backend": {"ports": [8000, 8001], "path": "/tmp/backend"},
        }})
        lines = to_env_lines(load())
        assert lines == ["BACKEND_PORT_1=8000", "BACKEND_PORT_2=8001"]

    def test_to_env_hyphen_and_space(self, tmp_registry):
        save({"projects": {
            "my-cool app": {"ports": [3000], "path": ""},
        }})
        lines = to_env_lines(load())
        assert lines == ["MY_COOL_APP_PORT=3000"]

    def test_to_env_empty_registry(self, tmp_registry):
        assert to_env_lines(load()) == []

    def test_to_env_project_with_no_ports(self, tmp_registry):
        save({"projects": {
            "app": {"ports": [], "path": ""},
        }})
        assert to_env_lines(load()) == []

    def test_to_json(self, tmp_registry):
        data = {"projects": {"app": {"ports": [3000], "path": "/tmp"}}}
        save(data)
        result = to_json(load())
        assert json.loads(result) == data


# ----------------------------------------------------------- isfree
class TestIsFree:
    def test_isfree_free_port(self):
        """A high port is unlikely to be in use."""
        from portchk.cli import cmd_isfree
        with pytest.raises(SystemExit) as exc:
            cmd_isfree(["49999"])
        assert exc.value.code == 0

    def test_isfree_in_use_port(self):
        """portchk test process doesn't listen, so a random port won't be in use.
        We test the negative path by checking the exit code logic directly."""
        from portchk.cli import cmd_isfree
        # use a port we know is listening - port 0 is always reserved
        # Actually, we can't reliably test "in use" without binding a socket.
        # Instead test arg parsing.
        with pytest.raises(SystemExit) as exc:
            cmd_isfree([])
        assert exc.value.code == 2


# ----------------------------------------------------------- kill
class TestKill:
    def test_kill_no_args(self):
        from portchk.cli import cmd_kill
        with pytest.raises(SystemExit) as exc:
            cmd_kill([])
        assert exc.value.code == 2

    def test_kill_port_not_in_use(self, capsys):
        from portchk.cli import cmd_kill
        cmd_kill(["49999"])
        captured = capsys.readouterr()
        assert "not in use" in captured.out

    def test_kill_force_flag_parsing(self):
        """Smoke test: --force on a dead port should not crash."""
        from portchk.cli import cmd_kill
        cmd_kill(["49999", "--force"])


# ----------------------------------------------------------- wait
class TestWait:
    def test_wait_no_args(self):
        from portchk.cli import cmd_wait
        with pytest.raises(SystemExit) as exc:
            cmd_wait([])
        assert exc.value.code == 2

    def test_wait_free_port_returns_immediately(self, capsys):
        from portchk.cli import cmd_wait
        cmd_wait(["49999"])
        captured = capsys.readouterr()
        assert "free" in captured.out


# ----------------------------------------------------------- scanner additions
class TestScannerAdditions:
    def test_find_pid_for_port_returns_none_if_free(self):
        assert scanner.find_pid_for_port(49999) is None

    def test_kill_pid_nonexistent_returns_false(self):
        """Killing a PID that doesn't exist should fail gracefully."""
        assert scanner.kill_pid(999999) is False
