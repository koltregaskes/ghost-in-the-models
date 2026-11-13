"""Verify current pages and regeneration paths retain the supported CSP."""
from pathlib import Path
import importlib, subprocess
from security_policy import CSP
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent.parent
class Policy(HTMLParser):
    def __init__(self):
        super().__init__(); self.values=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta' and a.get('http-equiv','').lower()=='content-security-policy':
            self.values.append(a.get('content',''))
def verify(text, name):
    p=Policy(); p.feed(text)
    assert len(p.values)==1, (name,'one CSP required')
    assert p.values[0] == CSP, (name,'policy drift')
for name in subprocess.check_output(['git','ls-files','*.html'],cwd=ROOT,text=True).splitlines():
    verify((ROOT/name).read_text(encoding='utf-8'),name)
verify(importlib.import_module('harden-html').CSP_META,'hardening output')
r=importlib.import_module('rebuild-derived'); posts=r.load_posts()
verify(r.render_archive(posts,r.build_counts(posts)),'generated archive')
verify(r.render_tags(posts),'generated tags')
print('Security policy present on every route and in regeneration paths.')