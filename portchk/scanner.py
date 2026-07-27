"""Cross-platform detection of listening TCP ports and process metadata.

Unix (macOS/Linux): uses ``lsof``.
Windows: uses ``netstat -ano`` + ``tasklist``.

No third-party dependencies. Read-only: nothing here changes system state.
"""

import csv
import platform
import subprocess

IS_WINDOWS = platform.system() == "Windows"


def _run(cmd, timeout=15):
    """Run a command, return stdout string. Empty string on failure."""
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _dedupe(results):
    seen = set()
    uniq = []
    for r in results:
        key = (r["port"], r["pid"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq


def _parse_port(text):
    """Extract the integer port from 'addr:PORT' or 'addr:PORT (LISTEN)'."""
    if ":" not in text:
        return None
    tail = text.rsplit(":", 1)[-1]
    digits = "".join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else None


# ----------------------------------------------------------------------- unix
def listening_ports_unix():
    out = _run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
    results = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 9:
            continue
        command = parts[0].replace("\\x20", " ")
        pid = parts[1]
        name_field = " ".join(parts[8:])
        port = _parse_port(name_field)
        if port is None:
            continue
        proto = parts[4] if len(parts) > 4 else "?"
        addr = name_field.split()[0] if name_field else ""
        results.append(
            {"port": port, "pid": pid, "command": command, "proto": proto, "addr": addr}
        )
    return _dedupe(results)


# ------------------------------------------------------------------- windows
def _tasklist_pid_names():
    out = _run(["tasklist", "/FO", "CSV", "/NH"])
    pid_names = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            fields = next(csv.reader([line]))
            if len(fields) >= 2:
                pid_names[fields[1]] = fields[0]
        except (StopIteration, ValueError):
            continue
    return pid_names


def listening_ports_windows():
    pid_names = _tasklist_pid_names()
    out = _run(["netstat", "-ano", "-p", "tcp"])
    results = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "LISTENING" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        proto, local_addr, _foreign, _state, pid = parts[0], parts[1], parts[2], parts[3], parts[-1]
        port = _parse_port(local_addr)
        if port is None:
            continue
        results.append(
            {
                "port": port,
                "pid": pid,
                "command": pid_names.get(pid, "?"),
                "proto": proto,
                "addr": local_addr,
            }
        )
    return _dedupe(results)


def listening_ports():
    """Return a list of dicts: {port, pid, command, proto, addr}."""
    if IS_WINDOWS:
        return listening_ports_windows()
    return listening_ports_unix()


# ----------------------------------------------------------- process working dir
def cwd_of_unix(pid):
    out = _run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], timeout=10)
    for line in out.splitlines():
        if line.startswith("n"):
            return line[1:]
    return ""


def cwd_of_windows(pid):
    # Windows does not expose a process cwd without elevation/ctypes.
    # Return empty so clash detection degrades to port-number-only matching.
    return ""


def cwd_of(pid):
    if IS_WINDOWS:
        return cwd_of_windows(pid)
    return cwd_of_unix(pid)
