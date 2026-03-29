# autoresearch-cycle

`autoresearch-cycle` is a small local helper repo for running agent-driven iterations against the `pythonic-ninja-blog` UI.

The active use case is `examples/blogui/`, not the older generic API/CLI scaffold. The shared package under `src/autoresearch_cycle/` now only contains the agent runner used by that example.

## Quickstart

Install the Python dev environment:

```bash
uv sync --dev
```

If your machine is pinned to a private package index, force PyPI:

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --dev
```

Start the blog dev server in another terminal:

```bash
cd /Users/pythonicninja/PycharmProjects/pythonic-ninja-blog/web
npm run dev
```

Optional one-time Lighthouse warmup:

```bash
cd /Users/pythonicninja/PycharmProjects/pythonic-ninja-blog/web
npx --yes lighthouse --version
```

Run one autoresearch loop:

```bash
cd /Users/pythonicninja/PycharmProjects/autoresearch-cycle
./examples/blogui/run.sh
```

To switch the optimizer, edit `OPTIMIZER_AGENT` in `examples/blogui/config.py`. Supported values are `"claude"` and `"codex"`.

## Repository Map

- `examples/blogui/` - the runnable experiment
- `src/autoresearch_cycle/` - small shared helpers for agent execution, JSON files, readiness checks, and Lighthouse
- `tests/test_agent_runner.py` - regression tests for the shared runner
- `docs/setup.md` - requirements and troubleshooting
- `docs/examples.md` - step-by-step blog UI walkthrough
- `docs/prd.md` - archived early design notes from the broader engine idea

## Current Scope

This repo is intentionally narrow:

- no FastAPI service
- no Typer CLI
- no synthetic example domain
- no file-backed experiment engine

It exists to keep the blog UI experiment logic small while centralizing the agent-specific subprocess and parsing behavior in one place.
