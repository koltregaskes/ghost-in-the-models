"""Catch stale share cards and drift between shipped collection pages and generators."""
from pathlib import Path
from PIL import Image
import importlib
import re
ROOT=Path(__file__).resolve().parent.parent
for post in (ROOT/'posts').glob('*.html'):
    raw=post.read_text(encoding='utf-8')
    if 'http-equiv="refresh"' in raw: continue
    source=ROOT/'assets/images/featured'/f'{post.stem}.webp'
    card=source.with_suffix('.png')
    with Image.open(source) as original, Image.open(card) as social:
        assert original.size == social.size and original.convert('RGB').tobytes() == social.convert('RGB').tobytes(), (post.name, 'stale share card')
    assert f'content="https://ghostinthemodels.com/assets/images/featured/{post.stem}.png"' in raw, (post.name, 'individual share card')
rebuild=importlib.import_module('rebuild-derived')
posts=rebuild.load_posts()
for name, rendered in [('archive.html',rebuild.render_archive(posts,rebuild.build_counts(posts))),('tags.html',rebuild.render_tags(posts))]:
    assert (ROOT/name).read_text(encoding='utf-8') == rendered, (name,'regenerate from source')
print('Derived pages match generators; individual PNG share cards match original artwork.')