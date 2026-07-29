# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-30

### Added
- Core port registry: claim, list, and release ports per project (`add`, `list`, `rm`)
- Live TCP port scanner: cross-platform via `lsof` (macOS/Linux) and `netstat` + `tasklist` (Windows)
- Clash detection: reconcile registry against live listeners, including process cwd matching on Unix
- `status` command: live listening ports annotated with registry status (claimed / clash / unregistered)
- `conflicts` command: show ports double-claimed in the registry
- `next` command: find the next free TCP port at or after a given number
- `kill` command: terminate the process listening on a port (confirmation prompt, `--force` for SIGKILL)
- `isfree` command: boolean port check with exit codes for scripting
- `wait` command: block until a port frees up, with configurable timeout
- `export` command: dump registry as env vars, dotenv, or JSON
- Single JSON registry at `~/.config/portchk/registry.json` (per-machine)
- 30 unit tests covering registry CRUD, scanner parsing, export formats, and command dispatch
