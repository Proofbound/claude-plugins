#!/usr/bin/env python3
"""Render a Jinja2 prompt template with a context dict.

Claude produces intro/summary/etc. text directly — but the *prompt* that drives
that generation comes from a canonical Jinja2 template fetched from the platform
(e.g. `introduction-prompt.jinja2`, cached under ~/.proofbound/cache/prompts/).
This helper renders that template so Claude doesn't have to interpret
`{% for %}` blocks in its head.

Usage:
    python3 render_prompt.py --template introduction-prompt.jinja2 \
                             --context /tmp/ctx.json

    # Or inline JSON:
    python3 render_prompt.py --template summary-prompt.jinja2 \
                             --context-json '{"title": "My Book", ...}'

    # Introduction/summary: work from what the chapters say, not their titles.
    python3 render_prompt.py --template introduction-prompt.jinja2 \
                             --context-json '{...}' \
                             --chapter-summaries ~/Books/<slug>/chapter-summaries.md

The rendered prompt goes to stdout so it can be piped, copied into the
conversation, or redirected into a file.

Requires Jinja2 (already a documented skill dependency for chapter generation).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound, Undefined
except ImportError:
    print(
        "ERROR: jinja2 is required.\n" "  Install with: pip install jinja2",
        file=sys.stderr,
    )
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import read_chapter_summaries  # noqa: E402

# Prompts are no longer vendored in the skill — they are fetched at runtime from
# the platform (GET /books/prompts via publish_book.py fetch-prompts) into a
# local cache. This is the default prompts dir; override with --prompts-dir.
PROMPTS_DIR = Path.home() / ".proofbound" / "cache" / "prompts"


class _ContextError(Exception):
    pass


def _load_context(args: argparse.Namespace) -> dict:
    if args.context and args.context_json:
        raise _ContextError("pass either --context or --context-json, not both.")
    if args.context:
        return json.loads(Path(args.context).expanduser().read_text(encoding="utf-8"))
    if args.context_json:
        return json.loads(args.context_json)
    return {}


def _add_chapter_summaries(context: dict, path: Path) -> None:
    if "chapter_summaries" in context:
        raise _ContextError("chapter_summaries given in both the context and --chapter-summaries.")
    summaries = read_chapter_summaries(path.expanduser())
    if not summaries:
        raise _ContextError(f"no '## Chapter <N>' entries found in {path}")
    context["chapter_summaries"] = summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--template",
        required=True,
        help="Template filename (relative to prompts/ dir, e.g. 'introduction-prompt.jinja2' or 'chapter-generation/system.jinja2').",
    )
    parser.add_argument("--context", help="Path to a JSON file with template variables.")
    parser.add_argument("--context-json", help="Inline JSON string with template variables.")
    parser.add_argument(
        "--chapter-summaries",
        type=Path,
        help="chapter-summaries.md to pass as chapter_summaries (introduction/summary prompts).",
    )
    parser.add_argument(
        "--prompts-dir",
        type=Path,
        default=PROMPTS_DIR,
        help="Override prompts dir (default: skill's synced templates).",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Fail on undefined variables instead of silently rendering empty strings."
    )
    args = parser.parse_args()

    prompts_dir: Path = args.prompts_dir.resolve()
    if not prompts_dir.is_dir():
        print(f"ERROR: prompts dir not found: {prompts_dir}", file=sys.stderr)
        return 1

    try:
        context = _load_context(args)
        if args.chapter_summaries:
            _add_chapter_summaries(context, args.chapter_summaries)
    except _ContextError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    env = Environment(
        loader=FileSystemLoader(str(prompts_dir)),
        undefined=StrictUndefined if args.strict else Undefined,
        keep_trailing_newline=True,
    )

    try:
        template = env.get_template(args.template)
    except TemplateNotFound:
        print(f"ERROR: template not found: {args.template} (in {prompts_dir})", file=sys.stderr)
        return 1

    try:
        rendered = template.render(**context)
    except Exception as exc:
        print(f"ERROR: render failed: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(rendered)
    if not rendered.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
