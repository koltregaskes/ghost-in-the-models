import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inspectSources} from './privacy-hosts.mjs';
import {decodeDataURL,MAX_DOCUMENT_DEPTH} from './privacy-data-documents.mjs';
import {htmlReferences,decodeReferenceText} from './privacy-source-references.mjs';

const probes=JSON.parse(readFileSync(new URL('./fixtures/privacy-guard-parity-probes.json',import.meta.url),'utf8'));
const inventory=JSON.parse(readFileSync(new URL('../config/privacy-hosts.json',import.meta.url),'utf8'));
const declared=new Set(Object.values(inventory).flat());
const resourceAllowed=new Set([...inventory.site_hosts,...inventory.resource_hosts]);
const inspect=(source,mentions,kind='html')=>inspectSources([{name:'index.html',kind,source}],{mentions:mentions??{version:1,mentions:[]}});
const mention=host=>({version:1,mentions:[{kind:'non-request mention',file:'index.html',host,reason:'Regression: cannot exempt an active view.'}]});
const data=(type,source,base64=false)=>`data:${type}${base64?';base64':''},${base64?Buffer.from(source).toString('base64'):encodeURIComponent(source)}`;
const attr=value=>value.replaceAll('&','&amp;').replaceAll('"','&quot;');
const script=url=>`<script src="${attr(url)}"></script>`;
const sheet=url=>`<link rel="stylesheet" href="${attr(url)}">`;
const importData=url=>inspect(`import(${JSON.stringify(url)})`,undefined,'js');

for(const row of probes)test(`retained ${row.probe}: ${row.label}`,()=>{
    let result;
    try{result=inspectSources([{name:row.name,kind:row.kind,source:row.source}],{mentions:row.mentions??{version:1,mentions:[]}});}
    catch(error){if(row.expected.startsWith('reject-or-'))return;throw error;}
    if(row.expected==='reject-or-resource')assert.ok(result.resource_hosts.some(host=>!resourceAllowed.has(host)),'navigation permission must not authorise a load');
    else if(row.expected==='reject-or-host')assert.ok(result.hosts.some(host=>!declared.has(host)),'unreviewed host must remain visible');
    else if(row.expected==='inert-mention')assert.ok(!result.hosts.includes('evil.invalid'));
    else assert.ok(result.resource_hosts.every(host=>resourceAllowed.has(host)),'retain the original control and documented indirect-JS limit');
});

// Independent list so accidentally removing an implementation alias fails a test.
const aliases=['application/ecmascript','application/javascript','application/x-ecmascript','application/x-javascript','text/ecmascript','text/javascript','text/javascript1.0','text/javascript1.1','text/javascript1.2','text/javascript1.3','text/javascript1.4','text/javascript1.5','text/jscript','text/livescript','text/x-ecmascript','text/x-javascript'];
for(const alias of aliases)test('browser JavaScript MIME alias '+alias,()=>{
    for(const base64 of [false,true]){
        const type=' '+alias.toUpperCase()+' ;charset=utf-8';
        assert.ok(importData(data(type,"fetch('https://x.com/t')",base64)).resource_hosts.includes('x.com'));
        assert.throws(()=>inspect(`import(${JSON.stringify(data(type,"fetch('https://evil.invalid/t')",base64))})`,mention('evil.invalid'),'js'));
    }
});
for(const type of ['text/css','TEXT/CSS',' text/css ;charset=utf-8','text/css\t;charset="UTF-8"'])test('CSS MIME syntax '+JSON.stringify(type),()=>{
    for(const base64 of [false,true])assert.ok(inspect(sheet(data(type,'@import url(https://github.com/a.css);',base64))).resource_hosts.includes('github.com'));
});
for(const target of ['href','HREF','xlink:href','XLINK:HREF','custom:HrEf'])for(const name of ['set','animate'])test('SMIL rejects '+name+' '+target,()=>{
    for(const attribute of ['to','from','by','values'])assert.throws(()=>inspect(`<svg><image href="/a.png"><${name} attributeName="${target}" ${attribute}="https://github.com/a.png"/></image></svg>`));
});
test('SMIL prefixes and duplicate target spellings cannot hide href',()=>{
    assert.throws(()=>inspect('<svg><svg:animate ns:attributeName="XLINK:HrEf" values="/a;https://x.com/t"/></svg>'));
    assert.throws(()=>inspect('<svg><set a:attributeName="fill" attributeName="href" to="https://x.com/t"/></svg>'));
});
for(const tag of ['script','style','title','desc','foreignObject','mi','mo','mn','ms','mtext','annotation-xml','noscript','template','textarea','xmp','iframe','noembed','noframes','plaintext'])test('foreign-content context rejects '+tag,()=>{
    for(const root of ['svg','math'])assert.throws(()=>inspect(`<${root}><${tag}><img src="https://github.com/a.png"></${tag}></${root}>`));
});
test('foreign-content rejection remains conservative after closing the root',()=>assert.throws(()=>inspect('<svg></svg><style>body{color:red}</style>')));
test('ordinary SVG, non-URL SMIL, navigation and allowed data resources remain valid',()=>{
    assert.ok(inspect('<svg><image href="https://fonts.gstatic.com/a.png"/><animate attributeName="fill" to="red"/></svg>').resource_hosts.includes('fonts.gstatic.com'));
    assert.ok(!inspect('<a href="https://x.com/t">Link</a>').resource_hosts.includes('x.com'));
    assert.ok(inspect(sheet(data('text/css','a{background:url(https://fonts.gstatic.com/a)}'))).resource_hosts.includes('fonts.gstatic.com'));
    assert.ok(importData(data('text/javascript',"fetch('https://fonts.gstatic.com/t')")).resource_hosts.includes('fonts.gstatic.com'));
    assert.doesNotThrow(()=>inspect('<img src="data:image/png;base64,iVBORw0KGgo=">'));
});
for(const [kind,body] of [['text/css','/* x_https://evil.invalid/a */'],['text/javascript','// x_https://evil.invalid/a'],['text/html','<!-- x_https://evil.invalid/a -->']])test('decoded '+kind+' backstop host cannot inherit a mention',()=>{
    const url=data(kind,body,true),source=kind==='text/css'?sheet(url):`<iframe src="${url}"></iframe>`;
    assert.ok(inspect(source).hosts.includes('evil.invalid'));
    assert.throws(()=>inspect(source,mention('evil.invalid')));
});
test('data CSS and JS recurse through HTML, CSS imports and JS imports',()=>{
    const css=data(' text/css ;charset=utf-8','@import "'+data('text/css','a{background:url(https://github.com/a.png)}',true)+'";',true);
    const html=data('text/html',sheet(css),true);
    assert.ok(inspect(`<iframe src="${html}"></iframe>`).resource_hosts.includes('github.com'));
    const js=data('text/javascript','import("'+data('text/jscript',"fetch('https://x.com/t')",true)+'")',true);
    assert.ok(importData(js).resource_hosts.includes('x.com'));
});
for(const value of ['data:text/css,%GG','data:text/css,%ff','data:text/javascript;base64,@@@','data:text/jscript,%00','data:text/css;charset=iso-8859-1,a{}','data:text/css,@charset%20%22utf-16%22;','data:application/xhtml+xml,<html/>','data:application/xml,<x/>','data:text/plain,fetch(1)','data:application/unknown,anything','data:,fetch(1)'])test('data resource fails closed '+value,()=>assert.throws(()=>inspect(sheet(value))));
test('data CSS depth limit rejects excessive imports',()=>{
    let url=data('text/css','a{color:red}');
    for(let depth=0;depth<=MAX_DOCUMENT_DEPTH;depth++)url=data('text/css',`@import "${url}";`,true);
    assert.throws(()=>inspect(sheet(url)));
});
test('parser cache keeps content, mode, mutation and entity limits separate',()=>{
    const source='<img src="https://x.com/t">';
    const first=htmlReferences(source);first.references[0].value='https://allowed.invalid/';
    assert.equal(htmlReferences(source).references[0].value,'https://x.com/t');
    assert.equal(decodeReferenceText(source),source);
    assert.equal(decodeReferenceText('&amp;amp;'),'&');
    assert.equal(decodeReferenceText('&amp;lt;'),'<' ,'changing tokens must retain decoding across token boundaries');
    assert.throws(()=>decodeReferenceText('&'+'amp;'.repeat(20)));
    assert.ok(inspect(source).resource_hosts.includes('x.com'));
    assert.ok(!inspect('<p>Local</p>').resource_hosts.includes('x.com'));
});
test('backstop data bodies outside recognised attributes cannot use mentions',()=>{
    const source='<!-- '+data('text/plain','x_https://evil.invalid/a',true)+' -->';
    assert.ok(inspect(source).hosts.includes('evil.invalid'));
    assert.throws(()=>inspect(source,mention('evil.invalid')));
});
test('URL whitespace cannot send a data stylesheet through HTML-string parsing',()=>{
    const url=' \t'+data('text/css','/* <b> */ @import "https://github.com/a.css";');
    assert.ok(inspect(sheet(url)).resource_hosts.includes('github.com'));
});
for(const render of [url=>`import(/* comment */ ${JSON.stringify(url)})`,url=>`import ${JSON.stringify(url)}`,url=>`import * as item from ${JSON.stringify(url)}`,url=>`export * from ${JSON.stringify(url)}`,url=>`fetch(/* comment */ ${JSON.stringify(url)})`])test('direct resource syntax inspects data JS: '+render('URL'),()=>{
    assert.ok(inspect(render(data('text/javascript',"fetch('https://x.com/t')",true)),undefined,'js').resource_hosts.includes('x.com'));
    assert.throws(()=>inspect(render(data('text/javascript',"fetch('https://evil.invalid/t')",true)),mention('evil.invalid'),'js'));
});
for(const mime of [...aliases,'text/css','text/plain','application/unknown',''])test('script data boundary rejects any MIME: '+(mime||'omitted'),()=>{
    for(const tag of ['script','SCRIPT','svg:script'])for(const attribute of ['src','href','xlink:href']){
        const element=`<${tag} ${attribute}="${data(mime,"fetch('https://x.com/t')",true)}"></${tag}>`;
        assert.throws(()=>inspect(element));
        assert.throws(()=>inspect(`<iframe srcdoc="${attr(element)}"></iframe>`));
    }
});
test('script data boundary applies URL whitespace and HTML entity decoding',()=>{
    assert.throws(()=>inspect('<script src=" &#9;d&#97;ta&colon;text/plain,fetch(1)"></script>'));
    assert.throws(()=>inspect('<script href="da&#10;ta:,fetch(1)"></script>'));
});
test('actual SVG script data attributes also reject inside srcdoc',()=>{
    for(const type of ['text/x-javascript','application/x-ecmascript','text/jscript',''])for(const attribute of ['src','href','xlink:href']){
        const element=`<svg><script ${attribute}="${data(type,"fetch('https://x.com/t')")}"></script></svg>`;
        assert.throws(()=>inspect(element));
        assert.throws(()=>inspect(`<iframe srcdoc="${attr(element)}"></iframe>`));
    }
});
test('entity decoding remains correct beyond the cache capacity',()=>{
    const source=Array.from({length:129},(_,i)=>`&review129token${i};`).join(' ');
    assert.equal(decodeReferenceText(source),source);
});
test('SVG XML namespace aliases cannot evade foreign/script boundaries',()=>{
    const xml='<s:svg xmlns:s="http://www.w3.org/2000/svg" xmlns:x="http://www.w3.org/1999/xlink"><s:script x:href="'+data('text/plain',"fetch('https://x.com/t')",true)+'"/></s:svg>';
    assert.throws(()=>inspect(`<iframe src="${data('image/svg+xml',xml,true)}"></iframe>`));
    assert.throws(()=>inspect('<s:script x:href="data:,fetch(1)"/>'));
    assert.throws(()=>inspect('<s:svg><s:style><img src="https://github.com/a.png"></s:style></s:svg>'));
    assert.ok(inspect('<s:svg xmlns:s="http://www.w3.org/2000/svg" xmlns:x="http://www.w3.org/1999/xlink"><s:image x:href="https://github.com/a.png"/></s:svg>').resource_hosts.includes('github.com'));
});
for(const source of ['<svg><noscript><img src="https://github.com/a.png"></noscript></svg>','<svg><template><img src="https://github.com/a.png"></template></svg>','<math><mi><svg><style><img src="https://github.com/a.png"></style></svg></mi></math>','<svg><foreignObject><img src="https://github.com/a.png"></foreignObject></svg>','<svg><desc><img src="https://github.com/a.png"></desc></svg>','<SVG><STYLE><IMG SRC="https://github.com/a.png"></STYLE></SVG>','<![CDATA[ > <img src="https://github.com/a.png">'])test('StackScout parity rejects '+source.slice(0,35),()=>assert.throws(()=>inspect(source)));
