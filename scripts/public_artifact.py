"""Shared allowlist for PR #48's builder and the pinned signature verifier."""
from pathlib import Path, PurePosixPath
import json
import re
import shutil

ROOT_FILES = {'index.html','about.html','archive.html','tags.html','privacy.html','404.html',
              'feed.xml','sitemap.xml','robots.txt','llms.txt','CNAME','cross-site-nav.js',
              'SECURITY.md','.well-known/security.txt','.nojekyll'}
ASSET_TYPES={'.css','.js','.png','.webp','.jpg','.jpeg','.gif','.svg','.mp4','.woff','.woff2','.ico'}


def allowed(name):
    path=PurePosixPath(name)
    if not path.parts or path.is_absolute():return False
    if any(p in {'.','..'} or p.startswith('.') for p in path.parts) and name not in ROOT_FILES:return False
    if name in ROOT_FILES:return True
    if path.parts[0]=='assets':return path.suffix.lower() in ASSET_TYPES or name=='assets/contact.json'
    if path.parts[0]=='posts':return len(path.parts)==2 and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.html',path.name))
    return len(path.parts)==3 and path.parts[0]=='voice' and path.parts[1] in {'claude','gemini','codex','grok'} and path.name=='index.html'


def public_sources(root):
    files=[]
    for name in sorted(ROOT_FILES):
        if (root/name).is_file():files.append(root/name)
    for directory in ['assets','posts','voice']:
        for p in (root/directory).rglob('*'):
            if p.is_file() and allowed(p.relative_to(root).as_posix()):files.append(p)
    for p in files:
        if any((root/part).is_symlink() for part in [p.relative_to(root),*p.relative_to(root).parents]):
            raise ValueError('Symlinks are not allowed in public output')
    return files


def build(root,output):
    if output.exists():raise ValueError('Output exists; use a fresh directory. Nothing is deleted.')
    files=public_sources(root)
    if not files:raise ValueError('No public inputs found')
    output.mkdir(parents=True)
    for source in files:
        target=output/source.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    contact=json.loads((root/'config/contact.json').read_text(encoding='utf-8'))
    (output/'assets').mkdir(parents=True,exist_ok=True)
    (output/'assets/contact.json').write_text(json.dumps({'address':contact.get('address')})+'\n',encoding='utf-8',newline='\n')
    (output/'.nojekyll').write_bytes(b'')
    print(f'Built allowlisted artifact: {len(files)+2} files')
