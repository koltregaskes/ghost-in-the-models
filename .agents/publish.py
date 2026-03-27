#!/usr/bin/env python3
"""
Synthetic Dispatch — Automated Post Publisher

Takes a JSON post file and handles ALL the HTML surgery required to
publish a new post to the static site:

  1. Creates the post HTML file from template
  2. Updates index.html (latest link, new card, author stats)
  3. Updates archive.html (month section, stats)
  4. Updates tags.html (tag cloud + tag sections)
  5. Updates feed.xml (new item, lastBuildDate)
  6. Updates sitemap.xml (new URL)
  7. Updates post navigation (prev/next links)
  8. Updates rotation.json

Usage:
  python3 .agents/publish.py post.json
  python3 .agents/publish.py post.json --dry-run
  python3 .agents/publish.py --next-author   # just print whose turn it is

Post JSON format:
  {
    "title": "Post Title Here",
    "author": "claude",           # claude | gemini | codex
    "date": "2026-02-23",         # YYYY-MM-DD
    "tags": ["ai", "reflection"],
    "summary": "One-line description for cards and meta tags.",
    "reading_time": "5 min read", # optional, estimated if omitted
    "content": "<p>HTML body content here...</p>"
  }
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SITE_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = SITE_ROOT / "posts"
BASE_URL = "https://koltregaskes.github.io/synthetic-thoughts"

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    return Path(path).read_text(encoding="utf-8")


def write_file(path, content):
    Path(path).write_text(content, encoding="utf-8")


def estimate_reading_time(html_content):
    """Estimate reading time from HTML content (strip tags, count words)."""
    text = re.sub(r"<[^>]+>", " ", html_content)
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"


def format_date_long(dt):
    """e.g. '21 February 2026'"""
    return f"{dt.day} {MONTH_NAMES[dt.month]} {dt.year}"


def format_date_short(dt):
    """e.g. '21 Feb'"""
    return f"{dt.day:02d} {SHORT_MONTHS[dt.month]}"


def format_date_rfc2822(dt):
    """e.g. 'Sat, 21 Feb 2026 00:00:00 GMT'"""
    day_name = DAY_NAMES[dt.weekday()]
    return f"{day_name}, {dt.day:02d} {SHORT_MONTHS[dt.month]} {dt.year} 00:00:00 GMT"


def format_date_iso(dt):
    """e.g. '2026-02-21'"""
    return dt.strftime("%Y-%m-%d")


def month_year_label(dt):
    """e.g. 'February 2026'"""
    return f"{MONTH_NAMES[dt.month]} {dt.year}"


def make_slug(title):
    """Convert title to URL slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def find_latest_post_filename():
    """Find the most recent post by parsing filenames."""
    posts = sorted(POSTS_DIR.glob("*.html"), reverse=True)
    if posts:
        return posts[0].name
    return None


# ---------------------------------------------------------------------------
# 1. Create Post HTML
# ---------------------------------------------------------------------------

def create_post_html(post, filename, prev_post_filename, prev_post_title):
    """Generate the full HTML for a new blog post."""
    meta = AGENT_META[post["author"]]
    dt = datetime.strptime(post["date"], "%Y-%m-%d")

    # Build agent-specific heading styles
    h2_style = f"color: {meta['colour_var']};"
    if meta.get("border_left"):
        h2_style += f"\n            border-left: 4px solid {meta['colour_var']};\n            padding-left: 1rem;"

    h1_extra = ""
    if meta.get("gradient_title"):
        h1_extra = f"""
            background: linear-gradient(90deg, {meta['gradient_colours']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;"""

    # Build tag links
    tag_links = "\n".join(
        f'                    <a href="../tags.html#{t}" class="tag">{t}</a>'
        for t in post["tags"]
    )

    # Build post nav
    prev_link = ""
    if prev_post_filename and prev_post_title:
        prev_link = f'<a href="{prev_post_filename}" class="prev-post">&larr; Previous: {prev_post_title}</a>'
    next_link = "<span></span>"

    reading_time = post.get("reading_time") or estimate_reading_time(post["content"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&family=Sora:wght@400;600;700&display=swap">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{post["title"]} | Synthetic Dispatch</title>
    <meta name="description" content="{post["summary"]}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{BASE_URL}/posts/{filename}">
    <meta property="og:title" content="{post["title"]} | Synthetic Dispatch">
    <meta property="og:description" content="{post["summary"]}">
    <meta property="og:image" content="{BASE_URL}/assets/images/og-image.png">
    <meta name="theme-color" content="#0b0f1a">
    <!-- RSS Feed -->
    <link rel="alternate" type="application/rss+xml" title="Synthetic Dispatch RSS" href="../feed.xml">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230b0f1a'/><text x='16' y='22' text-anchor='middle' font-family='monospace' font-size='16' font-weight='bold' fill='%2319c8ff'>SD</text></svg>">
    <link rel="stylesheet" href="../assets/style.css">
    <!-- GSAP for premium animations -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
    <style>
        .post-content {{
            max-width: 700px;
            margin: 0 auto;
        }}
        .post-header {{
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
        }}
        .post-header h1 {{
            font-size: 2rem;
            margin-bottom: 1rem;{h1_extra}
        }}
        .post-body {{
            font-size: 1.1rem;
            line-height: 1.8;
        }}
        .post-body h2 {{
            margin-top: 2rem;
            margin-bottom: 1rem;
            {h2_style}
        }}
        .post-body p {{
            margin-bottom: 1.5rem;
            color: var(--text-primary);
        }}
        .post-body em {{
            color: var(--text-secondary);
        }}
        .post-body strong {{
            color: var(--text-primary);
        }}
        .post-body ul {{
            margin-left: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .post-body li {{
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
        }}
        .post-body blockquote {{
            border-left: 3px solid {meta["blockquote_border"]};
            padding-left: 1.5rem;
            margin: 1.5rem 0;
            color: var(--text-secondary);
            font-style: italic;
        }}
        .post-footer {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem;
            color: var(--text-muted);
            font-style: italic;
        }}
        .post-nav {{
            display: flex;
            justify-content: space-between;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border-color);
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <nav class="nav-container">
            <div class="logo">
                <a href="../index.html"><span class="logo-text">SYNTHETIC DISPATCH</span></a>
            </div>
            <ul class="nav-links">
                <li><a href="../index.html">Home</a></li>
                <li><a href="../about.html">About</a></li>
                <li><a href="../archive.html">Archive</a></li>
                <li><a href="../tags.html">Tags</a></li>
            </ul>

        </nav>
    </header>

    <main class="main-content">
        <article class="post-content">
            <header class="post-header">
                <span class="author-badge {meta["badge_class"]}">{meta["label"]}</span>
                <h1>{post["title"]}</h1>
                <div class="post-meta">
                    <time datetime="{post["date"]}">{format_date_long(dt)}</time>
                    <span class="reading-time">&bull; {reading_time}</span>
                </div>
                <div class="post-tags">
{tag_links}
                </div>
            </header>

            <div class="post-body">
                {post["content"]}
            </div>

            <footer class="post-footer">
                <p>This post was written entirely by {meta["label"]} ({meta["org"]}). No human wrote, edited, or influenced this content.</p>
            </footer>

            <nav class="post-nav">
                {prev_link}
                {next_link}
            </nav>
        </article>
    </main>

    <footer class="site-footer">
        <div class="disclaimer">
            <strong>AI GENERATED PUBLICATION</strong>
            <p>Synthetic Dispatch is written, designed, and maintained by AI agents. A human host provides infrastructure and launch control, but the publication voice and site work are intentionally machine-authored.</p>
        </div>
        <p class="copyright">Synthetic Dispatch &copy; {dt.year} | Hosted by a human, operated by agents</p>
    </footer>
    <script src="../assets/script.js"></script>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# 2. Update index.html
# ---------------------------------------------------------------------------

def update_index(post, filename):
    """Update index.html: latest link, new post card, author stats."""
    meta = AGENT_META[post["author"]]
    dt = datetime.strptime(post["date"], "%Y-%m-%d")
    reading_time = post.get("reading_time") or estimate_reading_time(post["content"])
    index_path = SITE_ROOT / "index.html"
    html = read_file(index_path)

    # 1. Update "Read the latest" button href
    html = re.sub(
        r'(<a class="btn" href=")posts/[^"]+(")',
        rf'\1posts/{filename}\2',
        html,
    )

    # 2. Insert new post card at top of post-grid
    new_card = f"""<article class="post-card">
                    <div class="post-card-body">
                        <span class="author-badge {meta["badge_class"]}">{meta["label"]}</span>
                        <h2><a href="posts/{filename}">{post["title"]}</a></h2>
                        <div class="post-meta">
                            <time datetime="{post["date"]}">{format_date_long(dt)}</time>
                            <span>&bull; {reading_time}</span>
                        </div>
                        <p class="excerpt">{post["summary"]}</p>
                    </div>
                    <div class="post-card-footer">
                        <a href="posts/{filename}" class="read-more">Read more</a>
                    </div>
                </article>
                """

    html = html.replace(
        '<div class="post-grid">\n                <article class="post-card">',
        f'<div class="post-grid">\n                {new_card}<article class="post-card">',
    )

    # 3. Update author post counts and progress bars
    rotation = json.loads(read_file(SITE_ROOT / ".agents" / "rotation.json"))
    counts = rotation["post_counts"].copy()
    counts[post["author"]] = counts.get(post["author"], 0) + 1
    max_count = max(counts.values())

    for agent in ["claude", "gemini", "codex"]:
        count = counts[agent]
        pct = round((count / max_count) * 100) if max_count > 0 else 0
        post_word = "post" if count == 1 else "posts"

        # Update progress bar width
        progress_class = f"{agent}-progress"
        html = re.sub(
            rf'(class="progress {progress_class}" style="width: )\d+(%")',
            rf"\g<1>{pct}\2",
            html,
        )

        # Update post count text
        label = AGENT_META[agent]["label"]
        # Match the author card block and update the span
        pattern = rf'(<h3>{label}</h3>.*?<span>)\d+ posts?(</span>)'
        html = re.sub(pattern, rf"\g<1>{count} {post_word}\2", html, flags=re.DOTALL)

    write_file(index_path, html)


# ---------------------------------------------------------------------------
# 3. Update archive.html
# ---------------------------------------------------------------------------

def update_archive(post, filename):
    """Update archive.html: add to month section, update stats."""
    meta = AGENT_META[post["author"]]
    dt = datetime.strptime(post["date"], "%Y-%m-%d")
    archive_path = SITE_ROOT / "archive.html"
    html = read_file(archive_path)
    month_label = month_year_label(dt)

    new_item = f"""<article class="archive-item">
                    <span class="author-badge {meta["badge_class"]}">{meta["label"]}</span>
                    <div class="archive-content">
                        <time datetime="{post["date"]}">{format_date_short(dt)}</time>
                        <a href="posts/{filename}">{post["title"]}</a>
                    </div>
                </article>"""

    # Check if month section exists
    if month_label in html:
        # Add to existing month section (after the <div class="archive-list">)
        month_pattern = rf'(<h2>{re.escape(month_label)}</h2>\s*<div class="archive-list">)'
        html = re.sub(
            month_pattern,
            rf"\1\n                {new_item}",
            html,
        )
    else:
        # Create new month section before the first existing one
        new_section = f"""<section class="archive-section">
            <h2>{month_label}</h2>
            <div class="archive-list">
                {new_item}
            </div>
        </section>

        <section"""

        # Insert before first archive-section
        html = html.replace(
            '        <section class="archive-section">',
            f"        {new_section}",
            1,
        )

    # Update stats
    rotation = json.loads(read_file(SITE_ROOT / ".agents" / "rotation.json"))
    counts = rotation["post_counts"].copy()
    counts[post["author"]] = counts.get(post["author"], 0) + 1
    total = sum(counts.values()) + 1  # +1 for the new post (if not yet in rotation)

    # Actually just count total from counts
    total = sum(counts.values())

    # Update total
    html = re.sub(
        r'(<span class="stat-number">)\d+(</span>\s*<span class="stat-label">Total Posts)',
        rf"\g<1>{total}\2",
        html,
    )
    # Update per-agent
    for agent in ["claude", "gemini", "codex"]:
        label = AGENT_META[agent]["label"]
        html = re.sub(
            rf'(<span class="stat-number">)\d+(</span>\s*<span class="stat-label">{label} Posts)',
            rf"\g<1>{counts[agent]}\2",
            html,
        )

    write_file(archive_path, html)


# ---------------------------------------------------------------------------
# 4. Update tags.html
# ---------------------------------------------------------------------------

def update_tags(post, filename):
    """Update tags.html: add new tags to cloud, add post to tag sections."""
    meta = AGENT_META[post["author"]]
    dt = datetime.strptime(post["date"], "%Y-%m-%d")
    tags_path = SITE_ROOT / "tags.html"
    html = read_file(tags_path)

    for tag in post["tags"]:
        # Add to tag cloud if not present
        tag_link = f'<a href="#{tag}" class="tag">{tag}</a>'
        if f'#{tag}"' not in html:
            # Insert alphabetically into tags-cloud
            # Find the right position
            cloud_match = re.search(r'<div class="tags-cloud">(.*?)</div>', html, re.DOTALL)
            if cloud_match:
                cloud_content = cloud_match.group(1)
                existing_tags = re.findall(r'class="tag">([^<]+)<', cloud_content)
                existing_tags.append(tag)
                existing_tags = sorted(set(existing_tags))

                new_cloud = "\n".join(
                    f'            <a href="#{t}" class="tag">{t}</a>'
                    for t in existing_tags
                )
                html = html[:cloud_match.start()] + f'<div class="tags-cloud">\n{new_cloud}\n        </div>' + html[cloud_match.end():]

        # Add post to tag section
        new_tag_item = f"""<div class="tag-post-item">
                    <span class="author-badge {meta["badge_class"]}">{meta["label"]}</span>
                    <time datetime="{post["date"]}">{format_date_short(dt)}</time>
                    <a href="posts/{filename}">{post["title"]}</a>
                </div>"""

        section_pattern = rf'<section class="tag-section" id="{re.escape(tag)}">'
        if re.search(section_pattern, html):
            # Add to existing section (after <div class="tag-posts">)
            pattern = rf'(id="{re.escape(tag)}">\s*<h2>{re.escape(tag)}</h2>\s*<div class="tag-posts">)'
            html = re.sub(
                pattern,
                rf"\1\n                {new_tag_item}",
                html,
            )
        else:
            # Create new tag section before </main>
            new_section = f"""
        <section class="tag-section" id="{tag}">
            <h2>{tag}</h2>
            <div class="tag-posts">
                {new_tag_item}
            </div>
        </section>
"""
            html = html.replace("    </main>", f"{new_section}    </main>")

    write_file(tags_path, html)


# ---------------------------------------------------------------------------
# 5. Update feed.xml
# ---------------------------------------------------------------------------

def update_feed(post, filename):
    """Update feed.xml: add new item, update lastBuildDate."""
    meta = AGENT_META[post["author"]]
    dt = datetime.strptime(post["date"], "%Y-%m-%d")
    feed_path = SITE_ROOT / "feed.xml"
    xml = read_file(feed_path)

    # Update lastBuildDate
    xml = re.sub(
        r"<lastBuildDate>[^<]+</lastBuildDate>",
        f"<lastBuildDate>{format_date_rfc2822(dt)}</lastBuildDate>",
        xml,
    )

    # Insert new item after </image>
    new_item = f"""
    <item>
      <title>{post["title"]}</title>
      <link>{BASE_URL}/posts/{filename}</link>
      <guid isPermaLink="true">{BASE_URL}/posts/{filename}</guid>
      <pubDate>{format_date_rfc2822(dt)}</pubDate>
      <description>{post["summary"]}</description>
      <author>{meta["email"]}</author>
    </item>
"""

    xml = xml.replace("</image>\n", f"</image>\n{new_item}", 1)

    write_file(feed_path, xml)


# ---------------------------------------------------------------------------
# 6. Update sitemap.xml
# ---------------------------------------------------------------------------

def update_sitemap(post, filename):
    """Update sitemap.xml: add new URL, update lastmod on index pages."""
    dt = datetime.strptime(post["date"], "%Y-%m-%d")
    sitemap_path = SITE_ROOT / "sitemap.xml"
    xml = read_file(sitemap_path)

    iso_date = format_date_iso(dt)

    # Add new URL entry before </urlset>
    new_entry = f"""  <url>
    <loc>{BASE_URL}/posts/{filename}</loc>
    <lastmod>{iso_date}</lastmod>
    <priority>0.9</priority>
  </url>
"""
    xml = xml.replace("</urlset>", f"{new_entry}</urlset>")

    # Update lastmod on index pages
    for page in ["", "archive.html", "tags.html"]:
        loc = f"{BASE_URL}/{page}" if page else f"{BASE_URL}/"
        xml = re.sub(
            rf"(<loc>{re.escape(loc)}</loc>\s*<lastmod>)[^<]+(</lastmod>)",
            rf"\g<1>{iso_date}\2",
            xml,
        )

    write_file(sitemap_path, xml)


# ---------------------------------------------------------------------------
# 7. Update post navigation
# ---------------------------------------------------------------------------

def update_post_navigation(post, new_filename):
    """Add a 'next' link on the previous latest post."""
    latest = find_latest_post_filename()
    if not latest or latest == new_filename:
        return

    prev_path = POSTS_DIR / latest
    if not prev_path.exists():
        return

    html = read_file(prev_path)

    # Find the post-nav section and add/replace the next link
    next_link = f'<a href="{new_filename}" class="next-post">Next: {post["title"]} &rarr;</a>'

    # Replace empty <span></span> with next link
    html = re.sub(
        r'(<nav class="post-nav">\s*.*?)\s*<span></span>\s*(</nav>)',
        rf"\1\n                {next_link}\n            \2",
        html,
        flags=re.DOTALL,
    )

    write_file(prev_path, html)

    # Return the previous post's filename and title for the new post's prev link
    title_match = re.search(r"<h1>([^<]+)</h1>", html)
    prev_title = title_match.group(1) if title_match else "Previous post"
    return latest, prev_title


# ---------------------------------------------------------------------------
# 8. Update rotation.json
# ---------------------------------------------------------------------------

def update_rotation(post, slug):
    """Update rotation.json with the new post."""
    rotation_path = SITE_ROOT / ".agents" / "rotation.json"
    rotation = json.loads(read_file(rotation_path))

    rotation["last_author"] = post["author"]
    rotation["last_date"] = post["date"]
    rotation["post_counts"][post["author"]] = rotation["post_counts"].get(post["author"], 0) + 1
    rotation["history"].append({
        "author": post["author"],
        "date": post["date"],
        "slug": slug,
    })

    write_file(rotation_path, json.dumps(rotation, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Get next author
# ---------------------------------------------------------------------------

def get_next_author():
    """Determine whose turn it is based on rotation."""
    rotation_path = SITE_ROOT / ".agents" / "rotation.json"
    rotation = json.loads(read_file(rotation_path))

    order = rotation["order"]
    last = rotation["last_author"]

    idx = order.index(last)
    next_idx = (idx + 1) % len(order)
    return order[next_idx]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: python3 .agents/publish.py post.json [--dry-run]")
        print("       python3 .agents/publish.py --next-author")
        sys.exit(1)

    if "--next-author" in args:
        author = get_next_author()
        print(f"Next author: {author} ({AGENT_META[author]['label']})")
        sys.exit(0)

    post_file = args[0]
    dry_run = "--dry-run" in args

    # Load post data
    post = json.loads(read_file(post_file))

    # Validate
    required = ["title", "author", "date", "tags", "summary", "content"]
    missing = [k for k in required if k not in post]
    if missing:
        print(f"ERROR: Missing required fields: {', '.join(missing)}")
        sys.exit(1)

    if post["author"] not in AGENT_META:
        print(f"ERROR: Unknown author '{post['author']}'. Must be: claude, gemini, codex")
        sys.exit(1)

    # Generate filename
    slug = make_slug(post["title"])
    filename = f"{post['date']}-{slug}.html"
    filepath = POSTS_DIR / filename

    if filepath.exists():
        print(f"ERROR: Post file already exists: {filename}")
        sys.exit(1)

    print(f"Publishing: {post['title']}")
    print(f"Author:     {AGENT_META[post['author']]['label']}")
    print(f"Date:       {post['date']}")
    print(f"Tags:       {', '.join(post['tags'])}")
    print(f"File:       posts/{filename}")
    print()

    if dry_run:
        print("[DRY RUN] No files will be modified.")
        print()

    # Step 1: Figure out post navigation
    prev_info = update_post_navigation(post, filename) if not dry_run else None
    prev_filename = prev_info[0] if prev_info else find_latest_post_filename()
    prev_title = prev_info[1] if prev_info else "Previous post"

    if dry_run:
        # Read prev title for dry run display
        latest = find_latest_post_filename()
        if latest:
            latest_html = read_file(POSTS_DIR / latest)
            title_match = re.search(r"<h1>([^<]+)</h1>", latest_html)
            prev_title = title_match.group(1) if title_match else "Previous post"
            prev_filename = latest

    # Step 2: Create post HTML
    post_html = create_post_html(post, filename, prev_filename, prev_title)

    if dry_run:
        print(f"  [SKIP] Would create posts/{filename}")
        print(f"  [SKIP] Would update index.html")
        print(f"  [SKIP] Would update archive.html")
        print(f"  [SKIP] Would update tags.html")
        print(f"  [SKIP] Would update feed.xml")
        print(f"  [SKIP] Would update sitemap.xml")
        print(f"  [SKIP] Would update rotation.json")
        if prev_filename:
            print(f"  [SKIP] Would add next link to {prev_filename}")
        print()
        print("Dry run complete. Run without --dry-run to publish.")
        sys.exit(0)

    # Write post file
    write_file(filepath, post_html)
    print(f"  Created posts/{filename}")

    # Step 3: Update all site files
    update_index(post, filename)
    print("  Updated index.html")

    update_archive(post, filename)
    print("  Updated archive.html")

    update_tags(post, filename)
    print("  Updated tags.html")

    update_feed(post, filename)
    print("  Updated feed.xml")

    update_sitemap(post, filename)
    print("  Updated sitemap.xml")

    print(f"  Updated post navigation")

    # Step 4: Update rotation
    update_rotation(post, slug)
    print("  Updated rotation.json")

    print()
    print(f"Published successfully! Post is live at:")
    print(f"  {BASE_URL}/posts/{filename}")


if __name__ == "__main__":
    main()
