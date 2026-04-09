#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

SITE_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = SITE_ROOT / "posts"
DRAFTS_DIR = SITE_ROOT / "drafts"
POLICY_PATH = SITE_ROOT / ".agents" / "site-policy.json"
TEXT_SUFFIXES = {
    ".html",
    ".xml",
    ".txt",
    ".md",
    ".js",
    ".css",
    ".ps1",
    ".bat",
    ".json",
    ".yml",
    ".yaml",
    ".py",
}
MOJIBAKE_PATTERNS = (
    "Ã",
    "â€",
    "Â",
    "\ufffd",
)
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
TIME_DATETIME_RE = re.compile(r'<time[^>]+datetime="(\d{4}-\d{2}-\d{2})"', re.IGNORECASE)
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src="([^"]+)"', re.IGNORECASE)


@dataclass
class AuditMessage:
    level: str
    code: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tracked_text_files() -> list[Path]:
    raw = subprocess.check_output(
        ["git", "-C", str(SITE_ROOT), "ls-files"],
        encoding="utf-8",
        text=True,
    )
    files = []
    for rel in raw.splitlines():
        path = SITE_ROOT / rel
        if path.suffix.lower() in TEXT_SUFFIXES and path.is_file():
            files.append(path)
    return files


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        return {
            "legacy_date_exceptions": {},
            "draft_policy": {"max_stale_days": 3},
            "automation": {},
        }
    return json.loads(read_text(POLICY_PATH))


def normalize_rel(path: Path) -> str:
    return path.relative_to(SITE_ROOT).as_posix()


def add_grouped_duplicate_messages(
    bucket: dict[str, list[str]],
    *,
    code: str,
    label: str,
    level: str,
    messages: list[AuditMessage],
) -> None:
    for date, files in sorted(bucket.items()):
        joined = ", ".join(sorted(files))
        messages.append(
            AuditMessage(level, code, f"{label} for {date}: {joined}")
        )


def audit_dates(policy: dict, messages: list[AuditMessage]) -> None:
    legacy_exceptions = {
        date: sorted(values)
        for date, values in policy.get("legacy_date_exceptions", {}).items()
    }

    posts_by_date: dict[str, list[str]] = defaultdict(list)
    for path in sorted(POSTS_DIR.glob("*.html")):
        match = DATE_RE.match(path.name)
        if not match:
            continue
        posts_by_date[match.group(1)].append(normalize_rel(path))

        raw = read_text(path)
        time_match = TIME_DATETIME_RE.search(raw)
        if time_match and time_match.group(1) != match.group(1):
            messages.append(
                AuditMessage(
                    "error",
                    "post_date_mismatch",
                    f"{normalize_rel(path)} filename date {match.group(1)} does not match <time datetime> {time_match.group(1)}",
                )
            )

    unapproved_duplicates: dict[str, list[str]] = {}
    for date, files in posts_by_date.items():
        if len(files) <= 1:
            continue
        if sorted(files) == legacy_exceptions.get(date, []):
            messages.append(
                AuditMessage(
                    "warning",
                    "legacy_duplicate_date",
                    f"Legacy duplicate published date retained for {date}: {', '.join(sorted(files))}",
                )
            )
            continue
        unapproved_duplicates[date] = files

    add_grouped_duplicate_messages(
        unapproved_duplicates,
        code="duplicate_published_date",
        label="Multiple published posts share a date",
        level="error",
        messages=messages,
    )

    draft_dates: dict[str, list[str]] = defaultdict(list)
    max_stale_days = int(policy.get("draft_policy", {}).get("max_stale_days", 3))
    now = datetime.now()
    for path in sorted(DRAFTS_DIR.glob("*.html")):
        match = DATE_RE.match(path.name)
        if not match:
            continue
        draft_date = match.group(1)
        draft_dates[draft_date].append(normalize_rel(path))

        raw = read_text(path)
        time_match = TIME_DATETIME_RE.search(raw)
        if time_match and time_match.group(1) != draft_date:
            messages.append(
                AuditMessage(
                    "error",
                    "draft_date_mismatch",
                    f"{normalize_rel(path)} filename date {draft_date} does not match <time datetime> {time_match.group(1)}",
                )
            )

        age_days = (now - datetime.fromtimestamp(path.stat().st_mtime)).days
        if age_days >= max_stale_days:
            messages.append(
                AuditMessage(
                    "warning",
                    "stale_draft",
                    f"{normalize_rel(path)} is {age_days} day(s) old and still pending review",
                )
            )

    duplicate_draft_dates = {date: files for date, files in draft_dates.items() if len(files) > 1}
    add_grouped_duplicate_messages(
        duplicate_draft_dates,
        code="duplicate_draft_date",
        label="Multiple drafts share a date",
        level="error",
        messages=messages,
    )

    published_dates = set(posts_by_date)
    for date, files in sorted(draft_dates.items()):
        if date not in published_dates:
            continue
        messages.append(
            AuditMessage(
                "error",
                "draft_published_conflict",
                f"Draft date {date} collides with a published post: {', '.join(sorted(files))}",
            )
        )


def audit_text_integrity(messages: list[AuditMessage]) -> None:
    for path in tracked_text_files():
        raw = path.read_bytes()
        rel = normalize_rel(path)
        if raw.startswith(b"\xef\xbb\xbf"):
            messages.append(
                AuditMessage("error", "bom_detected", f"UTF-8 BOM present in {rel}")
            )

        text = raw.decode("utf-8", errors="replace")
        for marker in MOJIBAKE_PATTERNS:
            if marker in text:
                messages.append(
                    AuditMessage(
                        "error",
                        "mojibake_detected",
                        f"Suspicious encoding artefact '{marker}' found in {rel}",
                    )
                )
                break


def audit_html_security(messages: list[AuditMessage]) -> None:
    html_files = sorted(SITE_ROOT.glob("*.html")) + sorted(POSTS_DIR.glob("*.html")) + sorted(DRAFTS_DIR.glob("*.html"))

    for path in html_files:
        rel = normalize_rel(path)
        raw = read_text(path)

        if '<meta name="referrer" content="strict-origin-when-cross-origin">' not in raw:
            messages.append(
                AuditMessage(
                    "error",
                    "missing_referrer_policy",
                    f"{rel} is missing the referrer policy meta tag",
                )
            )

        if '<meta http-equiv="Content-Security-Policy"' not in raw:
            messages.append(
                AuditMessage(
                    "error",
                    "missing_csp_meta",
                    f"{rel} is missing the Content-Security-Policy meta tag",
                )
            )

        for src in SCRIPT_SRC_RE.findall(raw):
            lowered = src.lower()
            if lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("//"):
                messages.append(
                    AuditMessage(
                        "error",
                        "external_script",
                        f"{rel} loads external script {src}",
                    )
                )

        if "import mermaid from 'https://cdn.jsdelivr.net/" in raw:
            messages.append(
                AuditMessage(
                    "error",
                    "external_mermaid_import",
                    f"{rel} imports Mermaid from a CDN",
                )
            )


def summarize(messages: Iterable[AuditMessage]) -> tuple[list[AuditMessage], list[AuditMessage]]:
    warnings = [message for message in messages if message.level == "warning"]
    errors = [message for message in messages if message.level == "error"]
    return warnings, errors


def main() -> int:
    policy = load_policy()
    messages: list[AuditMessage] = []
    audit_dates(policy, messages)
    audit_text_integrity(messages)
    audit_html_security(messages)

    warnings, errors = summarize(messages)
    for message in warnings:
        print(f"WARNING [{message.code}] {message.message}")
    for message in errors:
        print(f"ERROR   [{message.code}] {message.message}")

    payload = {
        "warnings": [message.__dict__ for message in warnings],
        "errors": [message.__dict__ for message in errors],
        "warning_count": len(warnings),
        "error_count": len(errors),
    }
    print(json.dumps(payload, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
