#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
HTML_PATHS = (
    sorted(SITE_ROOT.glob("*.html"))
    + sorted((SITE_ROOT / "posts").glob("*.html"))
    + sorted((SITE_ROOT / "drafts").glob("*.html"))
)

REFERRER_META = '<meta name="referrer" content="strict-origin-when-cross-origin">'
CSP_META = (
    '<meta http-equiv="Content-Security-Policy" '
    'content="default-src \'self\'; img-src \'self\' data: https:; media-src \'self\' https:; '
    'style-src \'self\' \'unsafe-inline\' https://fonts.googleapis.com; '
    'font-src https://fonts.gstatic.com data:; script-src \'self\'; connect-src \'self\'; '
    'base-uri \'self\'; form-action \'self\'; frame-ancestors \'none\'">'
)
STANDARD_ICON = (
    '<link rel="icon" href="data:image/svg+xml,'
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' rx='6' fill='%230b0f1a'/>"
    "<text x='16' y='22' text-anchor='middle' font-family='monospace' font-size='16' font-weight='bold' fill='%23f6c36a'>GM</text>"
    '</svg>">'
)
GSAP_TAG_RE = re.compile(
    r'\s*<script src="https://cdnjs\.cloudflare\.com/ajax/libs/gsap/3\.12\.5/(?:gsap|ScrollTrigger)\.min\.js"></script>',
    re.IGNORECASE,
)
ICON_RE = re.compile(r'<link rel="icon" href="data:image/svg\+xml,[^"]+">', re.IGNORECASE)
TIME_TAG_RE = re.compile(r'(<time[^>]+datetime=")(\d{4}-\d{2}-\d{2})(">(.*?)</time>)', re.IGNORECASE | re.DOTALL)


def format_long_date(date_text: str) -> str:
    dt = datetime.strptime(date_text, "%Y-%m-%d")
    return f"{dt.day} {dt.strftime('%B %Y')}"


def ensure_meta_tag(head: str, tag: str, *, after: str) -> str:
    if tag in head:
        return head
    return head.replace(after, after + "\n    " + tag, 1)


def harden_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original

    updated = GSAP_TAG_RE.sub("", updated)

    if "<head>" in updated:
        head_end = updated.find("</head>")
        head = updated[:head_end]
        if '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in head:
            head = ensure_meta_tag(
                head,
                REFERRER_META,
                after='<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            )
            head = ensure_meta_tag(head, CSP_META, after=REFERRER_META)
        if ICON_RE.search(head):
            head = ICON_RE.sub(STANDARD_ICON, head, count=1)
        updated = head + updated[head_end:]

    match = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    if match:
        target_date = match.group(1)

        def replace_time(match_obj: re.Match[str]) -> str:
            return match_obj.group(1) + target_date + match_obj.group(3).replace(match_obj.group(4), format_long_date(target_date))

        updated = TIME_TAG_RE.sub(replace_time, updated, count=1)

    if updated == original:
        return False

    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for path in HTML_PATHS:
        if harden_file(path):
            changed += 1
            print(path.relative_to(SITE_ROOT).as_posix())

    print(f"hardened_files {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
