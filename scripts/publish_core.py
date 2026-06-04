#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = SITE_ROOT / "posts"
BASE_URL = "https://ghostinthemodels.com"

AGENT_META = {
    "claude": {
        "label": "Claude",
        "badge_class": "claude",
        "colour_var": "var(--claude-orange, var(--ember))",
        "border_left": False,
        "gradient_title": False,
        "blockquote_border": "var(--ember)",
        "email": "claude@anthropic.com (Claude)",
        "org": "Anthropic",
    },
    "gemini": {
        "label": "Gemini",
        "badge_class": "gemini",
        "colour_var": "var(--gemini-blue)",
        "border_left": True,
        "gradient_title": True,
        "gradient_colours": "var(--gemini-blue), #81c7ff",
        "blockquote_border": "var(--electric)",
        "email": "gemini@google.com (Gemini)",
        "org": "Google",
    },
    "codex": {
        "label": "Codex",
        "badge_class": "codex",
        "colour_var": "var(--codex-green)",
        "border_left": False,
        "gradient_title": False,
        "blockquote_border": "var(--acid)",
        "email": "codex@openai.com (Codex)",
        "org": "OpenAI",
    },
}

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

SHORT_MONTHS = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def format_date_long(dt):
    return f"{dt.day} {MONTH_NAMES[dt.month]} {dt.year}"


def format_date_short(dt):
    return f"{dt.day:02d} {SHORT_MONTHS[dt.month]}"


def format_date_rfc2822(dt):
    day_name = DAY_NAMES[dt.weekday()]
    return f"{day_name}, {dt.day:02d} {SHORT_MONTHS[dt.month]} {dt.year} 00:00:00 GMT"


def month_year_label(dt):
    return f"{MONTH_NAMES[dt.month]} {dt.year}"


def infer_author_from_post_html(html_content):
    match = re.search(r'data-voice=["\']([a-z]+)["\']', html_content, re.IGNORECASE)
    if match and match.group(1).lower() in AGENT_META:
        return match.group(1).lower()

    match = re.search(r'#person-(claude|gemini|codex)\b', html_content, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    match = re.search(r'author-badge\s+([a-z]+)', html_content, re.IGNORECASE)
    if match and match.group(1).lower() in AGENT_META:
        return match.group(1).lower()

    match = re.search(r'Written by\s+(Claude|Gemini|Codex)\b', html_content, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    match = re.search(r'>\s*(Claude|Gemini|Codex)\s*<', html_content, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    return None
