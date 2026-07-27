#!/usr/bin/env python3
"""portchk - local dev port registry + scanner.

Claim ports per project, detect clashes before your app fails to bind.

Usage:
  portchk                       live listening ports + registry status
  portchk list                  show the registry
  portchk conflicts             show only double-claimed ports
  portchk next [port]           print the next free TCP port >= <port> (default 3000)
  portchk add <port> <name>     claim a port (path = current dir)
  portchk add <port> <name> -p /path/to/project
  portchk rm <port>             release a claim
  portchk kill <port> [--force] kill the process listening on a port
  portchk isfree <port>         exit 0 if port is free, exit 1 if in use
  portchk wait <port> [--timeout N]  block until port is free (default 30s)
  portchk export [env|dotenv|json]    dump registry as env vars, dotenv, or JSON
  portchk --version
  portchk --help
"""

import os
import sys
import time

from . import __version__
from .registry import build_port_index, find_conflicts, load, save, to_env_lines, to_json
from .scanner import cwd_of, find_pid_for_port, kill_pid, listening_ports

# ---------- ANSI ----------
DIM, BOLD = "\033[2m", "\033[1m"
GREEN, YELLOW, RED, CYAN = "\033[32m", "\033[33m", "\033[31m", "\033[36m"
RESET = "\033[0m"


def colour(text, c):
    if not sys.stdout.isatty():
        return text
    return f"{c}{text}{RESET}"


def _usage():
    print(__doc__.strip())


# -------------------------------------------------------------------- commands
def cmd_status(_args):
    reg = load()
    idx = build_port_index(reg)
    by_path = {
        os.path.realpath(info.get("path", "")): name
        for name, info in reg["projects"].items()
        if info.get("path")
    }
    live = listening_ports()
    cwd_cache = {}

    def get_cwd(pid):
        if pid not in cwd_cache:
            cwd_cache[pid] = cwd_of(pid)
        return cwd_cache[pid]

    live_ports = {r["port"] for r in live}

    print(colour("LIVE listening TCP ports", BOLD))
    print(colour("-" * 78, DIM))
    for r in sorted(live, key=lambda x: x["port"]):
        port = r["port"]
        cwd = get_cwd(r["pid"])
        claimed = idx.get(port, [])
        if claimed:
            if cwd:
                resolved = os.path.realpath(cwd)
                matched = by_path.get(resolved)
                if matched and matched in claimed:
                    status = colour("claimed:" + matched, GREEN)
                else:
                    status = colour(
                        "CLASH (claimed by " + ",".join(claimed) + ")", YELLOW
                    )
            else:
                status = colour("claimed:" + ",".join(claimed), CYAN)
        else:
            status = colour("unregistered", DIM)
        print(f"  {port:<6} {r['command']:<14} pid {r['pid']:<7} {status}")
        if cwd:
            print(colour(f"         {cwd}", DIM))

    print()
    print(colour("REGISTERED but not running", BOLD))
    print(colour("-" * 78, DIM))
    idle = [(port, names) for port, names in sorted(idx.items()) if port not in live_ports]
    if not idle:
        print(colour("  (all registered ports are live)", DIM))
    else:
        for port, names in idle:
            print(f"  {port:<6} {','.join(names)}")

    print()
    conflicts = find_conflicts(reg)
    print(
        colour("Conflicts: ", BOLD)
        + (colour("none", GREEN) if not conflicts else colour("see 'portchk conflicts'", YELLOW))
    )


def cmd_list(_args):
    reg = load()
    if not reg["projects"]:
        print(colour("(registry empty) use: portchk add <port> <name>", DIM))
        return
    for name in sorted(reg["projects"]):
        info = reg["projects"][name]
        ports = ", ".join(str(p) for p in info.get("ports", [])) or colour("(none)", DIM)
        path = info.get("path", colour("(no path)", DIM))
        print(colour(f"  {name}", CYAN))
        print(colour(f"    ports: {ports}", DIM))
        print(colour(f"    path:  {path}", DIM))


def cmd_conflicts(_args):
    reg = load()
    conf = find_conflicts(reg)
    if not conf:
        print(colour("No double-claimed ports in the registry.", GREEN))
    else:
        for port, names in conf:
            print(colour(f"  port {port} claimed by: {', '.join(names)}", YELLOW))


def _is_port_listening(port):
    return any(r["port"] == port for r in listening_ports())


def cmd_next(args):
    start = int(args[0]) if args else 3000
    reg = load()
    claimed = set(build_port_index(reg).keys())
    port = start
    while port < 65536:
        if port not in claimed and not _is_port_listening(port):
            print(port)
            return
        port += 1
    print(colour("no free port found", RED), file=sys.stderr)
    sys.exit(1)


def cmd_add(args):
    if len(args) < 2:
        print(colour("usage: portchk add <port> <name> [-p /path]", RED), file=sys.stderr)
        sys.exit(2)
    port = int(args[0])
    name = args[1]
    path = os.getcwd()
    rest = args[2:]
    if "-p" in rest:
        i = rest.index("-p")
        path = os.path.abspath(rest[i + 1])
    reg = load()
    reg["projects"].setdefault(name, {"ports": [], "path": path})
    reg["projects"][name]["path"] = path
    if port not in reg["projects"][name]["ports"]:
        reg["projects"][name]["ports"].append(port)
    save(reg)
    print(colour(f"claimed {port} for '{name}' ({path})", GREEN))


def cmd_rm(args):
    if not args:
        print(colour("usage: portchk rm <port>", RED), file=sys.stderr)
        sys.exit(2)
    port = int(args[0])
    reg = load()
    removed = []
    for name, info in reg["projects"].items():
        if port in info.get("ports", []):
            info["ports"] = [p for p in info["ports"] if p != port]
            removed.append(name)
    if removed:
        save(reg)
        print(colour(f"released {port} from: {', '.join(removed)}", GREEN))
    else:
        print(colour(f"port {port} was not claimed by anyone", DIM))


# --------------------------------------------------------------- kill
def cmd_kill(args):
    if not args:
        print(colour("usage: portchk kill <port> [--force]", RED), file=sys.stderr)
        sys.exit(2)
    port = int(args[0])
    force = "--force" in args or "-f" in args
    pid = find_pid_for_port(port)
    if pid is None:
        print(colour(f"port {port} is not in use", DIM))
        return
    command = ""
    for r in listening_ports():
        if r["port"] == port:
            command = r["command"]
            break
    if not force:
        label = f"pid {pid} ({command}) on port {port}"
        try:
            resp = input(f"Kill {label}? [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if resp.strip().lower() not in ("y", "yes"):
            print(colour("aborted", DIM))
            return
    ok = kill_pid(pid, force=force)
    if ok:
        print(colour(f"killed pid {pid} ({command}) on port {port}", GREEN))
    else:
        print(colour(f"failed to kill pid {pid} on port {port}", RED), file=sys.stderr)
        sys.exit(1)


# --------------------------------------------------------------- isfree
def cmd_isfree(args):
    if not args:
        print(colour("usage: portchk isfree <port>", RED), file=sys.stderr)
        sys.exit(2)
    port = int(args[0])
    if _is_port_listening(port):
        print(colour(f"port {port} is in use", RED))
        sys.exit(1)
    else:
        print(colour(f"port {port} is free", GREEN))
        sys.exit(0)


# --------------------------------------------------------------- wait
def cmd_wait(args):
    if not args:
        print(colour("usage: portchk wait <port> [--timeout 30]", RED), file=sys.stderr)
        sys.exit(2)
    port = int(args[0])
    timeout = 30
    if "--timeout" in args:
        i = args.index("--timeout")
        if i + 1 < len(args):
            timeout = int(args[i + 1])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_port_listening(port):
            print(colour(f"port {port} is free", GREEN))
            return
        time.sleep(0.5)
    print(colour(f"timeout: port {port} still in use after {timeout}s", RED), file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------- export
def cmd_export(args):
    fmt = args[0] if args else "env"
    reg = load()
    if fmt in ("env", "dotenv"):
        for line in to_env_lines(reg):
            print(line)
    elif fmt == "json":
        print(to_json(reg))
    else:
        print(colour(f"unknown format: {fmt} (use: env, dotenv, json)", RED), file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------- dispatch
COMMANDS = {
    "status": cmd_status,
    "list": cmd_list,
    "conflicts": cmd_conflicts,
    "next": cmd_next,
    "add": cmd_add,
    "rm": cmd_rm,
    "kill": cmd_kill,
    "isfree": cmd_isfree,
    "wait": cmd_wait,
    "export": cmd_export,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] in ("-h", "--help"):
        _usage()
        return
    if argv and argv[0] in ("-v", "--version"):
        print(__version__)
        return

    cmd = argv[0] if argv else "status"
    if cmd not in COMMANDS:
        print(colour(f"unknown command: {cmd}", RED), file=sys.stderr)
        _usage()
        sys.exit(2)

    COMMANDS[cmd](argv[1:] if argv else [])


if __name__ == "__main__":
    main()
