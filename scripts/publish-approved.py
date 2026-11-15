#!/usr/bin/env python3
"""Prepare exact Chief-signed bytes; never infer approval from a GitHub account."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
SCRIPTS_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from approval import approved_record, verify_public
from approval_trust import ApprovalError, regular_bytes, trusted_signers
import importlib.util
import re
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import publish_core as pub  # noqa: E402


QUEUE_DIRNAME = "publish-queue"
NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)\.html$")


class Skip(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def london_now(value: datetime | None = None) -> datetime:
    LONDON = ZoneInfo("Europe/London")
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


def eligible_files(queue_dir: Path, posts_dir: Path, now: datetime, signers: bytes) -> list[Path]:
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
        approved_record(path, queue_dir.parent, signers)
        post_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        if post_date > today:
            print(f"SKIP {path.name}: date is still in the future for Europe/London")
            continue
        text = path.read_text(encoding="utf-8")
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


def publish_one(root: Path, now: datetime, *, apply: bool, skip_rebuild: bool, signers: bytes) -> str | None:
    queue_dir = root / QUEUE_DIRNAME
    posts_dir = root / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    files = eligible_files(queue_dir, posts_dir, now, signers)
    if not files:
        print("No approved post is waiting.")
        return None
    source = files[0]
    if not apply:
        print(f"DRY RUN would publish {source.name}")
        return source.name
    destination = posts_dir / source.name
    if destination.exists():
        raise SystemExit(f"Destination already exists: {destination.name}")
    approved_bytes = regular_bytes(source, root)
    approved_record(source, root, signers, content=approved_bytes)
    shutil.move(str(source), str(destination))
    try:
        approved_record(destination, root, signers)
        if not skip_rebuild:
            rebuild = load_rebuild_derived()
            # Run pinned generator code against the explicit candidate data.
            rebuild.SITE_ROOT = root
            rebuild.POSTS_DIR = root / "posts"
            rebuild.rebuild(update_posts=False)
        # Check again after moving/rebuilding. Never overwrite a detected edit
        # with old bytes and silently claim that the approved article survived.
        if regular_bytes(destination, root) != approved_bytes:
            raise ApprovalError("Article changed during preparation")
        approved_record(destination, root, signers)
    except Exception:
        if destination.exists() and not source.exists():
            shutil.move(str(destination), str(source))
        raise
    relative = destination.relative_to(root).as_posix()
    print(f"PREPARED {relative} (local candidate, not a public deployment)")
    return relative


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish one Kol-approved queued post.")
    parser.add_argument("--root", type=Path, default=SITE_ROOT)
    parser.add_argument("--apply", action="store_true", help="Move the file and rebuild. Default is dry-run.")
    parser.add_argument("--trust-root-sha256", required=True, help="Externally pinned SHA-256 of the initial PUBLIC allowed_signers file.")
    parser.add_argument("--ignore-window", action="store_true")
    parser.add_argument("--skip-rebuild", action="store_true")
    parser.add_argument("--now", help="Override the clock as an ISO timestamp, used by tests.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    signers = trusted_signers(args.root.resolve(), args.trust_root_sha256)
    verify_public(args.root.resolve(), signers)
    now = datetime.fromisoformat(args.now) if args.now else london_now()
    if args.apply and not args.ignore_window and not in_publish_window(now):
        print("Outside the Europe/London publish window (Mon-Thu 09:xx). Nothing published.")
        return 0
    publish_one(args.root.resolve(), now, apply=args.apply, skip_rebuild=args.skip_rebuild, signers=signers)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApprovalError as exc:
        print(f"APPROVAL REJECTED: {exc}", file=sys.stderr)
        raise SystemExit(1)
