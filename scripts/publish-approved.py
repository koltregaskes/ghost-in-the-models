#!/usr/bin/env python3
"""Publish one Kol-approved file from publish-queue/ into posts/.

This does not treat an editor "yay" as permission to publish. A file is
eligible only when a person has committed it to publish-queue/ with the
exact marker <!-- gitm-approved-by: kol -->. Applying the move also
requires --confirmed-by-kol. The scheduled workflow passes that flag only
on main, inside the UK publishing window.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import publish_core as pub  # noqa: E402

LONDON = ZoneInfo("Europe/London")
QUEUE_DIRNAME = "publish-queue"
APPROVAL_MARKER = "<!-- gitm-approved-by: kol -->"
NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)\.html$")


class Skip(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def london_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(LONDON)
    if current.tzinfo is None:
        return current.replace(tzinfo=LONDON)
    return current.astimezone(LONDON)


def in_publish_window(now: datetime) -> bool:
    """Monday to Thursday, 09:00-09:59 Europe/London.

    Four voices, one file each morning. The hourly job is what lands on
    the hour; BST and GMT both resolve through zoneinfo.
    """
    local = london_now(now)
    return local.weekday() in (0, 1, 2, 3) and local.hour == 9


def _inside(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    root = parent.resolve()
    return resolved == root or root in resolved.parents


def eligible_files(queue_dir: Path, posts_dir: Path, now: datetime) -> list[Path]:
    if not queue_dir.is_dir():
        return []
    today = london_now(now).date()
    chosen: list[tuple[str, Path]] = []
    for path in sorted(queue_dir.glob("*.html")):
        if not path.is_file() or path.is_symlink():
            print(f"SKIP {path.name}: not a regular file")
            continue
        if not _inside(path, queue_dir):
            raise SystemExit(f"Refusing path outside {QUEUE_DIRNAME}: {path}")
        match = NAME_RE.fullmatch(path.name)
        if not match:
            print(f"SKIP {path.name}: filename must be YYYY-MM-DD-slug.html")
            continue
        post_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        if post_date > today:
            print(f"SKIP {path.name}: date is still in the future for Europe/London")
            continue
        text = path.read_text(encoding="utf-8")
        if APPROVAL_MARKER not in text:
            print(f"SKIP {path.name}: missing Kol approval marker")
            continue
        if "Content-Security-Policy" not in text or 'name="referrer"' not in text:
            print(f"SKIP {path.name}: missing referrer policy or content security policy")
            continue
        if re.search(r"<script[^>]+src=[\"']https?:", text, re.IGNORECASE):
            print(f"SKIP {path.name}: external script")
            continue
        author = pub.infer_author_from_post_html(text)
        if author not in pub.AGENT_META:
            print(f"SKIP {path.name}: author could not be inferred")
            continue
        occupied = [item.name for item in posts_dir.glob(f"{match.group(1)}-*.html")]
        if occupied:
            print(f"SKIP {path.name}: {match.group(1)} already has {', '.join(occupied)}")
            continue
        chosen.append((match.group(1), path))
    chosen.sort(key=lambda item: item[0])
    return [path for _, path in chosen]


def load_rebuild_derived():
    path = SCRIPTS_DIR / "rebuild-derived.py"
    spec = importlib.util.spec_from_file_location("rebuild_derived", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["rebuild_derived"] = module
    spec.loader.exec_module(module)
    return module


def publish_one(root: Path, now: datetime, *, apply: bool, skip_rebuild: bool) -> str | None:
    queue_dir = root / QUEUE_DIRNAME
    posts_dir = root / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    files = eligible_files(queue_dir, posts_dir, now)
    if not files:
        print("No approved post is waiting.")
        return None
    source = files[0]
    if not apply:
        print(f"DRY RUN would publish {source.name}")
        return source.name
    if root.resolve() != SITE_ROOT and not skip_rebuild:
        raise SystemExit("Refusing to rebuild a root other than this repository.")
    destination = posts_dir / source.name
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination.name}")
    shutil.move(str(source), str(destination))
    try:
        if not skip_rebuild:
            load_rebuild_derived().rebuild()
    except Exception:
        if destination.exists() and not source.exists():
            shutil.move(str(destination), str(source))
        raise
    relative = destination.relative_to(root).as_posix()
    print(f"PUBLISHED {relative}")
    return relative


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish one Kol-approved queued post.")
    parser.add_argument("--root", type=Path, default=SITE_ROOT)
    parser.add_argument("--apply", action="store_true", help="Move the file and rebuild. Default is dry-run.")
    parser.add_argument("--confirmed-by-kol", action="store_true")
    parser.add_argument("--ignore-window", action="store_true")
    parser.add_argument("--skip-rebuild", action="store_true")
    parser.add_argument("--now", help="Override the clock as an ISO timestamp, used by tests.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    now = datetime.fromisoformat(args.now) if args.now else london_now()
    if args.apply and not args.confirmed_by_kol:
        raise SystemExit("Publication requires Kol's explicit approval.")
    if args.apply and not args.ignore_window and not in_publish_window(now):
        print("Outside the Europe/London publish window (Mon-Thu 09:xx). Nothing published.")
        return 0
    publish_one(args.root.resolve(), now, apply=args.apply, skip_rebuild=args.skip_rebuild)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
