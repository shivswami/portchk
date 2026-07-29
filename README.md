# portchk

[![PyPI version](https://img.shields.io/pypi/v/portchk.svg)](https://pypi.org/project/portchk/)
[![Python 3.8+](https://img.shields.io/pypi/pyversions/portchk.svg)](https://pypi.org/project/portchk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/shivswami/portchk/blob/main/LICENSE)
[![Tests](https://github.com/shivswami/portchk/actions/workflows/test.yml/badge.svg)](https://github.com/shivswami/portchk/actions/workflows/test.yml)

**Local dev port registry + scanner. Claim ports per project, detect clashes before your app fails to bind.**

If you run multiple local projects, you know the pain: everything defaults to `3000` or `8000`, and two of them collide. `portchk` keeps a lightweight registry of which project claims which port, and reconciles it against what's actually listening so you see a clash *before* your app refuses to start.

- **Cross-platform**: macOS/Linux via `lsof`, Windows via `netstat` + `tasklist`
- **Zero dependencies**: Python 3.8+ standard library only
- **Safe by default**: confirmation prompt before killing processes; read-only until you explicitly act
- **Single JSON registry**: `~/.config/portchk/registry.json` (per-machine)

## Install

    pip install portchk

Or from source:

    git clone https://github.com/shivswami/portchk.git
    cd portchk
    pip install .

## Quick start

    portchk                          # show live listeners + registry status
    portchk add 3000 myapp           # claim port 3000 for "myapp" (uses cwd)
    portchk add 8000 backend -p ~/projects/api
    portchk                          # now shows CLAIMED / CLASH / unregistered
    portchk next 3000                # find the next free port >= 3000

## Commands

| Command | Description |
|---|---|
| `portchk` | Default: live listening ports with registry status |
| `portchk list` | Show all registered projects and their ports |
| `portchk conflicts` | Show only ports claimed by more than one project |
| `portchk next [port]` | Print the next free TCP port at or after `port` (default 3000) |
| `portchk add <port> <name>` | Claim a port for a project (path = current dir) |
| `portchk add <port> <name> -p /path` | Claim with explicit project path |
| `portchk rm <port>` | Release a claim |
| `portchk kill <port> [--force]` | Kill the process listening on a port |
| `portchk isfree <port>` | Exit 0 if free, exit 1 if in use (for scripting) |
| `portchk wait <port> [--timeout N]` | Block until port is free (default 30s) |
| `portchk export [env\|dotenv\|json]` | Dump registry as env vars, dotenv, or JSON |
| `portchk --version` | Print version |
| `portchk --help` | Show usage |

## Status output explained

Running `portchk` shows every listening TCP port and how it relates to your registry:

- `claimed:myapp` (green) — the port is live and its process cwd matches a registered project path
- `claimed:myapp` (cyan) — the port is registered, but cwd could not be confirmed (Windows, or system process)
- `CLASH (claimed by ...)` (yellow) — the port is live but the running process doesn't match the registered project
- `unregistered` (grey) — the port is in use but not in your registry

## Killing processes

When you find a clash, kill the offender directly:

    portchk kill 3000              # prompts for confirmation
    portchk kill 3000 --force      # skip prompt, SIGKILL on Unix / taskkill /F on Windows

Without `--force`, you'll be asked to confirm. The command kills whatever process is listening on that port, whether or not it's in your registry.

## Scripting with isfree and wait

`isfree` and `wait` are designed for CI, Makefiles, and shell scripts. They use exit codes, not text, to signal state:

    # Only start dev server if port is free
    portchk isfree 3000 && npm run dev

    # Conditional logic
    if portchk isfree 5432; then
        echo "starting database..."
    fi

    # In CI: wait for a port to free up after teardown
    docker-compose down
    portchk wait 5432 --timeout 60
    pytest

`isfree` exits 0 if the port is free, 1 if in use. `wait` polls every 0.5s and exits 0 when the port frees up, or 1 on timeout.

## Exporting the registry

Export your registered ports for use in docker-compose, Makefiles, or .env files:

    portchk export env       # MYAPP_PORT=3000 / BACKEND_PORT_1=8000 / BACKEND_PORT_2=8001
    portchk export dotenv    # same format, alias
    portchk export json      # raw registry JSON

Wire into docker-compose:

    portchk export dotenv > .env
    docker-compose up

Variable naming: `NAME_PORT` for single-port projects, `NAME_PORT_1`, `NAME_PORT_2` for multi-port. Hyphens and spaces in project names become underscores.

## Why not just a markdown file?

A markdown list rots the day you forget to update it, can't be queried, and won't flag a clash until your app fails to bind. `portchk` gives you a queryable registry (`portchk next`) and a live scan that shows the actual state of your machine.

## Why not a background service?

A port manager shouldn't need its own port. `portchk` runs on demand and exits. No daemon, no background process, no extra listening socket.

## Registry format

`~/.config/portchk/registry.json`:

```json
{
  "projects": {
    "myapp": {
      "ports": [3000],
      "path": "/Users/you/projects/myapp"
    },
    "backend": {
      "ports": [8000, 8001],
      "path": "/Users/you/projects/api"
    }
  }
}
```

The registry is per-machine (ports differ across machines) so do not sync it.

## Windows note

On macOS/Linux, `portchk` can read each process's working directory, so it can confirm that the process on a registered port is actually *your* project (green `claimed:`). Windows does not expose a process's cwd without elevation, so on Windows the status falls back to port-number matching only. Clashes are still detected; the cwd confirmation degrades gracefully.

## Requirements

- **Python 3.8+**
- **macOS / Linux**: `lsof` (pre-installed on macOS, available on all major Linux distros)
- **Windows**: `netstat` and `tasklist` (both built into Windows)

No other dependencies. `portchk` uses the Python standard library only.

## License

MIT — see [LICENSE](LICENSE).

Copyright (c) 2026 Shivprakash Swami.
