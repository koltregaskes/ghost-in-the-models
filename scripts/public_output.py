"""Explicit public-file allowlist and URL host extraction. No recursive root copy."""
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

ROOT_FILES = {'index.html','about.html','archive.html','tags.html','privacy.html','404.html',
              'feed.xml','sitemap.xml','robots.txt','llms.txt','CNAME','cross-site-nav.js',
              'SECURITY.md','.well-known/security.txt','.nojekyll'}
ASSET_TYPES={'.css','.js','.png','.webp','.jpg','.jpeg','.gif','.svg','.mp4','.woff','.woff2','.ico'}


def allowed(name):
    path=PurePosixPath(name)
    if any(p in {'.','..'} or p.startswith('.') for p in path.parts) and name not in ROOT_FILES:return False
    if name in ROOT_FILES:return True
    if path.parts[0]=='assets':return path.suffix.lower() in ASSET_TYPES or name=='assets/contact.json'
    if path.parts[0]=='posts':return len(path.parts)==2 and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.html',path.name))
    return len(path.parts)==3 and path.parts[0]=='voice' and path.parts[1] in {'claude','gemini','codex','grok'} and path.name=='index.html'


# Keep authority punctuation until URL parsing strips userinfo/port. Terminate at
# slash, query, fragment, whitespace, quotes, closing parenthesis and comma.
HOST_RE=re.compile(r'(?i)(?<![\w:])(?:(?:https?|wss?):)?//([^/\s?#\"\'`<>),;]+)')
def hosts(text):
    result=set()
    for m in HOST_RE.finditer(text):
        authority=m[1]
        # Avoid treating ordinary JS/CSS line comments as protocol-relative URLs.
        if '.' not in authority and not authority.startswith('['):continue
        try: host=urlsplit('https://'+authority).hostname
        except ValueError:raise ValueError('Malformed URL authority in public output')
        if host:result.add(host.lower().rstrip('.'))
    return result


def public_sources(root):
    files=[]
    for name in sorted(ROOT_FILES):
        p=root/name
        if p.is_file():files.append(p)
    for directory in ['assets','posts','voice']:
        for p in (root/directory).rglob('*'):
            if p.is_file() and allowed(p.relative_to(root).as_posix()):files.append(p)
    for p in files:
        if p.is_symlink() or any((root/parent).is_symlink() for parent in p.relative_to(root).parents if parent!=Path('.')):
            raise ValueError('Symlinks are not allowed in public output')
    return files
