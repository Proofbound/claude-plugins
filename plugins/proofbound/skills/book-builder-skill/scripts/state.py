#!/usr/bin/env python3
"""Durable per-book state for the book-builder skill (schema v2).

The project directory owns the state. `book-state.json` inside the project dir
is **canonical**; the home directory holds only a pointer/index record so
`list` can find in-progress books without scanning the filesystem:

  Canonical:  <project_dir>/book-state.json
  Index:      ~/.proofbound/in-progress/<slug>.json   (pointer, not a copy)
  Projection: <project_dir>/PROGRESS.md               (generated, never truth)

This inverts schema v1, where the home record was canonical and the project dir
held a `.proofbound-state.json` mirror. v1 records migrate on load: the freshest
legacy record wins, is rewritten into the project dir as v2, the home record
becomes a pointer, and the legacy mirror is deleted. A v2 project state always
wins over any legacy record — records are never silently merged. A v1 record
whose `project_dir` no longer exists is *flagged* by `list`, never deleted.

Write order is honest about what is atomic: the canonical JSON is persisted
atomically (temp file + os.replace) first, then `PROGRESS.md` is regenerated
from it. If projection generation fails, canonical state is still valid and
`render-progress` repairs it. Every mutating command regenerates the projection;
`show` regenerates it when missing, stale (revision mismatch), or malformed, so
a resume always reads a truthful PROGRESS.md. There is deliberately no `.prev`
backup — a second stateful file would only add drift. Corrupt state is instead
rebuilt from the project's own artifacts (`state.py rebuild`).

CLI (callable from SKILL.md prose):
    python3 scripts/state.py list
    python3 scripts/state.py show <slug>
    python3 scripts/state.py init <slug> [--project-dir D --title T --author A
                                          --target-words N --chapter-count N]
    python3 scripts/state.py set <slug> <dotted.path> <value>
    python3 scripts/state.py gate <slug> (research_map|outline|book_bible) <status>
    python3 scripts/state.py mark <slug> chapter <N> <stage> \
                                 [--chars N] [--words N] [--target-words N]
                                 [--summary-written] [--bump-revision]
    python3 scripts/state.py mark <slug> (intro|summary) <status> [--chars N]
    python3 scripts/state.py render-progress <slug>
    python3 scripts/state.py rebuild <slug> [--project-dir D]
    python3 scripts/state.py delete <slug> [--purge]

Stdlib only.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

INDEX_ROOT = Path.home() / ".proofbound" / "in-progress"
DEFAULT_BOOKS_ROOT = Path.home() / "Books"

STATE_BASENAME = "book-state.json"
PROGRESS_BASENAME = "PROGRESS.md"
LEGACY_MIRROR_BASENAME = ".proofbound-state.json"

# Chapter lifecycle (v2). `pitched`/`drafted`/`edited` track the per-chapter
# material → draft → editor loop; `saved` is the only stage that claims a
# durable artifact on disk.
VALID_CHAPTER_STAGES = {
    "pending",
    "pitched",
    "drafted",
    "edited",
    "saved",
    "truncated",
    "failed",
}
# intro/summary keep the v1 status vocabulary — they have no pitch/edit stages.
VALID_ARTIFACT_STATUSES = {"pending", "in_progress", "complete", "truncated", "failed"}

VALID_GATES = {"research_map", "outline", "book_bible"}
VALID_GATE_STATUSES = {"not_applicable", "pending", "approved"}

# v1 chapter `status` → v2 chapter `stage`.
_V1_STATUS_TO_STAGE = {
    "pending": "pending",
    "in_progress": "drafted",
    "complete": "saved",
    "truncated": "truncated",
    "failed": "failed",
}

_PROGRESS_REVISION_RE = re.compile(r"revision\s+(\d+)")


class StateError(Exception):
    """Raised for bad state inputs or corrupted files (user-facing message)."""


# ---------- IO primitives ----------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".state.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=False)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".progress.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise StateError(f"no state file at {path}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateError(
            f"state file is corrupted: {path}\n"
            f"  parse error: {exc.msg} at line {exc.lineno}, col {exc.colno}\n"
            f"  recovery: run 'state.py rebuild <slug>' to reconstruct from the "
            f"project's artifacts, or repair the JSON by hand"
        )
    if not isinstance(data, dict):
        raise StateError(f"state file is not a JSON object: {path}")
    return data


def _read_json_or_none(path: Path | None) -> dict[str, Any] | None:
    """Read a state file, returning None when it is absent OR unusable.

    Used for the *candidate* records during migration, where a corrupt or
    missing file simply means "this candidate does not count".
    """
    if path is None or not path.is_file():
        return None
    try:
        return _read_json(path)
    except StateError:
        return None


# ---------- Paths ----------


def index_path(slug: str) -> Path:
    if not slug or "/" in slug or slug.startswith("."):
        raise StateError(f"invalid slug: {slug!r}")
    return INDEX_ROOT / f"{slug}.json"


def state_path(project_dir: Path | str) -> Path:
    return Path(project_dir).expanduser() / STATE_BASENAME


def progress_path(project_dir: Path | str) -> Path:
    return Path(project_dir).expanduser() / PROGRESS_BASENAME


def legacy_mirror_path(project_dir: Path | str) -> Path:
    return Path(project_dir).expanduser() / LEGACY_MIRROR_BASENAME


def default_project_dir(slug: str) -> Path:
    return DEFAULT_BOOKS_ROOT / slug


def _project_dir_of(record: dict[str, Any]) -> Path | None:
    """Extract a project dir from either a v2 pointer or a v1 full record."""
    raw = record.get("project_dir") or (record.get("paths") or {}).get("project")
    if not raw:
        return None
    return Path(str(raw)).expanduser()


def _is_pointer(record: dict[str, Any]) -> bool:
    """A pointer carries no book payload — only where the real state lives."""
    return "chapters" not in record and "book" not in record


# ---------- Migration ----------


def _word_count(path: Path) -> int | None:
    try:
        return len(path.read_text(encoding="utf-8").split())
    except OSError:
        return None


def _chapter_file(project_dir: Path | None, number: str) -> Path | None:
    if project_dir is None:
        return None
    for ext in ("qmd", "md"):
        candidate = project_dir / "chapters" / f"chapter_{number}.{ext}"
        if candidate.is_file():
            return candidate
    return None


def _default_gates() -> dict[str, str]:
    return {"research_map": "not_applicable", "outline": "pending", "book_bible": "pending"}


def migrate_record(record: dict[str, Any], project_dir: Path | None) -> dict[str, Any]:
    """Return a schema-v2 copy of `record` (idempotent for v2 input)."""
    migrated = dict(record)
    if int(migrated.get("schema_version") or 1) >= SCHEMA_VERSION:
        migrated.setdefault("gates", _default_gates())
        migrated.setdefault("revision", 0)
        return migrated

    chapters: dict[str, Any] = {}
    for number, raw_entry in (migrated.get("chapters") or {}).items():
        entry = dict(raw_entry) if isinstance(raw_entry, dict) else {}
        status = entry.pop("status", "pending")
        entry["stage"] = _V1_STATUS_TO_STAGE.get(status, "pending")
        if "words" not in entry:
            chapter_file = _chapter_file(project_dir, str(number))
            words = _word_count(chapter_file) if chapter_file else None
            if words is not None:
                entry["words"] = words
        entry.setdefault("summary_written", False)
        chapters[str(number)] = entry
    migrated["chapters"] = chapters

    # v1 had no gate concept. An outline demonstrably existed if chapters were
    # enumerated; the research map and bible gate are new, so they start unset.
    gates = _default_gates()
    if chapters:
        gates["outline"] = "approved"
    migrated["gates"] = gates

    migrated["revision"] = int(migrated.get("revision") or 0)
    migrated["schema_version"] = SCHEMA_VERSION
    if project_dir is not None:
        migrated.setdefault("paths", {})["project"] = str(project_dir)
    return migrated


def _freshest(candidates: Iterable[dict[str, Any] | None]) -> dict[str, Any] | None:
    real = [c for c in candidates if c]
    if not real:
        return None
    return max(real, key=lambda c: str(c.get("updated_at") or ""))


# ---------- Public API ----------


def load_state(slug: str) -> dict[str, Any]:
    """Load canonical state for `slug`, migrating a v1 record in place.

    Resolution order (never a merge):
      1. A schema-v2 `<project>/book-state.json` wins unconditionally.
      2. Otherwise the freshest legacy record (home record, project v1 state,
         or legacy mirror) is migrated to v2, written into the project dir, the
         home record is rewritten as a pointer, and the mirror is deleted.
    """
    record = _read_json(index_path(slug))
    project_dir = _project_dir_of(record)

    # A canonical file that exists but will not parse is a loud failure, not a
    # missing candidate — silently falling back to a legacy record would lose work.
    project_state = None
    if project_dir and state_path(project_dir).is_file():
        project_state = _read_json(state_path(project_dir))
    if project_state and int(project_state.get("schema_version") or 1) >= SCHEMA_VERSION:
        return project_state

    legacy_home = None if _is_pointer(record) else record
    legacy_mirror = _read_json_or_none(legacy_mirror_path(project_dir)) if project_dir else None
    winner = _freshest([legacy_home, project_state, legacy_mirror])
    if winner is None:
        raise StateError(
            f"no usable state for slug {slug!r}: the index points at "
            f"{project_dir or '(nowhere)'} but no {STATE_BASENAME} is there.\n"
            f"  recovery: 'state.py rebuild {slug} --project-dir <dir>'"
        )
    if project_dir is None or not project_dir.is_dir():
        raise StateError(
            f"orphaned v1 record for slug {slug!r}: project dir {project_dir or '(unset)'} "
            f"does not exist, so its state cannot be migrated.\n"
            f"  recovery: restore the project dir, or 'state.py delete {slug}' to drop the record"
        )

    migrated = migrate_record(winner, project_dir)
    migrated["slug"] = slug
    _persist(migrated, project_dir)
    with contextlib.suppress(OSError):
        legacy_mirror_path(project_dir).unlink()
    return migrated


def save_state(state: dict[str, Any]) -> dict[str, Any]:
    """Persist canonical project state, refresh the index pointer + projection."""
    slug = state.get("slug")
    if not isinstance(slug, str) or not slug:
        raise StateError("state payload missing 'slug'")
    project_dir = _project_dir_of(state)
    if project_dir is None:
        raise StateError(f"state for {slug!r} has no paths.project; canonical state lives in the project dir")
    return _persist(state, project_dir)


def _persist(state: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    state["schema_version"] = SCHEMA_VERSION
    state["revision"] = int(state.get("revision") or 0) + 1
    state["updated_at"] = _now_iso()
    state.setdefault("paths", {})["project"] = str(project_dir)

    project_dir.mkdir(parents=True, exist_ok=True)
    # Canonical first, atomically. Everything below is derived and repairable.
    _atomic_write_json(state_path(project_dir), state)
    _atomic_write_json(
        index_path(str(state["slug"])),
        {
            "schema_version": SCHEMA_VERSION,
            "slug": state["slug"],
            "project_dir": str(project_dir),
            "updated_at": state["updated_at"],
        },
    )
    try:
        write_progress(state)
    except Exception as exc:  # — a projection failure must not lose the commit
        print(
            f"WARNING: canonical state saved but {PROGRESS_BASENAME} could not be written: {exc}\n"
            f"  repair: python3 scripts/state.py render-progress {state['slug']}",
            file=sys.stderr,
        )
    return state


def delete_state(slug: str, *, purge: bool = False) -> bool:
    """Drop the index record. With `purge`, also remove the project's state files."""
    path = index_path(slug)
    project_dir: Path | None = None
    existed = path.exists()
    if existed:
        with contextlib.suppress(StateError):
            project_dir = _project_dir_of(_read_json(path))
        path.unlink()
    if purge and project_dir is not None:
        for victim in (state_path(project_dir), progress_path(project_dir), legacy_mirror_path(project_dir)):
            with contextlib.suppress(OSError):
                victim.unlink()
    return existed


def init_state(
    slug: str,
    *,
    project_dir: Path | str | None = None,
    title: str | None = None,
    author: str | None = None,
    target_words: int | None = None,
    chapter_count: int | None = None,
) -> dict[str, Any]:
    """Create a new state record. Fails if one already exists for this slug."""
    idx = index_path(slug)
    resolved = Path(project_dir).expanduser() if project_dir else default_project_dir(slug)
    if idx.exists() or state_path(resolved).exists():
        raise StateError(
            f"state already exists for slug {slug!r} at {state_path(resolved)}. "
            f"Use 'state show' to inspect, or 'state delete' to remove."
        )
    chapters: dict[str, Any] = {}
    if chapter_count:
        for i in range(1, chapter_count + 1):
            chapters[str(i)] = {"stage": "pending", "summary_written": False}
    state = {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "revision": 0,
        "phase": 1,
        "book": {
            "title": title or "",
            "author": author or "",
            "target_words": target_words or 0,
        },
        "gates": _default_gates(),
        "paths": {"project": str(resolved), "cc_config": None, "outline": None},
        "chapters": chapters,
        "intro": {"status": "pending"},
        "summary": {"status": "pending"},
        "updated_at": _now_iso(),
    }
    return _persist(state, resolved)


def mark_artifact(
    slug: str,
    artifact: str,
    status: str,
    *,
    chars: int | None = None,
    words: int | None = None,
    summary_written: bool | None = None,
    target_words: int | None = None,
    bump_revision: bool = False,
) -> dict[str, Any]:
    """Update an artifact's stage/status.

    `artifact` is "intro", "summary", or "chapter/<N>" (e.g. "chapter/3").
    Chapters use the v2 stage vocabulary; intro/summary keep v1 statuses.
    Omitted `chars`/`words` are derived from the chapter file when it exists.
    """
    state = load_state(slug)
    is_chapter = artifact.startswith("chapter/")
    allowed = VALID_CHAPTER_STAGES if is_chapter else VALID_ARTIFACT_STATUSES
    if status not in allowed:
        raise StateError(f"invalid {'stage' if is_chapter else 'status'} {status!r}; must be one of {sorted(allowed)}")

    entry = _select_artifact_entry(state, artifact)
    entry["stage" if is_chapter else "status"] = status

    if is_chapter and (chars is None or words is None):
        chapter_file = _chapter_file(_project_dir_of(state), artifact.partition("/")[2])
        if chapter_file is not None:
            text = chapter_file.read_text(encoding="utf-8")
            chars = len(text) if chars is None else chars
            words = len(text.split()) if words is None else words

    if chars is not None:
        entry["chars"] = int(chars)
    if words is not None:
        entry["words"] = int(words)
    if summary_written is not None:
        entry["summary_written"] = bool(summary_written)
    # The chapter's summed section-beat target. Persisting it is what gives the
    # recorded `words` something to be compared against — without it, "state the
    # target" has no anchor and a short chapter looks identical to a complete one.
    if target_words is not None:
        entry["target_words"] = int(target_words)
    if bump_revision:
        entry["revision_count"] = int(entry.get("revision_count", 0)) + 1

    return save_state(state)


def set_gate(slug: str, gate: str, status: str) -> dict[str, Any]:
    if gate not in VALID_GATES:
        raise StateError(f"invalid gate {gate!r}; must be one of {sorted(VALID_GATES)}")
    if status not in VALID_GATE_STATUSES:
        raise StateError(f"invalid gate status {status!r}; must be one of {sorted(VALID_GATE_STATUSES)}")
    state = load_state(slug)
    state.setdefault("gates", _default_gates())[gate] = status
    return save_state(state)


def set_dotted(slug: str, dotted_path: str, value: Any) -> dict[str, Any]:
    """Set a nested field by dotted path, e.g. 'book.title'."""
    if not dotted_path:
        raise StateError("empty dotted path")
    state = load_state(slug)
    keys = dotted_path.split(".")
    cursor: Any = state
    for key in keys[:-1]:
        if not isinstance(cursor, dict):
            raise StateError(f"cannot descend into non-object at {key!r}")
        cursor = cursor.setdefault(key, {})
    if not isinstance(cursor, dict):
        raise StateError(f"cannot set {dotted_path!r}: parent is not an object")
    cursor[keys[-1]] = _coerce_value(value)
    return save_state(state)


def rebuild_from_artifacts(
    slug: str,
    project_dir: Path | str,
    *,
    title: str | None = None,
    author: str | None = None,
) -> dict[str, Any]:
    """Reconstruct state from what is on disk, discarding an unreadable record.

    Reads `outline.yml` for the chapter roster (falling back to the files in
    `chapters/`), `chapters/chapter_N.*` for stages and counts, and
    `chapter-summaries.md` for which chapters already have a summary entry.
    """
    resolved = Path(project_dir).expanduser()
    if not resolved.is_dir():
        raise StateError(f"cannot rebuild: {resolved} is not a directory")

    numbers = _outline_chapter_numbers(resolved) or _chapter_file_numbers(resolved)
    summarized = _summarized_chapter_numbers(resolved)

    chapters: dict[str, Any] = {}
    for number in numbers:
        chapter_file = _chapter_file(resolved, number)
        entry: dict[str, Any] = {"stage": "pending", "summary_written": number in summarized}
        if chapter_file is not None:
            text = chapter_file.read_text(encoding="utf-8")
            entry["stage"] = "saved" if text.strip() else "truncated"
            entry["chars"] = len(text)
            entry["words"] = len(text.split())
        chapters[number] = entry

    gates = _default_gates()
    if (resolved / "outline.yml").is_file():
        gates["outline"] = "approved"
    if (resolved / "book-bible.md").is_file():
        gates["book_bible"] = "approved"
    if (resolved / "research-notes.md").is_file():
        gates["research_map"] = "approved"

    state = {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "revision": 0,
        "phase": 4 if chapters else 1,
        "book": {"title": title or "", "author": author or "", "target_words": 0},
        "gates": gates,
        "paths": {"project": str(resolved), "cc_config": None, "outline": None},
        "chapters": chapters,
        "intro": {"status": "complete" if (resolved / "introduction.md").is_file() else "pending"},
        "summary": {"status": "complete" if (resolved / "summary.md").is_file() else "pending"},
        "updated_at": _now_iso(),
    }
    return _persist(state, resolved)


def list_books() -> list[dict[str, Any]]:
    """Enumerate index records, flagging legacy and orphaned ones rather than fixing them."""
    if not INDEX_ROOT.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(INDEX_ROOT.glob("*.json")):
        row: dict[str, Any] = {"slug": path.stem, "status": "ok", "project_dir": None}
        try:
            record = _read_json(path)
        except StateError as exc:
            rows.append({**row, "status": "corrupt", "detail": str(exc).splitlines()[0]})
            continue
        project_dir = _project_dir_of(record)
        row["project_dir"] = str(project_dir) if project_dir else None
        project_state = None
        if project_dir and state_path(project_dir).is_file():
            try:
                project_state = _read_json(state_path(project_dir))
            except StateError:
                rows.append({**row, "status": "corrupt", "detail": f"{STATE_BASENAME} will not parse"})
                continue

        if project_state and int(project_state.get("schema_version") or 1) >= SCHEMA_VERSION:
            rows.append({**row, **_summarize(project_state)})
            continue
        if project_dir is None or not project_dir.is_dir():
            rows.append({**row, "status": "orphan", "detail": "project dir missing; migration blocked"})
            continue
        legacy = _freshest([None if _is_pointer(record) else record, project_state])
        if legacy is None:
            rows.append({**row, "status": "orphan", "detail": f"no {STATE_BASENAME} in the project dir"})
            continue
        rows.append({**row, **_summarize(legacy), "status": "legacy", "detail": "v1 record; migrates on next load"})
    return rows


def list_slugs() -> list[str]:
    return [row["slug"] for row in list_books()]


# ---------- PROGRESS.md projection ----------


def render_progress_md(state: dict[str, Any]) -> str:
    """Render the human-readable projection of canonical state."""
    title = (state.get("book") or {}).get("title") or "(untitled)"
    revision = int(state.get("revision") or 0)
    gates = {**_default_gates(), **(state.get("gates") or {})}
    chapters = state.get("chapters") or {}
    ordered = sorted(chapters.items(), key=lambda kv: _chapter_sort_key(kv[0]))
    saved = sum(1 for _, entry in ordered if entry.get("stage") == "saved")
    words = sum(int(entry.get("words") or 0) for _, entry in ordered)
    book_target = int(((state.get("book") or {}).get("target_words")) or 0)

    lines = [
        f"<!-- generated from {STATE_BASENAME} · revision {revision} · do not edit by hand -->",
        f"# Progress — {title}",
        "",
        f"- **slug**: `{state.get('slug', '?')}`",
        f"- **state**: `{STATE_BASENAME}` (canonical) · revision {revision} · "
        f"updated {state.get('updated_at') or '?'}",
        f"- **phase**: {state.get('phase', '?')}",
        "",
        "## Gates",
        f"- research map: {gates['research_map']}",
        f"- outline: {gates['outline']}",
        f"- book bible: {gates['book_bible']}",
        "",
        f"## Chapters — {saved}/{len(ordered)} saved · {words:,} words"
        + (f" of {book_target:,} target" if book_target else ""),
        "",
        "| # | stage | words | target | summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for number, entry in ordered:
        entry_words = entry.get("words")
        entry_target = entry.get("target_words")
        # Show the shortfall inline: a bare word count says nothing about whether
        # the chapter is finished, which is the whole reason short chapters slipped
        # through unnoticed. Scope, not a score — never a reason to pad.
        target_cell = "—"
        if entry_target:
            target_cell = format(int(entry_target), ",")
            if entry_words and int(entry_words) < int(entry_target) * 0.9:
                target_cell += f" (short {int(entry_target) - int(entry_words):,})"
        lines.append(
            f"| {number} | {entry.get('stage', 'pending')} | "
            f"{format(int(entry_words), ',') if entry_words else '—'} | "
            f"{target_cell} | "
            f"{'yes' if entry.get('summary_written') else 'no'} |"
        )
    if not ordered:
        lines.append("| — | no chapters yet | — | — | — |")

    lines += [
        "",
        "## Front & back matter",
        f"- introduction: {(state.get('intro') or {}).get('status', 'pending')}",
        f"- summary: {(state.get('summary') or {}).get('status', 'pending')}",
        "",
        f"_Regenerate with `python3 scripts/state.py render-progress {state.get('slug', '<slug>')}`._",
        "",
    ]
    return "\n".join(lines)


def write_progress(state: dict[str, Any]) -> Path:
    project_dir = _project_dir_of(state)
    if project_dir is None:
        raise StateError(f"cannot write {PROGRESS_BASENAME} without paths.project")
    target = progress_path(project_dir)
    _atomic_write_text(target, render_progress_md(state))
    return target


def progress_is_stale(state: dict[str, Any]) -> bool:
    """True when PROGRESS.md is missing, malformed, or behind canonical state."""
    project_dir = _project_dir_of(state)
    if project_dir is None:
        return True
    try:
        head = progress_path(project_dir).read_text(encoding="utf-8")[:400]
    except OSError:
        return True
    match = _PROGRESS_REVISION_RE.search(head)
    if match is None:
        return True
    return int(match.group(1)) != int(state.get("revision") or 0)


def ensure_progress(state: dict[str, Any]) -> bool:
    """Regenerate the projection when stale/missing/malformed. True if rewritten."""
    if not progress_is_stale(state):
        return False
    write_progress(state)
    return True


# ---------- Helpers ----------


def _chapter_sort_key(number: str) -> tuple[int, str]:
    return (int(number), "") if str(number).isdigit() else (10**9, str(number))


def _summarize(state: dict[str, Any]) -> dict[str, Any]:
    chapters = state.get("chapters") or {}
    saved = sum(
        1
        for entry in chapters.values()
        if isinstance(entry, dict) and (entry.get("stage") == "saved" or entry.get("status") == "complete")
    )
    return {
        "title": (state.get("book") or {}).get("title") or "(untitled)",
        "phase": state.get("phase", "?"),
        "updated_at": state.get("updated_at", "?"),
        "chapters_saved": saved,
        "chapters_total": len(chapters),
    }


def _outline_chapter_numbers(project_dir: Path) -> list[str]:
    """Pull chapter numbers out of outline.yml without a YAML dependency."""
    outline = project_dir / "outline.yml"
    if not outline.is_file():
        return []
    numbers = {
        match.group(1)
        for line in outline.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"\s*-?\s*number:\s*(\d+)\s*$", line))
    }
    return sorted(numbers, key=int)


def _chapter_file_numbers(project_dir: Path) -> list[str]:
    numbers = {
        match.group(1)
        for path in (project_dir / "chapters").glob("chapter_*")
        if (match := re.match(r"chapter_(\d+)\.(?:qmd|md)$", path.name))
    }
    return sorted(numbers, key=int)


_SUMMARY_HEADING = re.compile(r"\s*#+\s*Chapter\s+(\d+)\b", re.IGNORECASE)


def read_chapter_summaries(summaries: Path) -> list[dict[str, Any]]:
    """Parse chapter-summaries.md into `[{number, summary}]`, ordered by number.

    Each entry starts at a `## Chapter <N> — <title>` heading; its body is the
    text up to the next such heading, collapsed to one line. A chapter summarized
    twice keeps its later entry (the revision).
    """
    if not summaries.is_file():
        return []
    entries: dict[int, list[str]] = {}
    current: list[str] | None = None
    for line in summaries.read_text(encoding="utf-8").splitlines():
        if match := _SUMMARY_HEADING.match(line):
            current = entries[int(match.group(1))] = []
        elif current is not None:
            current.append(line)
    return [
        {"number": number, "summary": " ".join(" ".join(body).split())}
        for number, body in sorted(entries.items())
        if " ".join(body).strip()
    ]


def _summarized_chapter_numbers(project_dir: Path) -> set[str]:
    """Chapter numbers that already have an entry in chapter-summaries.md."""
    summaries = project_dir / "chapter-summaries.md"
    if not summaries.is_file():
        return set()
    return {
        match.group(1)
        for line in summaries.read_text(encoding="utf-8").splitlines()
        if (match := _SUMMARY_HEADING.match(line))
    }


def _select_artifact_entry(state: dict[str, Any], artifact: str) -> dict[str, Any]:
    if artifact == "intro":
        return state.setdefault("intro", {})
    if artifact == "summary":
        return state.setdefault("summary", {})
    if artifact.startswith("chapter/"):
        _, _, n = artifact.partition("/")
        if not n.isdigit() or int(n) < 1:
            raise StateError(f"invalid chapter selector {artifact!r}")
        chapters = state.setdefault("chapters", {})
        return chapters.setdefault(n, {})
    raise StateError(f"invalid artifact selector {artifact!r}; expected 'intro', 'summary', or 'chapter/<N>'")


def _coerce_value(raw: Any) -> Any:
    """CLI values arrive as strings — try to coerce to int/bool/null/json."""
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    if stripped.lower() in {"null", "none"}:
        return None
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    if stripped.lstrip("-").isdigit():
        return int(stripped)
    # Try JSON (for arrays/objects); otherwise treat as literal string.
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return raw


# ---------- CLI ----------


def _cmd_list(_args: argparse.Namespace) -> int:
    rows = list_books()
    if not rows:
        print("(no in-progress books)")
        return 0
    for row in rows:
        if row["status"] in {"orphan", "corrupt"}:
            print(f"{row['slug']}\t<{row['status']}: {row.get('detail', '')}>\t{row.get('project_dir') or ''}")
            continue
        flag = "\t(legacy v1 — migrates on next load)" if row["status"] == "legacy" else ""
        print(
            f"{row['slug']}\tphase={row.get('phase', '?')}\t"
            f"{row.get('chapters_saved', 0)}/{row.get('chapters_total', 0)} chapters\t"
            f"{row.get('updated_at', '?')}\t{row.get('title', '(untitled)')}{flag}"
        )
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    state = load_state(args.slug)
    if not args.no_repair and ensure_progress(state):
        print(f"(regenerated {PROGRESS_BASENAME})", file=sys.stderr)
    json.dump(state, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    state = init_state(
        args.slug,
        project_dir=args.project_dir,
        title=args.title,
        author=args.author,
        target_words=args.target_words,
        chapter_count=args.chapter_count,
    )
    print(f"initialized state for {args.slug!r} at {state_path(state['paths']['project'])}")
    return 0


def _cmd_set(args: argparse.Namespace) -> int:
    set_dotted(args.slug, args.path, args.value)
    print(f"set {args.path}")
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    set_gate(args.slug, args.gate, args.status)
    print(f"gate {args.gate}={args.status}")
    return 0


def _cmd_mark(args: argparse.Namespace) -> int:
    # Normalize the two possible argument shapes:
    #   mark <slug> chapter <N> <stage>
    #   mark <slug> intro <status>        # or summary
    if args.artifact == "chapter":
        if args.chapter_num is None or args.status is None:
            raise StateError("usage: mark <slug> chapter <N> <stage>")
        selector = f"chapter/{args.chapter_num}"
        status = args.status
    else:
        # intro | summary: positional after artifact is the status
        if args.chapter_num is None:
            raise StateError(f"usage: mark <slug> {args.artifact} <status>")
        selector = args.artifact
        status = args.chapter_num  # re-interpret the positional
    mark_artifact(
        args.slug,
        selector,
        status,
        chars=args.chars,
        words=args.words,
        summary_written=True if args.summary_written else None,
        target_words=args.target_words,
        bump_revision=args.bump_revision,
    )
    print(f"marked {selector}={status}")
    return 0


def _cmd_render_progress(args: argparse.Namespace) -> int:
    print(f"wrote {write_progress(load_state(args.slug))}")
    return 0


def _cmd_rebuild(args: argparse.Namespace) -> int:
    project_dir = args.project_dir
    if project_dir is None:
        try:
            project_dir = _project_dir_of(_read_json(index_path(args.slug)))
        except StateError:
            project_dir = None
    if project_dir is None:
        raise StateError(f"cannot infer a project dir for {args.slug!r}; pass --project-dir")
    state = rebuild_from_artifacts(args.slug, project_dir, title=args.title, author=args.author)
    print(f"rebuilt state for {args.slug!r} from artifacts in {project_dir} ({len(state['chapters'])} chapters)")
    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    existed = delete_state(args.slug, purge=args.purge)
    print("deleted" if existed else "no such slug")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="state", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list in-progress books").set_defaults(func=_cmd_list)

    sp_show = sub.add_parser("show", help="print canonical state JSON (repairs PROGRESS.md)")
    sp_show.add_argument("slug")
    sp_show.add_argument("--no-repair", action="store_true", help="do not regenerate PROGRESS.md")
    sp_show.set_defaults(func=_cmd_show)

    sp_init = sub.add_parser("init", help="create a new state record")
    sp_init.add_argument("slug")
    sp_init.add_argument("--project-dir", default=None, help="defaults to ~/Books/<slug>")
    sp_init.add_argument("--title", default=None)
    sp_init.add_argument("--author", default=None)
    sp_init.add_argument("--target-words", type=int, default=None)
    sp_init.add_argument("--chapter-count", type=int, default=None)
    sp_init.set_defaults(func=_cmd_init)

    sp_set = sub.add_parser("set", help="set a nested field by dotted path")
    sp_set.add_argument("slug")
    sp_set.add_argument("path", help="e.g. book.title or paths.project")
    sp_set.add_argument("value")
    sp_set.set_defaults(func=_cmd_set)

    sp_gate = sub.add_parser("gate", help="record a checkpoint gate's status")
    sp_gate.add_argument("slug")
    sp_gate.add_argument("gate", choices=sorted(VALID_GATES))
    sp_gate.add_argument("status", choices=sorted(VALID_GATE_STATUSES))
    sp_gate.set_defaults(func=_cmd_gate)

    sp_mark = sub.add_parser("mark", help="update an artifact's stage/status")
    sp_mark.add_argument("slug")
    sp_mark.add_argument("artifact", choices=["chapter", "intro", "summary"])
    sp_mark.add_argument("chapter_num", nargs="?", help="chapter number OR status (for intro/summary)")
    sp_mark.add_argument("status", nargs="?", help="stage (when artifact is 'chapter')")
    sp_mark.add_argument("--chars", type=int, default=None)
    sp_mark.add_argument("--words", type=int, default=None)
    sp_mark.add_argument("--summary-written", action="store_true", help="chapter-summaries.md entry appended")
    sp_mark.add_argument(
        "--target-words",
        type=int,
        default=None,
        help="this chapter's summed section-beat word_target (scope, not a floor)",
    )
    sp_mark.add_argument("--bump-revision", action="store_true")
    sp_mark.set_defaults(func=_cmd_mark)

    sp_prog = sub.add_parser("render-progress", help="regenerate PROGRESS.md from canonical state")
    sp_prog.add_argument("slug")
    sp_prog.set_defaults(func=_cmd_render_progress)

    sp_rebuild = sub.add_parser("rebuild", help="reconstruct state from the project's artifacts")
    sp_rebuild.add_argument("slug")
    sp_rebuild.add_argument("--project-dir", default=None)
    sp_rebuild.add_argument("--title", default=None)
    sp_rebuild.add_argument("--author", default=None)
    sp_rebuild.set_defaults(func=_cmd_rebuild)

    sp_del = sub.add_parser("delete", help="remove the index record")
    sp_del.add_argument("slug")
    sp_del.add_argument("--purge", action="store_true", help="also delete the project's book-state.json/PROGRESS.md")
    sp_del.set_defaults(func=_cmd_delete)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.func(args)
    except StateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
