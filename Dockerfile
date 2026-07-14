# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
# Installs the package (and its deps) into an isolated virtualenv that we copy
# into the slim runtime image, keeping the final image small and build-tool-free.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only what's needed to build/install the package (better layer caching).
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Run as an unprivileged user.
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --create-home app

WORKDIR /app

# Bring in the prebuilt virtualenv (contains the installed console script).
COPY --from=builder /opt/venv /opt/venv

# Source + graph manifest: enables the optional `langgraph dev` server mode too.
COPY --chown=app:app src ./src
COPY --chown=app:app langgraph.json README.md ./

# Writable location for --output artifacts (mount a volume here to persist).
RUN mkdir -p /app/output && chown -R app:app /app/output

USER app

# The container behaves like the `code-reviewer` CLI. Provide the task + flags as
# arguments, e.g.:
#   docker run --rm --env-file .env code-reviewer:latest "Write a prime sieve"
ENTRYPOINT ["code-reviewer"]
CMD ["--help"]
