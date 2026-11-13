#!/usr/bin/env python3
"""Check links, assets, downloads and redirect safety without treating outages as success."""
import argparse
import ipaddress
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT=Path(__file__).resolve().parent.parent
SITE='https://ghostinthemodels.com/'
class References(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.add(a['id'])
        if tag=='a' and a.get('name'): self.ids.add(a['name'])
        if tag=='link' and set(a.get('rel','').lower().split()) & {'preconnect','dns-prefetch'}: return
        for key in ('href','src','poster'):
            if a.get(key): self.refs.append(a[key])
        if a.get('srcset') and not a['srcset'].startswith('data:'):
            self.refs.extend(part.strip().split()[0] for part in a['srcset'].split(',') if part.strip())

def unsafe_url(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https'): return 'unsupported destination scheme'
    if p.username or p.password: return 'credentials in URL'
    host=(p.hostname or '').lower()
    if not host or host=='localhost' or host.endswith(('.localhost','.local')): return 'non-public destination'
    try:
        if not ipaddress.ip_address(host).is_global: return 'non-public IP destination'
    except ValueError: pass
    return None

class UnsafeRedirect(Exception): pass
class SafeRedirects(HTTPRedirectHandler):
    max_redirections=5
    def http_error_302(self,req,fp,code,msg,headers):
        # urllib rejects file: before redirect_request; classify it as unsafe first.
        target=headers.get('location') or headers.get('uri')
        if target and urlsplit(target).scheme not in ('','http','https'):
            if fp is not None: fp.close()
            raise UnsafeRedirect('unsupported destination scheme')
        return super().http_error_302(req,fp,code,msg,headers)
    http_error_301=http_error_303=http_error_307=http_error_308=http_error_302
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        reason=unsafe_url(newurl)
        if urlsplit(req.full_url).scheme=='https' and urlsplit(newurl).scheme!='https': reason='HTTPS downgrade'
        if reason: raise UnsafeRedirect(reason)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def printable(url):
    p=urlsplit(url)
    return f'{p.scheme}://{p.hostname or ""}{p.path}'

def check_external(url):
    reason=unsafe_url(url)
    if reason: return ('error',f'Unsafe destination: {reason} {printable(url)}')
    try:
        with build_opener(SafeRedirects()).open(Request(url,headers={'User-Agent':'GhostInTheModelsLinkCheck/2.0'}),timeout=12) as response:
            end=response.geturl()
            return ('ok',f'{response.status} {printable(url)}' + (f' -> {printable(end)}' if end!=url else ''))
    except UnsafeRedirect as exc: return ('error',f'Unsafe redirect: {exc} {printable(url)}')
    except HTTPError as exc:
        return ('error' if exc.code in (404,410) else 'unknown',f'HTTP {exc.code} {printable(url)}')
    except (URLError,TimeoutError,OSError,ValueError) as exc:
        return ('unknown',f'Unconfirmed ({type(exc).__name__}) {printable(url)}')

def local_target(source,ref):
    absolute=urljoin(SITE+source.relative_to(ROOT).as_posix(),ref)
    p=urlsplit(absolute)
    if p.netloc not in ('ghostinthemodels.com','www.ghostinthemodels.com'): return None
    clean=unquote(p.path).lstrip('/')
    if clean.startswith('ghost-in-the-models/'): clean=clean[len('ghost-in-the-models/'):]
    target=(ROOT/clean).resolve()
    if not target.is_relative_to(ROOT.resolve()): raise ValueError('path escapes publication')
    if target.is_dir(): target=target/'index.html'
    return target,unquote(p.fragment)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--external',action='store_true'); args=parser.parse_args()
    names=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    files=[ROOT/name for name in names if name.endswith('.html')]
    parsed={}
    for file in files:
        page=References(); page.feed(file.read_text(encoding='utf-8')); parsed[file.resolve()]=page
    errors=[]; external=set(); downloads=set()
    for source,page in parsed.items():
        for ref in page.refs:
            if ref.startswith(('data:','mailto:','tel:')): continue
            if ref.lower().startswith('javascript:'):
                errors.append(f'Unsafe script URL in {source.relative_to(ROOT)}'); continue
            try: local=local_target(source,ref)
            except ValueError as exc:
                errors.append(f'{source.relative_to(ROOT)}: {exc}'); continue
            if local is None:
                external.add(urljoin(SITE+source.relative_to(ROOT).as_posix(),ref).split('#')[0]); continue
            target,fragment=local
            if not target.is_file(): errors.append(f'Missing destination: {source.relative_to(ROOT)} -> {ref}')
            elif target.suffix.lower() not in ('.html','.css','.js','.json','.png','.webp','.svg','.mp4','.woff2','.xml','.txt'):
                downloads.add(target)
            if fragment and target.suffix=='.html' and target.resolve() in parsed and fragment not in parsed[target.resolve()].ids:
                errors.append(f'Missing fragment: {source.relative_to(ROOT)} -> {ref}')
    # Include destinations inserted by the shared navigation scripts.
    for name in names:
        if name.endswith('.js'):
            external.update(re.findall(r'https?://[^\s\x22\x27<>`]+', (ROOT/name).read_text(encoding='utf-8')))
    outcomes=[]
    if args.external:
        with ThreadPoolExecutor(max_workers=8) as pool: outcomes=list(pool.map(check_external,sorted(external)))
        for state,detail in outcomes:
            if state=='error': errors.append(detail)
            elif state=='unknown': print('UNKNOWN '+detail)
            elif ' -> ' in detail: print('REDIRECT '+detail)
    for error in sorted(set(errors)): print('ERROR '+error)
    unknown=sum(state=='unknown' for state,_ in outcomes)
    print(f'Checked {len(files)} HTML routes, {len(downloads)} local downloads, {len(outcomes)} external destinations: {len(set(errors))} errors, {unknown} unconfirmed.')
    return 1 if errors else 0
if __name__=='__main__': raise SystemExit(main())