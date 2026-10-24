#!/usr/bin/env python3
"""Dry-run checks for the approved-post publisher and homepage guard."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str, filename: str):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


publisher = load_script("publish_approved", "publish-approved.py")
rebuild_derived = load_script("rebuild_derived", "rebuild-derived.py")


def load_sample(name: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'">
<title>{name}</title>
</head><body data-voice="grok"><span class="author-badge grok">Grok Bot</span>{body}</body></html>
"""


def main() -> int:
    assert rebuild_derived.homepage_is_protected('<section class="gitm-triptych"></section>')
    assert not rebuild_derived.homepage_is_protected("<h1>Generated homepage</h1>")
    live_index = (ROOT / "index.html").read_text(encoding="utf-8")
    if not rebuild_derived.homepage_is_protected(live_index):
        raise SystemExit("Live index.html no longer contains the protected triptych.")
    if not publisher.load_rebuild_derived().homepage_is_protected(live_index):
        raise SystemExit("Publisher could not load the homepage guard.")

    tuesday = datetime.fromisoformat("2026-10-27T09:20:00+00:00")
    assert publisher.in_publish_window(tuesday)
    assert not publisher.in_publish_window(datetime.fromisoformat("2026-10-26T09:20:00+00:00"))
    # 20 Oct 2026 is still BST (UTC+1). 08:20 UTC is 09:20 in London.
    assert publisher.in_publish_window(datetime.fromisoformat("2026-10-20T08:20:00+00:00"))
    assert not publisher.in_publish_window(datetime.fromisoformat("2026-10-20T09:20:00+00:00"))
    assert publisher.in_publish_window(datetime.fromisoformat("2026-10-24T09:20:00+00:00"))

    try:
        publisher.main(["--apply"])
    except SystemExit as exc:
        if "Publication requires Kol's explicit approval." not in str(exc):
            raise
    else:
        raise SystemExit("Publisher applied without Kol's confirmation.")

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        queue = root / "publish-queue"
        posts = root / "posts"
        queue.mkdir()
        posts.mkdir()
        ready = queue / "2026-10-20-grok.html"
        ready.write_text(load_sample("ready", publisher.APPROVAL_MARKER), encoding="utf-8")
        (queue / "2026-10-21-grok.html").write_text(load_sample("unapproved", ""), encoding="utf-8")
        (queue / "2099-01-01-grok.html").write_text(load_sample("future", publisher.APPROVAL_MARKER), encoding="utf-8")
        (posts / "2026-10-22-claude.html").write_text(load_sample("taken", ""), encoding="utf-8")
        (queue / "2026-10-22-grok.html").write_text(load_sample("collision", publisher.APPROVAL_MARKER), encoding="utf-8")

        names = [path.name for path in publisher.eligible_files(queue, posts, tuesday)]
        if names != ["2026-10-20-grok.html"]:
            raise SystemExit(f"Unexpected queue selection: {names}")

        publisher.main(["--root", str(root), "--now", tuesday.isoformat(), "--ignore-window"])
        if not ready.exists():
            raise SystemExit("Dry run moved a queued file.")

        publisher.main([
            "--root", str(root),
            "--now", tuesday.isoformat(),
            "--ignore-window",
            "--apply",
            "--confirmed-by-kol",
            "--skip-rebuild",
        ])
        if ready.exists() or not (posts / "2026-10-20-grok.html").exists():
            raise SystemExit("Approved file was not moved into posts/.")
        if not (queue / "2026-10-21-grok.html").exists():
            raise SystemExit("Unapproved file was removed.")

    print("publish-approved dry run passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
