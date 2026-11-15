"""Offline artifact closure, host inventory and hostile URL regressions."""
import importlib.util
import json
import re
import tempfile
import unittest
import argparse
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit,unquote
from public_output import allowed,hosts,inspect_sources

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('build_public',ROOT/'scripts/build-public.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
BASE='https://ghostinthemodels.com/'


class FooterLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.footers=[];self.in_footer=False
    def handle_starttag(self,tag,attrs):
        a={}
        for key,value in attrs:
            if key not in a:a[key]=value
        if tag=='footer':self.in_footer=True;self.footers.append([])
        if self.in_footer and tag=='a':self.footers[-1].append(a.get('href',''))
    def handle_endtag(self,tag):
        if tag=='footer':self.in_footer=False


def check_artifact(output,inventory):
    files=[p for p in output.rglob('*') if p.is_file()]
    assert files,'Empty artifact'
    declared=set().union(*[set(v) for v in inventory.values()])
    found=set();resource_hosts=set();pages=0;references=0;sources=[]
    for p in files:
        name=p.relative_to(output).as_posix()
        assert allowed(name),('Unlisted artifact file',name)
        assert not p.is_symlink(),name
        if p.suffix not in {'.html','.css','.js','.svg','.xml','.txt','.md','.json'}:continue
        text=p.read_text(encoding='utf-8')
        kind='html' if p.suffix=='.svg' else p.suffix[1:] if p.suffix in {'.html','.js','.css'} else 'text'
        sources.append(dict(name=name,kind=kind,source=text))
        if p.suffix=='.html':
            pages+=1;parser=FooterLinks();parser.feed(text)
            for footer in parser.footers:assert any(urlsplit(r).path.endswith('privacy.html') for r in footer),('Footer privacy link missing',name)
    inspected=inspect_sources(sources)
    found.update(inspected['hosts']);resource_hosts.update(inspected['resource_hosts'])
    for ref in inspected['references']:
        url=urlsplit(ref['url']);name=ref['name']
        if url.hostname not in {'ghostinthemodels.com','www.ghostinthemodels.com'}:continue
        path=unquote(url.path).lstrip('/')
        if path.startswith('ghost-in-the-models/'):path=path[len('ghost-in-the-models/'):]
        target=(output/path).resolve()
        assert output.resolve() in target.parents or target==output.resolve(),('Reference escaped artifact',name)
        if target.is_dir():target=target/'index.html'
        assert target.is_file(),('Broken artifact reference',name,path)
        references+=1
    assert not found-declared,('Unlisted public URL hosts',sorted(found-declared))
    assert not resource_hosts-set(inventory['resource_hosts'])-set(inventory['site_hosts']),('Undisclosed resource hosts',sorted(resource_hosts))
    # Font CSS itself is fetched from Google and references its static host.
    privacy=(output/'privacy.html').read_text(encoding='utf-8')
    for host in inventory['resource_hosts']:assert host in privacy,('Missing privacy disclosure',host)
    print(f'Artifact verified: {len(files)} files, {pages} pages, {references} local references; {len(found)} URL hosts; no unlisted hosts or files')
    return len(files)


class OutputTests(unittest.TestCase):
    def test_url_boundaries(self):
        for suffix in ['/path','?q=x','#fragment',':8443/path']:
            self.assertEqual(hosts('HTTPS://Example.COM'+suffix),{'example.com'})
        self.assertEqual(hosts('//reader@example.com:8443/a'),{'example.com'})
        self.assertEqual(hosts('https://reader:label@EXAMPLE.COM:8443/a'),{'example.com'})
        self.assertEqual(hosts('WSS://Example.COM:443/path'),{'example.com'})
        with self.assertRaises(ValueError):hosts('https://')

    def test_allowlist(self):
        for name in ['drafts/test.html','publish-queue/test.html','scripts/test.js','config/contact.json','docs/x.html','.git/config','assets/.hidden.js','assets/../drafts/x.js','preview/option-a.html','assets/test.env','assets/test.key']:
            self.assertFalse(allowed(name),name)

    def test_artifact_and_negative_guards(self):
        inventory=json.loads((ROOT/'config/privacy-hosts.json').read_text())
        with tempfile.TemporaryDirectory() as raw:
            output=Path(raw)/'public';builder.build(ROOT,output)
            check_artifact(output,inventory)
            (output/'assets/injected.js').write_text('fetch("//UNLISTED.example:443/path")',encoding='utf-8')
            with self.assertRaises(AssertionError):check_artifact(output,inventory)
            (output/'assets/injected.js').write_text('',encoding='utf-8')
            index=output/'index.html';original=index.read_text(encoding='utf-8')
            index.write_text(original+'<a href="drafts/missing.html">Broken local reference</a>',encoding='utf-8')
            with self.assertRaises(AssertionError):check_artifact(output,inventory)
            index.write_text(original,encoding='utf-8')
            (output/'assets/injected.js').write_text('fetch("https://x.com/active")',encoding='utf-8')
            with self.assertRaises(AssertionError):check_artifact(output,inventory)
            (output/'assets/injected.js').write_text('',encoding='utf-8')
            (output/'queue.html').write_text('private',encoding='utf-8')
            with self.assertRaises(AssertionError):check_artifact(output,inventory)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path);args,remaining=parser.parse_known_args()
    if args.artifact:check_artifact(args.artifact.resolve(),json.loads((ROOT/'config/privacy-hosts.json').read_text()))
    else:unittest.main(argv=['test-public-output.py']+remaining)
