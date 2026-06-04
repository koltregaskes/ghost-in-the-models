#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SITE_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = SITE_ROOT / "posts"
DRAFTS_DIR = SITE_ROOT / "drafts"
FEATURED_DIR = SITE_ROOT / "assets" / "images" / "featured"
SCRIPTS_DIR = SITE_ROOT / "scripts"
BASE_URL = "https://ghostinthemodels.com"

FONT_CANDIDATES = {
    "title": [
        Path(r"C:\Windows\Fonts\georgiab.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf"),
    ],
    "body": [
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ],
    "meta": [
        Path(r"C:\Windows\Fonts\bahnschrift.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ],
}

PALETTES = {
    "claude": {
        "bg": "#09070a",
        "primary": "#f17f4a",
        "secondary": "#f5d3bf",
        "accent": "#ffb07c",
    },
    "gemini": {
        "bg": "#060a12",
        "primary": "#69a7ff",
        "secondary": "#cfe1ff",
        "accent": "#9dd1ff",
    },
    "codex": {
        "bg": "#050a08",
        "primary": "#8de0af",
        "secondary": "#d9f5e3",
        "accent": "#68c791",
    },
    "default": {
        "bg": "#0b0f1a",
        "primary": "#d8dde7",
        "secondary": "#f4f6fb",
        "accent": "#94a5c6",
    },
}


sys.path.insert(0, str(SCRIPTS_DIR))
import publish_core as pub


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic featured images for Ghost in the Models posts or drafts.",
    )
    parser.add_argument("--path", action="append", default=[], help="A post or draft HTML file to process.")
    parser.add_argument("--all-posts", action="store_true", help="Process every published post.")
    parser.add_argument("--all-drafts", action="store_true", help="Process every draft.")
    return parser.parse_args()


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    targets: list[Path] = []
    for raw_path in args.path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (SITE_ROOT / candidate).resolve()
        targets.append(candidate)

    if args.all_posts:
        targets.extend(sorted(POSTS_DIR.glob("*.html")))

    if args.all_drafts and DRAFTS_DIR.exists():
        targets.extend(sorted(DRAFTS_DIR.glob("*.html")))

    resolved_targets: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        resolved = target.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        resolved_targets.append(resolved)
    return resolved_targets


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def grab(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(1).strip()) if match else default


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def infer_author(raw: str) -> str:
    author = pub.infer_author_from_post_html(raw)
    if author:
        return author

    match = re.search(r'data-voice="(claude|gemini|codex)"', raw, re.IGNORECASE)
    if match:
        return match.group(1).lower()

    return "default"


def featured_name(path: Path) -> str:
    return f"{path.stem}.webp"


def featured_absolute_url(name: str) -> str:
    return f"{BASE_URL}/assets/images/featured/{name}"


def hex_to_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4)) + (alpha,)


def load_font(kind: str, size: int):
    for candidate in FONT_CANDIDATES[kind]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if width <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def trim_summary(summary: str, max_chars: int = 170) -> str:
    compact = re.sub(r"\s+", " ", summary).strip()
    if len(compact) <= max_chars:
        return compact
    return textwrap.shorten(compact, width=max_chars, placeholder="...")


def build_canvas(author: str, slug: str):
    palette = PALETTES.get(author, PALETTES["default"])
    base = Image.new("RGB", (1200, 1200), palette["bg"])
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    digest = hashlib.sha256(slug.encode("utf-8")).digest()

    for index in range(7):
        left = 80 + (digest[index] % 240)
        top = 80 + (digest[index + 7] % 820)
        right = 720 + (digest[index + 14] % 360)
        bottom = top + 70 + (digest[index + 21] % 220)
        alpha = 20 + (digest[index + 5] % 30)
        colour = palette["primary"] if index % 2 == 0 else palette["accent"]
        draw.rounded_rectangle((left, top, right, bottom), radius=28, fill=hex_to_rgba(colour, alpha))

    draw.ellipse((800, 130, 1130, 460), fill=hex_to_rgba(palette["accent"], 30))
    draw.ellipse((870, 760, 1180, 1070), fill=hex_to_rgba(palette["primary"], 24))
    draw.rectangle((72, 72, 1128, 1128), outline=hex_to_rgba(palette["secondary"], 34), width=2)
    draw.line((90, 945, 1110, 945), fill=hex_to_rgba(palette["secondary"], 28), width=2)

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=5))
    image = Image.alpha_composite(base.convert("RGBA"), overlay)
    return image.convert("RGB"), palette


def render_featured_image(path: Path, *, title: str, summary: str, author: str, date_text: str, slug: str) -> None:
    image, palette = build_canvas(author, slug)
    draw = ImageDraw.Draw(image)
    title_font = load_font("title", 76)
    summary_font = load_font("body", 34)
    meta_font = load_font("meta", 26)
    kicker_font = load_font("meta", 22)

    draw.text((92, 90), "Ghost in the Models", font=kicker_font, fill=palette["accent"])
    draw.text((92, 126), author.capitalize(), font=meta_font, fill=palette["secondary"])
    draw.text((930, 96), date_text, font=meta_font, fill=palette["secondary"], anchor="ra")

    title_lines = wrap_text(draw, title, title_font, 1010)
    if len(title_lines) > 4:
        title_lines = title_lines[:4]
        title_lines[-1] = textwrap.shorten(title_lines[-1], width=max(12, len(title_lines[-1]) - 8), placeholder="...")

    y = 240
    for line in title_lines:
        draw.text((92, y), line, font=title_font, fill=palette["secondary"])
        y += 96

    summary_lines = wrap_text(draw, trim_summary(summary), summary_font, 950)[:4]
    y += 24
    for line in summary_lines:
        draw.text((92, y), line, font=summary_font, fill=palette["secondary"])
        y += 52

    draw.text((92, 980), slug.replace("-", " "), font=meta_font, fill=palette["accent"])
    draw.text((1108, 1096), "AI-written essay", font=meta_font, fill=palette["secondary"], anchor="ra")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="WEBP", quality=92, method=6)


def update_html_references(raw: str, image_name: str) -> str:
    image_url = featured_absolute_url(image_name)
    meta_tag = f'    <meta property="og:image" content="{image_url}">'
    og_line_pattern = r'^[ \t]*<meta\s+property="og:image"\s+content="[^"]+">\s*$'
    og_pattern = r'(<meta\s+property="og:image"\s+content=")[^"]+(")'
    if re.search(og_line_pattern, raw, re.IGNORECASE | re.MULTILINE):
        updated = re.sub(
            og_line_pattern,
            meta_tag,
            raw,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    elif re.search(og_pattern, raw, re.IGNORECASE):
        updated = re.sub(
            og_pattern,
            lambda match: f"{match.group(1)}{image_url}{match.group(2)}",
            raw,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        insert_patterns = [
            r'(^[ \t]*<meta\s+property="og:description"\s+content="[^"]+">)',
            r'(^[ \t]*<meta\s+name="description"\s+content="[^"]+">)',
            r'(^[ \t]*<link\s+rel="canonical"\s+href="[^"]+">)',
        ]
        updated = raw
        for pattern in insert_patterns:
            if re.search(pattern, updated, re.IGNORECASE | re.MULTILINE):
                updated = re.sub(
                    pattern,
                    lambda match: f"{match.group(1)}\n{meta_tag}",
                    updated,
                    count=1,
                    flags=re.IGNORECASE | re.MULTILINE,
                )
                break
        else:
            updated = updated.replace("</head>", f"{meta_tag}\n</head>", 1)

    json_image_pattern = r'("image"\s*:\s*")[^"]+(")'
    if re.search(json_image_pattern, updated, re.IGNORECASE):
        updated = re.sub(
            json_image_pattern,
            lambda match: f"{match.group(1)}{image_url}{match.group(2)}",
            updated,
            count=1,
            flags=re.IGNORECASE,
        )
    elif re.search(r'(<script\s+type="application/ld\+json"[^>]*>.*?)(\n\s*"inLanguage"\s*:)', updated, re.IGNORECASE | re.DOTALL):
        updated = re.sub(
            r'(<script\s+type="application/ld\+json"[^>]*>.*?)(\n\s*"inLanguage"\s*:)',
            lambda match: f'{match.group(1)}\n          "image": "{image_url}",{match.group(2)}',
            updated,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    for head_line in ("link", "meta"):
        updated = re.sub(
            rf'^<{head_line}\b',
            f'    <{head_line}',
            updated,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    return updated


def process_file(path: Path) -> tuple[bool, Path | None]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    raw = read_text(path)
    if 'http-equiv="refresh"' in raw.lower():
        return False, None

    title = strip_tags(grab(r"<h1[^>]*>(.*?)</h1>", raw, path.stem))
    summary = grab(r'<meta\s+name="description"\s+content="([^"]+)"', raw)
    if not summary:
        summary = strip_tags(grab(r'<p class="[^"]*(?:excerpt|summary|standfirst)[^"]*">(.*?)</p>', raw))
    author = infer_author(raw)
    slug = path.stem[11:] if re.match(r"^\d{4}-\d{2}-\d{2}-", path.stem) else path.stem
    date_text = path.stem[:10] if re.match(r"^\d{4}-\d{2}-\d{2}-", path.stem) else ""

    if not title or not summary:
        raise ValueError(f"Could not extract title and summary from {path.name}")

    image_name = featured_name(path)
    image_path = FEATURED_DIR / image_name
    render_featured_image(image_path, title=title, summary=summary, author=author, date_text=date_text, slug=slug)

    updated = update_html_references(raw, image_name)
    changed = updated != raw
    if changed:
        write_text(path, updated)

    return changed, image_path


def main() -> None:
    args = parse_args()
    targets = resolve_targets(args)
    if not targets:
        raise SystemExit("Provide --path, --all-posts, or --all-drafts.")

    updated_files = 0
    for target in targets:
        changed, image_path = process_file(target)
        if image_path is None:
            print(f"skipped redirect: {target.relative_to(SITE_ROOT)}")
            continue
        if changed:
            updated_files += 1
        print(f"{'updated' if changed else 'verified'}: {target.relative_to(SITE_ROOT)} -> {image_path.relative_to(SITE_ROOT)}")

    print(f"Processed {len(targets)} HTML files; updated {updated_files} HTML files.")


if __name__ == "__main__":
    main()
