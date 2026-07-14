# Multi-Agent Code Reviewer

A two-node [LangGraph](https://docs.langchain.com/) application in which a **Coder**
agent writes a Python script and a **Reviewer** agent critiques it. They collaborate
in a **cycle** — the Coder refines the code based on the Reviewer's feedback — until
the Reviewer approves it or a hard iteration cap is reached.


---

## How it works

```
        ┌─────────┐        ┌──────────┐
START ─▶│  Coder  │ ─────▶ │ Reviewer │ ──▶ approved OR max iterations ──▶ END
        └─────────┘        └──────────┘
             ▲                   │
             └─── needs changes ─┘   (cycle)
```

- **Coder node** — on the first pass, writes a complete script from the task. On
  revisions, it makes **surgical edits** instead of rewriting the whole file: it
  emits `SEARCH/REPLACE` blocks that are applied to the previous code, so untouched
  lines stay byte-for-byte identical. If an edit doesn't apply cleanly, it falls
  back to a full rewrite. Increments the iteration counter.
- **Reviewer node** — critiques the code against the task and returns a **structured
  verdict** (`approved: bool`, `feedback: str`) via LangGraph structured output. On
  follow-up reviews it is given the **full history** of the task (earlier attempts and
  its own prior reviews) so it can focus on whether its requested changes were applied.
- **Conditional edge** — after each review, routes back to the Coder or ends the run.

> **Design note — surgical edits & reviewer memory.** The Coder edits like a human
> using an editor (SEARCH/REPLACE + a deterministic applier + full-rewrite fallback),
> which keeps revisions cheap and preserves already-approved code exactly — important
> once files grow beyond toy size. The Reviewer carries memory of the whole task so
> follow-up reviews are change-focused. See [`edits.py`](src/code_reviewer/edits.py)
> and the prompt builders in [`prompts.py`](src/code_reviewer/prompts.py).

### Stop conditions (defense in depth)

1. **Approval** — the Reviewer sets `approved = True` (primary stop).
2. **Max iterations** — the loop stops after `MAX_ITERATIONS` cycles (default **3**),
   guarding cost and preventing infinite loops.
3. **Recursion limit** — LangGraph's `recursion_limit` as a final backstop.

---

## Project structure

```
.
├── langgraph.json              # graph registration (LangGraph Platform / `langgraph dev`)
├── pyproject.toml
├── .env.example
├── src/code_reviewer/
│   ├── configuration.py        # typed settings (pydantic-settings)
│   ├── state.py                # graph state + Pydantic ReviewVerdict
│   ├── llm.py                  # Gemini chat-model factory
│   ├── prompts.py              # Coder (full + edit) & Reviewer prompts
│   ├── edits.py                # SEARCH/REPLACE parser + applier (surgical edits)
│   ├── nodes/
│   │   ├── coder.py            # full first draft, then surgical edits + fallback
│   │   └── reviewer.py         # history-aware, structured verdict
│   ├── graph.py                # builds & compiles the cyclic StateGraph (exports `graph`)
│   ├── runner.py               # reusable orchestration
│   └── cli.py                  # command-line entrypoint
└── tests/
    ├── unit/                   # routing, nodes, utils (fake LLMs)
    └── integration/            # full graph cycle (fake LLMs, no network)
```

---

## Setup

Requires Python 3.10+. Do this once.

### Windows (PowerShell)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install the project + test dependencies
pip install -e ".[dev]"

# 3. Create your .env, then open it and paste your Gemini API key
Copy-Item .env.example .env
```

> **If `python` opens the Microsoft Store or says "Python was not found":** the
> `python` command is a Windows alias stub. Use `py -3 -m venv .venv` instead, or
> the full interpreter path, e.g.
> `& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe" -m venv .venv`.

### macOS / Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then add your GOOGLE_API_KEY
```

Get a Gemini API key at <https://aistudio.google.com/app/apikey>.

---

## Running the project

Once the venv is **activated**, the `code-reviewer` command is on your PATH. The
task is required (in quotes); everything else is optional.

```powershell
# Simplest run — prints the final code to the terminal
code-reviewer "Write a function that reverses the words in a sentence"

# Save the final approved code to a file
code-reviewer "Implement a thread-safe LRU cache" -o output/lru_cache.py

# Verbose: show every Coder attempt + Reviewer verdict as it iterates
code-reviewer "Convert Roman numerals to integers and back, with validation" -o output/roman.py -v

# Limit the number of Coder<->Reviewer cycles and turn on debug logs
code-reviewer "Write a prime-number sieve" --max-iterations 3 --log-level DEBUG
```

### Running without activating the venv

Prefix with the venv's interpreter and call the module directly — handy on Windows:

```powershell
.\.venv\Scripts\python.exe -m code_reviewer.cli "Write a binary search function" -o output/bsearch.py -v
```

On macOS / Linux:

```bash
./.venv/bin/python -m code_reviewer.cli "Write a function that validates an email address" -o output/email.py -v
```

### All CLI flags

| Flag | Description |
| --- | --- |
| `task` (positional, required) | The problem to solve, in quotes. |
| `--output, -o FILE` | Write the **final** code to `FILE` (parent dirs auto-created). |
| `--verbose, -v` | Print every iteration to the terminal — each Coder attempt and the Reviewer's feedback. |
| `--max-iterations N` | Override the Coder↔Reviewer cycle cap (default from `.env`, 3). |
| `--log-level LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR`. |
| `--help, -h` | Show usage and exit. |

> **Note:** `--verbose` output is **terminal-only**. The `--output` file always
> contains just the single final result — intermediate attempts are never written
> to disk.

**Exit codes:** `0` approved · `2` stopped at max iterations without approval · `1` error.

### Programmatic use (from Python)

```python
from code_reviewer import run_review

final = run_review("Write a prime-number sieve", max_iterations=3)
print(final["approved"], final["iterations"])
print(final["code"])
```

---

## Configuration

All settings come from environment variables / `.env` (see `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | — | **Required.** Gemini API key. |
| `MODEL_NAME` | `gemini-3.1-flash-lite` | Gemini model for both agents. |
| `MAX_ITERATIONS` | `3` | Max review cycles. |
| `CODER_TEMPERATURE` | `0.3` | Coder sampling temperature. |
| `REVIEWER_TEMPERATURE` | `0.0` | Reviewer sampling temperature. |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |

---

## Testing

Tests use fake LLMs — **no API key or network required**:

```powershell
# After activating the venv
pytest                 # run all tests
pytest -v              # list each test by name

# Without activating the venv
.\.venv\Scripts\python.exe -m pytest
```

Coverage includes the routing/stop logic, both nodes, the helpers, the CLI
transcript, the SEARCH/REPLACE edit parser & applier (including the fallback path),
the history-aware reviewer prompt, and full end-to-end cycles (loops-until-approved,
stops-at-max-iterations, first-pass approval).

---

## Docker

A lean, multi-stage, non-root image is provided. The container behaves like the
`code-reviewer` CLI — pass the task and flags as arguments.

Build:

```bash
docker build -t code-reviewer:latest .
```

Run (secrets passed at runtime via `--env-file`, never baked into the image):

```bash
docker run --rm --env-file .env \
  -v "$(pwd)/output:/app/output" \
  code-reviewer:latest \
  "Write a function that parses a CSV file into a list of dicts" -o output/csv.py
```

The `-v` mount persists any `--output` artifacts to `./output` on the host.

### docker compose

```bash
docker compose build
docker compose run --rm code-reviewer "Implement a thread-safe LRU cache" -o output/cache.py
```

**Image notes**
- Multi-stage build → runtime image has no build tools, just the venv + package.
- Runs as an unprivileged `app` user.
- `.env` is excluded via `.dockerignore`; provide credentials at runtime.

---

## LangGraph Studio / Platform (optional)

The graph is registered in `langgraph.json` as `code_reviewer`, so you can also run
it in LangGraph Studio:

```bash
pip install "langgraph-cli[inmem]"
langgraph dev
```

---

## License

MIT
