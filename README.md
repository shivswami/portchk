# portdocket

**Local dev port registry + scanner. Claim ports per project, detect clashes before your app fails to bind.**

If you run multiple local projects, you know the pain: everything defaults to `3000` or `8000`, and two of them collide. `portdocket` keeps a lightweight registry of which project claims which port, and reconciles it against what's actually listening so you see a clash *before* your app refuses to start.

- **Cross-platform**: macOS/Linux via `lsof`, Windows via `netstat` + `tasklist`
- **Zero dependencies**: Python 3.8+ standard library only
- **Read-only scanning**: inspects system state, changes nothing
- **Single JSON registry**: `~/.config/portdocket/registry.json` (per-machine)

## Install

    pip install portdocket

Or from source:

    git clone https://github.com/shivswami/portdocket.git
    cd portdocket
    pip install .

## Quick start

    portdocket                          # show live listeners + registry status
    portdocket add 3000 myapp           # claim port 3000 for "myapp" (uses cwd)
    portdocket add 8000 backend -p ~/projects/api
    portdocket                          # now shows CLAIMED / CLASH / unregistered
    portdocket next 3000                # find the next free port >= 3000

## Commands

| Command | Description |
|---|---|
| `portdocket` | Default: live listening ports with registry status |
| `portdocket list` | Show all registered projects and their ports |
| `portdocket conflicts` | Show only ports claimed by more than one project |
| `portdocket next [port]` | Print the next free TCP port at or after `port` (default 3000) |
| `portdocket add <port> <name>` | Claim a port for a project (path = current dir) |
| `portdocket add <port> <name> -p /path` | Claim with explicit project path |
| `portdocket rm <port>` | Release a claim |
| `portdocket --version` | Print version |
| `portdocket --help` | Show usage |

## Status output explained

Running `portdocket` shows every listening TCP port and how it relates to your registry:

- `claimed:myapp` (green) — the port is live and its process cwd matches a registered project path
- `claimed:myapp` (cyan) — the port is registered, but cwd could not be confirmed (Windows, or system process)
- `CLASH (claimed by ...)` (yellow) — the port is live but the running process doesn't match the registered project
- `unregistered` (grey) — the port is in use but not in your registry

## Why not just a markdown file?

A markdown list rots the day you forget to update it, can't be queried, and won't flag a clash until your app fails to bind. `portdocket` gives you a queryable registry (`portdocket next`) and a live scan that shows the actual state of your machine.

## Why not a background service?

A port manager shouldn't need its own port. `portdocket` runs on demand and exits. No daemon, no background process, no extra listening socket.

## Registry format

`~/.config/portdocket/registry.json`:

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

On macOS/Linux, `portdocket` can read each process's working directory, so it can confirm that the process on a registered port is actually *your* project (green `claimed:`). Windows does not expose a process's cwd without elevation, so on Windows the status falls back to port-number matching only. Clashes are still detected; the cwd confirmation degrades gracefully.

To get full cwd detection on Windows, install `psutil` and it will be used automatically:

    pip install portdocket[windows]

## License

MIT
