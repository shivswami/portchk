# Contributing to portchk

Thanks for your interest in contributing! portchk is a small, focused tool and contributions are welcome.

## Development setup

    git clone https://github.com/shivswami/portchk.git
    cd portchk
    python3 -m venv .venv
    source .venv/bin/activate       # Windows: .venv\Scripts\activate
    pip install -e ".[dev]"

## Running tests

    python -m pytest tests/ -v

All tests must pass before a PR is merged. Tests cover pure logic (parsing, registry CRUD, export formats) and do not require elevated permissions.

## Style and conventions

- **Zero dependencies**: Python standard library only. Do not add `psutil`, `rich`, or any third-party package.
- **Cross-platform**: Code must work on macOS, Linux, and Windows. Platform-specific logic goes in `scanner.py` behind a common interface.
- **Keep cli.py thin**: CLI functions parse args, call core logic, and format output. Business logic belongs in `scanner.py` or `registry.py`.
- **Match existing style**: 4-space indentation, double quotes for strings, ANSI colours via the existing `colour()` helper.

## Submitting changes

1. Fork the repo and create a branch from `main`.
2. Write tests for any new functionality.
3. Ensure `python -m pytest tests/ -v` passes.
4. Open a pull request with a clear description of what changed and why.

## Reporting issues

Use [GitHub Issues](https://github.com/shivswami/portchk/issues). Include:
- OS and Python version
- The exact command you ran
- Expected vs actual output
