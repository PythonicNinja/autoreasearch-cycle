# Blog UI Example

The main example lives in `examples/blogui/`.

## Prerequisites

- Python 3.10+
- `uv`
- Node.js and `npm`
- Google Chrome
- a working sibling checkout at `/Users/pythonicninja/PycharmProjects/pythonic-ninja-blog`
- either `claude` or `codex` installed locally

## Run Flow

Install Python dependencies:

```bash
cd /Users/pythonicninja/PycharmProjects/autoresearch-cycle
uv sync --dev
```

Start the blog app in another terminal:

```bash
cd /Users/pythonicninja/PycharmProjects/pythonic-ninja-blog/web
npm run dev
```

Optional first-run Lighthouse warmup:

```bash
cd /Users/pythonicninja/PycharmProjects/pythonic-ninja-blog/web
npx --yes lighthouse --version
```

Run the experiment:

```bash
cd /Users/pythonicninja/PycharmProjects/autoresearch-cycle
./examples/blogui/run.sh
```

The script will:

1. check that `http://localhost:4321` is reachable
2. ask the configured agent to make one focused UI change
3. run Lighthouse accessibility and performance checks
4. commit accepted changes or roll them back
5. write experiment history to `/tmp/blog-ui-research`

## Switching Agents

Edit `examples/blogui/config.py`:

```python
OPTIMIZER_AGENT = "claude"
```

Supported values:

- `"claude"`
- `"codex"`

## Expected Output Shape

The experiment expects the agent to return exactly this JSON shape:

```json
{
  "change": "what changed",
  "reason": "why it changed",
  "files": ["list/of/files"]
}
```

That validation is kept in the blog UI example itself, while the generic subprocess and JSON extraction logic lives in `src/autoresearch_cycle/agent_runner.py`.
