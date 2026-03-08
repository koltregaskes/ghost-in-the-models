#!/usr/bin/env python3
"""
Generate a blog post for Synthetic Thoughts using Gemini or Codex APIs.
Updates all site files (index.html, archive.html, tags.html, post navigation).

Usage:
    python scripts/generate-post.py gemini
    python scripts/generate-post.py codex
"""

import sys
import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"


def read_prompt(author: str) -> str:
    """Read the prompt file for the given author."""
    prompt_file = ROOT / "docs" / f"prompt-{author}.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text()


def get_latest_post() -> dict:
    """Find the most recent post by filename date."""
    posts = sorted(POSTS_DIR.glob("*.html"), reverse=True)
    if not posts:
        return {"file": None, "title": None}

    latest = posts[0]
    # Extract title from <h1> tag
    content = latest.read_text()
    title_match = re.search(r"<h1>(.*?)</h1>", content)
    title = title_match.group(1) if title_match else latest.stem

    return {"file": latest.name, "title": title}


def call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Google Gemini API."""
    import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-pro",
        system_instruction=system_prompt,
    )
    response = model.generate_content(user_prompt)
    return response.text


def call_codex(system_prompt: str, user_prompt: str) -> str:
    """Call OpenAI API for Codex."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="o3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def extract_html_from_response(response: str) -> str:
    """Extract HTML content from a model response that may include markdown code fences."""
    # Try to find HTML in code fences first
    html_match = re.search(r"```html?\s*\n(.*?)```", response, re.DOTALL)
    if html_match:
        return html_match.group(1).strip()

    # If the response starts with <!DOCTYPE or <html, use it directly
    stripped = response.strip()
    if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
        return stripped

    # Last resort: look for the full HTML document
    doc_match = re.search(r"(<!DOCTYPE html>.*?</html>)", response, re.DOTALL | re.IGNORECASE)
    if doc_match:
        return doc_match.group(1).strip()

    raise ValueError("Could not extract HTML from model response")


def extract_post_metadata(html: str) -> dict:
    """Extract metadata from a post's HTML."""
    title_match = re.search(r"<h1>(.*?)</h1>", html)
    date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', html)
    tags_matches = re.findall(r'class="tag">(.*?)</a>', html)
    author_match = re.search(r'class="author-badge\s+(\w+)"', html)
    reading_match = re.search(r"(\d+)\s*min read", html)
    excerpt_match = re.search(r'<meta name="description" content="(.*?)"', html)

    return {
        "title": title_match.group(1) if title_match else "Untitled",
        "date": date_match.group(1) if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "tags": tags_matches,
        "author": author_match.group(1) if author_match else "unknown",
        "reading_time": reading_match.group(1) if reading_match else "5",
        "excerpt": excerpt_match.group(1) if excerpt_match else "",
    }


def generate_filename(date: str, title: str) -> str:
    """Generate a post filename from date and title."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    # Truncate slug to reasonable length
    slug = "-".join(slug.split("-")[:6])
    return f"{date}-{slug}.html"


def update_index(filename: str, metadata: dict):
    """Update index.html with the new post."""
    index_path = ROOT / "index.html"
    content = index_path.read_text()

    # Update "Read the latest" button
    content = re.sub(
        r'href="posts/[^"]+">Read the latest',
        f'href="posts/{filename}">Read the latest',
        content,
    )

    # Build new post card
    date_obj = datetime.strptime(metadata["date"], "%Y-%m-%d")
    display_date = date_obj.strftime("%-d %B %Y")
    new_card = f"""                <article class="post-card">
                    <div class="post-card-body">
                        <span class="author-badge {metadata['author']}">{metadata['author'].title()}</span>
                        <h2><a href="posts/{filename}">{metadata['title']}</a></h2>
                        <div class="post-meta">
                            <time datetime="{metadata['date']}">{display_date}</time>
                            <span>• {metadata['reading_time']} min read</span>
                        </div>
                        <p class="excerpt">{metadata['excerpt']}</p>
                    </div>
                    <div class="post-card-footer">
                        <a href="posts/{filename}" class="read-more">Read more</a>
                    </div>
                </article>"""

    # Insert at the top of the post grid
    content = content.replace(
        '<div class="post-grid">',
        f'<div class="post-grid">\n{new_card}',
    )

    # Count existing cards and remove excess (keep 7)
    cards = list(re.finditer(r"<article class=\"post-card\">", content))
    if len(cards) > 7:
        # Remove the last card(s)
        last_card_start = cards[7].start()
        # Find the closing </article> after this
        remaining = content[last_card_start:]
        for _ in range(len(cards) - 7):
            end_match = re.search(r"</article>", remaining)
            if end_match:
                cut_end = last_card_start + end_match.end()
                # Also remove any whitespace/newline after
                while cut_end < len(content) and content[cut_end] in "\n\r \t":
                    cut_end += 1
                content = content[:last_card_start] + content[cut_end:]
                remaining = content[last_card_start:]

    # Update author post counts
    author = metadata["author"]
    count_pattern = rf'(<div class="author-card">.*?<h3>{author.title()}</h3>.*?<span>)(\d+)( posts</span>)'
    count_match = re.search(count_pattern, content, re.DOTALL)
    if count_match:
        old_count = int(count_match.group(2))
        new_count = old_count + 1
        content = content[:count_match.start(2)] + str(new_count) + content[count_match.end(2):]

    index_path.write_text(content)
    print(f"Updated index.html")


def update_archive(filename: str, metadata: dict):
    """Update archive.html with the new post."""
    archive_path = ROOT / "archive.html"
    content = archive_path.read_text()

    date_obj = datetime.strptime(metadata["date"], "%Y-%m-%d")
    month_name = date_obj.strftime("%B %Y")
    display_date = date_obj.strftime("%-d %B %Y")

    new_entry = f"""                    <li>
                        <span class="author-badge {metadata['author']}">{metadata['author'].title()}</span>
                        <a href="posts/{filename}">{metadata['title']}</a>
                        <time datetime="{metadata['date']}">{display_date}</time>
                    </li>"""

    # Check if the month section exists
    month_id = date_obj.strftime("%B").lower() + "-" + date_obj.strftime("%Y")
    if f'id="{month_id}"' in content:
        # Add to existing month section (after the <ul>)
        month_section = content.index(f'id="{month_id}"')
        ul_pos = content.index("<ul>", month_section)
        content = content[:ul_pos + 4] + "\n" + new_entry + content[ul_pos + 4:]
    else:
        # Create new month section — insert after the archive-intro paragraph
        new_section = f"""
        <section class="archive-month" id="{month_id}">
            <h2>{month_name}</h2>
            <ul class="archive-list">
{new_entry}
                </ul>
        </section>"""
        # Insert after the first </p> in the archive intro
        intro_end = content.index("</p>", content.index("archive-intro")) + 4
        content = content[:intro_end] + "\n" + new_section + content[intro_end:]

    archive_path.write_text(content)
    print(f"Updated archive.html")


def update_tags(filename: str, metadata: dict):
    """Update tags.html with the new post for each tag."""
    tags_path = ROOT / "tags.html"
    content = tags_path.read_text()

    date_obj = datetime.strptime(metadata["date"], "%Y-%m-%d")
    display_date = date_obj.strftime("%-d %B %Y")

    for tag in metadata["tags"]:
        tag_slug = tag.lower().replace(" ", "-")
        entry = f"""                    <li>
                        <span class="author-badge {metadata['author']}">{metadata['author'].title()}</span>
                        <a href="posts/{filename}">{metadata['title']}</a>
                        <time datetime="{metadata['date']}">{display_date}</time>
                    </li>"""

        if f'id="{tag_slug}"' in content:
            # Add to existing tag section
            tag_section = content.index(f'id="{tag_slug}"')
            ul_pos = content.index("<ul", tag_section)
            ul_open_end = content.index(">", ul_pos) + 1
            content = content[:ul_open_end] + "\n" + entry + content[ul_open_end:]
        else:
            # Create new tag section and add to cloud
            new_section = f"""
        <section class="tag-section" id="{tag_slug}">
            <h2>#{tag}</h2>
            <ul class="archive-list">
{entry}
            </ul>
        </section>"""

            # Add before closing </main>
            main_close = content.rindex("</main>")
            content = content[:main_close] + new_section + "\n    " + content[main_close:]

            # Add to tags cloud if not already there
            if f'href="#{tag_slug}"' not in content:
                cloud_end = content.index("</div>", content.index("tags-cloud"))
                tag_link = f'            <a href="#{tag_slug}" class="tag">{tag}</a>\n'
                content = content[:cloud_end] + tag_link + "        " + content[cloud_end:]

    tags_path.write_text(content)
    print(f"Updated tags.html")


def update_post_navigation(new_filename: str, new_title: str, prev_filename: str):
    """Update the previous post's nav to link to the new post."""
    prev_path = POSTS_DIR / prev_filename
    if not prev_path.exists():
        print(f"Warning: previous post {prev_filename} not found, skipping nav update")
        return

    content = prev_path.read_text()

    # Replace empty <span></span> or add next link
    if "<span></span>" in content:
        content = content.replace(
            "<span></span>",
            f'<a href="{new_filename}" class="next-post">Next: {new_title} &rarr;</a>',
        )
    elif "post-nav" in content:
        # Try to find the post-nav and add a next link
        nav_match = re.search(r"(<nav class=\"post-nav\">.*?)(</nav>)", content, re.DOTALL)
        if nav_match:
            nav_content = nav_match.group(1)
            if "next-post" not in nav_content:
                next_link = f'\n                <a href="{new_filename}" class="next-post">Next: {new_title} &rarr;</a>\n            '
                content = content[:nav_match.end(1)] + next_link + content[nav_match.start(2):]

    prev_path.write_text(content)
    print(f"Updated navigation in {prev_filename}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("gemini", "codex"):
        print("Usage: python generate-post.py [gemini|codex]")
        sys.exit(1)

    author = sys.argv[1]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Read the prompt
    prompt_content = read_prompt(author)

    # Get latest post info for context
    latest = get_latest_post()
    latest_info = ""
    if latest["file"]:
        latest_info = f"\n\nThe most recent post is '{latest['title']}', file: posts/{latest['file']}. Your post's Previous link should point to this file."

    # Build the user prompt
    user_prompt = f"""Write a new blog post for Synthetic Thoughts. Today's date is {today}.

Search for the most interesting AI or technology news from the past 7-14 days and write a post about it.

Return ONLY the complete HTML file for the post — no explanation, no markdown fences, just the raw HTML starting with <!DOCTYPE html>.
{latest_info}

Refer to the writing guide below for voice, template, and quality standards:

{prompt_content}"""

    system_prompt = f"You are {author.title()}, an AI author on the Synthetic Thoughts blog. You write in UK English. Return only raw HTML."

    # Call the appropriate API
    print(f"Calling {author} API...")
    if author == "gemini":
        response = call_gemini(system_prompt, user_prompt)
    else:
        response = call_codex(system_prompt, user_prompt)

    # Extract HTML
    html = extract_html_from_response(response)
    metadata = extract_post_metadata(html)

    # Generate filename
    filename = generate_filename(metadata["date"], metadata["title"])
    post_path = POSTS_DIR / filename
    post_path.write_text(html)
    print(f"Wrote post: {post_path}")

    # Update site files
    update_index(filename, metadata)
    update_archive(filename, metadata)
    update_tags(filename, metadata)

    if latest["file"]:
        update_post_navigation(filename, metadata["title"], latest["file"])

    print(f"\nDone! Post '{metadata['title']}' by {author.title()} published.")
    print(f"File: posts/{filename}")
    print(f"Tags: {', '.join(metadata['tags'])}")


if __name__ == "__main__":
    main()
