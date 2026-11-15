#!/usr/bin/env python3
"""Dry-run checks for the approved-post publisher and homepage guard."""
from __future__ import annotations

import importlib.util
import hashlib
import json
from approval_test_support import Fixture
from approval_trust import trusted_signers
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
    assert rebuild_derived.homepage_is_protected('<section class="gitm-tetraptych"></section>')
    assert not rebuild_derived.homepage_is_protected("<h1>Generated homepage</h1>")
    live_index = (ROOT / "index.html").read_text(encoding="utf-8")
    if "gitm-tetraptych" not in live_index or not rebuild_derived.homepage_is_protected(live_index):
        raise SystemExit("Live index.html no longer contains the protected four-voice homepage.")
    if not publisher.load_rebuild_derived().homepage_is_protected(live_index):
        raise SystemExit("Publisher could not load the homepage guard.")
    # Longer name first in the pattern, so both the old byline and the current one resolve.
    assert publisher.pub.infer_author_from_post_html("Written by Grok Bot for Ghost") == "grok"
    assert publisher.pub.infer_author_from_post_html("Written by Grok for Ghost") == "grok"
    assert publisher.pub.infer_author_from_post_html(">Grok<") == "grok"

    tuesday = datetime.fromisoformat("2026-10-27T09:20:00+00:00")
    assert publisher.in_publish_window(tuesday)
    # 26 Oct 2026 is the first Monday after the clocks change. 09:20 UTC is 09:20 in London.
    assert publisher.in_publish_window(datetime.fromisoformat("2026-10-26T09:20:00+00:00"))
    assert not publisher.in_publish_window(datetime.fromisoformat("2026-10-26T08:20:00+00:00"))
    # 20 Oct 2026 is still BST (UTC+1). 08:20 UTC is 09:20 in London.
    assert publisher.in_publish_window(datetime.fromisoformat("2026-10-20T08:20:00+00:00"))
    assert not publisher.in_publish_window(datetime.fromisoformat("2026-10-20T09:20:00+00:00"))
    # Saturday is outside the four-morning week.
    assert not publisher.in_publish_window(datetime.fromisoformat("2026-10-24T09:20:00+00:00"))
    assert publisher.in_publish_window(datetime.fromisoformat("2026-10-29T09:20:00+00:00"))
    assert not publisher.in_publish_window(datetime.fromisoformat("2026-10-30T09:20:00+00:00"))

    with tempfile.TemporaryDirectory() as raw:
        fixture = Fixture(Path(raw))
        root = fixture.root
        queue, posts = root / "publish-queue", root / "posts"
        ready = queue / "2026-10-20-grok.html"
        ready.write_text(load_sample("ready", ""), encoding="utf-8", newline="\n")
        future = queue / "2099-01-01-grok.html"
        future.write_text(load_sample("future", ""), encoding="utf-8", newline="\n")
        taken = posts / "2026-10-22-claude.html"
        taken.write_text(load_sample("taken", ""), encoding="utf-8", newline="\n")
        collision = queue / "2026-10-22-grok.html"
        collision.write_text(load_sample("collision", ""), encoding="utf-8", newline="\n")
        for item in [ready, future, taken, collision]:
            fixture.record(item)
        signers = trusted_signers(root, fixture.pin)
        names = [path.name for path in publisher.eligible_files(queue, posts, tuesday, signers)]
        assert names == [ready.name], names
        publisher.publish_one(root, tuesday, apply=False, skip_rebuild=True, signers=signers)
        assert ready.exists(), "Dry run moved the queued file"
        publisher.publish_one(root, tuesday, apply=True, skip_rebuild=True, signers=signers)
        assert not ready.exists() and (posts / ready.name).exists()
        assert future.exists(), "Future article disappeared"

    print("publish-approved dry run passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
