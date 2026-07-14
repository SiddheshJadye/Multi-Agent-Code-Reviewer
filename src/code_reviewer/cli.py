"""Command-line entrypoint.

Usage::

    code-reviewer "Write a function that parses a CSV file into a list of dicts"
    python -m code_reviewer.cli "..." --max-iterations 2 --output solution.py
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from .configuration import get_settings
from .runner import run_review
from .utils import configure_logging, message_text

_RULE = "=" * 70


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-reviewer",
        description="Two-agent (Coder + Reviewer) LangGraph that iteratively "
        "writes and critiques a Python script until approved.",
    )
    parser.add_argument("task", help="Description of the Python script to build.")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Override the max Coder<->Reviewer cycles (default from settings).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write the final code to this file instead of stdout only.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print every iteration to the terminal: each Coder attempt and the "
        "Reviewer's feedback. Does NOT affect the --output file (only the final "
        "approved code is ever written there).",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    load_dotenv()
    args = _build_parser().parse_args(argv)

    settings = get_settings()
    configure_logging(args.log_level or settings.log_level)

    if not settings.google_api_key:
        # Not fatal on its own (client may read GOOGLE_API_KEY from env), but the
        # most common failure mode, so warn clearly.
        print(
            "WARNING: GOOGLE_API_KEY is not set. Create a .env from .env.example "
            "or export GOOGLE_API_KEY before running.\n",
            file=sys.stderr,
        )

    try:
        final = run_review(args.task, max_iterations=args.max_iterations)
    except Exception as exc:  # surface a clean message instead of a traceback
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.verbose:
        _print_transcript(final)

    _print_summary(final)

    if args.output:
        # Only the FINAL code is ever persisted; intermediate attempts are
        # terminal-only (via --verbose) and never written to disk.
        parent = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(parent, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(final.get("code", ""))
        print(f"\nFinal code written to {args.output}")

    # Exit non-zero if we stopped without approval, so scripts/CI can detect it.
    return 0 if final.get("approved") else 2


def _print_transcript(state: dict) -> None:
    """Print the full per-iteration history to the terminal (stdout only).

    Reconstructed from the graph's ``messages`` audit trail: each Coder attempt
    (``name == "coder"``) followed by the Reviewer's verdict + feedback
    (``name == "reviewer"``). This is purely for the user to watch how the code
    evolved; nothing here is written to the --output file.
    """
    messages = state.get("messages", [])
    if not messages:
        return

    print(f"\n{_RULE}")
    print("ITERATION-BY-ITERATION TRANSCRIPT (terminal only)")
    print(_RULE)

    iteration = 0
    for msg in messages:
        name = getattr(msg, "name", None)
        content = message_text(msg.content)

        if name == "coder":
            iteration += 1
            print(f"\n>>> Iteration {iteration} - Coder wrote:\n")
            print(content)
        elif name == "reviewer":
            # content is prefixed with "[APPROVED]" / "[CHANGES REQUESTED]".
            print(f"\n--- Iteration {iteration} - Reviewer said: ---")
            print(content)


def _print_summary(state: dict) -> None:
    approved = state.get("approved", False)
    iterations = state.get("iterations", 0)

    print(f"\n{_RULE}")
    print(f"RESULT: {'APPROVED' if approved else 'NOT APPROVED (max iterations hit)'}")
    print(f"Iterations used: {iterations}")
    print(_RULE)

    print("\n--- Final review ---")
    print(state.get("review", "(no review recorded)"))

    print("\n--- Final code ---\n")
    print(state.get("code", "(no code produced)"))


if __name__ == "__main__":
    raise SystemExit(main())
