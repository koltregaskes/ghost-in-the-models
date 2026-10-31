#!/usr/bin/env python3
"""Check links in tracked HTML files.

Local references fail the run. External references are checked only when
--external is set, and only a confirmed 404 or 410 fails the run.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
REF_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"', re.IGNORECASE)
SKIP_EXTERNAL_PREFIXES = ("data:", "mailto:", "tel:", "javascript:", "#")
# <link rel="preconnect"> and rel="dns-prefetch" name an origin to connect to early, not a
# document. Requesting the bare origin (https://fonts.googleapis.com) returns 404, so these
# resource hints are not links and are left out of the check.
RESOURCE_HINT_RE = re.compile(
    r"<link\b[^>]*\brel\s*=\s*\"[^\"]*\b(?:preconnect|dns-prefetch)\b[^\"]*\"[^>]*>", re.IGNORECASE
)


def tracked_html() -> list[Path]:
    raw = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "*.html"], text=True)
    return [ROOT / line for line in raw.splitlines() if line.endswith(".html")]


def local_target(source: Path, ref: str) -> Path | None:
    if ref.startswith(("http://", "https://")) or ref.startswith(SKIP_EXTERNAL_PREFIXES):
        return None
    clean = ref.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return None
    if clean.startswith("/ghost-in-the-models/"):
        clean = clean[len("/ghost-in-the-models/"):]
    elif clean.startswith("/"):
        clean = clean.lstrip("/")
        return ROOT / clean
    return (source.parent / clean).resolve()


def check_external(url: str) -> str | None:
    request = Request(url, method="GET", headers={"User-Agent": "GhostInTheModelsLinkCheck/1.0"})
    try:
        with urlopen(request, timeout=12) as response:
            if response.status in (404, 410):
                return f"{response.status} {url}"
    except HTTPError as exc:
        if exc.code in (404, 410):
            return f"{exc.code} {url}"
    except (URLError, TimeoutError, OSError):
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    external: set[str] = set()
    files = tracked_html()
    for path in files:
        raw = RESOURCE_HINT_RE.sub("", path.read_text(encoding="utf-8", errors="ignore"))
        for match in REF_RE.finditer(raw):
            ref = match.group(1)
            if ref.startswith(("http://", "https://")):
                external.add(ref.split("#", 1)[0])
                continue
            target = local_target(path, ref)
            if target is not None and not target.exists():
                errors.append(f"Broken reference in {path.relative_to(ROOT)}: {ref}")

    if args.external and external:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(check_external, url) for url in sorted(external)]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    errors.append(f"Broken external link: {result}")

    if errors:
        print("\n".join(sorted(set(errors))))
        return 1
    print(f"Link check passed across {len(files)} HTML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
