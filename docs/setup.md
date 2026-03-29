# Setup

## Requirements

- Python 3.10+
- `uv`
- Node.js and `npm`
- Google Chrome
- `claude` or `codex`
- the sibling repo `/Users/pythonicninja/PycharmProjects/pythonic-ninja-blog`

## Python Environment

```bash
cd /Users/pythonicninja/PycharmProjects/autoresearch-cycle
uv sync --dev
```

If dependency resolution is forced through a private index, use:

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --dev
```

## Blog App

Run the blog dev server from the sibling repo:

```bash
cd /Users/pythonicninja/PycharmProjects/pythonic-ninja-blog/web
npm run dev
```

The experiment expects the app at `http://localhost:4321`.

## Run the Experiment

```bash
cd /Users/pythonicninja/PycharmProjects/autoresearch-cycle
./examples/blogui/run.sh
```

Results are written to:

```text
/tmp/blog-ui-research
```

## Troubleshooting

Private package index errors:

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple uv sync --dev
```

Blog server not reachable:

```bash
curl -I http://localhost:4321
```

Lighthouse first-run setup:

```bash
cd /Users/pythonicninja/PycharmProjects/pythonic-ninja-blog/web
npx --yes lighthouse --version
```

Switch agent:

Edit `examples/blogui/config.py` and change `OPTIMIZER_AGENT`.
