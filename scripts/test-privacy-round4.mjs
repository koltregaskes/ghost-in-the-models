// Adapted from Photography cf0cabb's final two-layer/refresh regressions.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectSources} from './privacy-hosts.mjs';
import {backstopHosts,validateMentions} from './privacy-backstop.mjs';
import {htmlReferences,cssReferences,jsReferenceEntries,validateHtmlHelperOutput} from './privacy-source-references.mjs';

const file='index.html',host='evil.invalid';
const source=(text,kind='html',name=file)=>({name,kind,source:text});
const inspect=(text,kind='html',options)=>inspectSources([source(text,kind)],options);
const mention={kind:'non-request mention',file,host,reason:'Reviewed inert documentation comment.'};
const options={mentions:{version:1,mentions:[mention]}};
const comment='<!-- https://evil.invalid/reference -->';
const attr=value=>value.replaceAll('&','&amp;').replaceAll('"','&quot;');
const refresh=value=>`<meta http-equiv=refresh content="${attr(value)}">`;
const attacks=[
 ['comma refresh',refresh('0,url=https://evil.invalid/a')],
 ['srcdoc','<iframe srcdoc="&lt;img src=&quot;https://evil.invalid/a&quot;&gt;"></iframe>'],
 ['encoded srcdoc','<iframe srcdoc="&lt;img src=&quot;https://ev&amp;#105;l.invalid/a&quot;&gt;"></iframe>'],
 ['image-set','<style>body{background-image:image-set("https://evil.invalid/a" 1x)}</style>'],
 ['nested template','<script>const u=`${fetch(`https://evil.invalid/a`)}`;</script>'],
 ['twice-nested template','<script>const p=`outer ${`inner ${fetch(`https://evil.invalid/a`)}`}`;</script>'],
];
for(const [name,text] of attacks)test(name+' is found and cannot inherit an inert exception',()=>{
  assert.ok(inspect(text).hosts.includes(host));
  assert.ok(inspect(text).resource_hosts.includes(host));
  assert.ok(backstopHosts(text).has(host));
  assert.throws(()=>inspect(comment+text,'html',options));
});
test('structured extractors independently see the new loading contexts',()=>{
  assert.equal(htmlReferences(refresh('0,url=https://evil.invalid/a')).references[0].value,'https://evil.invalid/a');
  assert.equal(htmlReferences(attacks[1][1]).references[0].kind,'html');
  assert.deepEqual(cssReferences('a{background:image-set("https://evil.invalid/a" 1x)}'),['https://evil.invalid/a']);
  assert.ok(jsReferenceEntries('const u=`${fetch(`https://evil.invalid/a`)}`;').some(ref=>ref.value==='https://evil.invalid/a'&&ref.resource));
});
test('nested srcdoc resolves its own base and preserves resource roles',()=>{
  const text='<iframe srcdoc="&lt;iframe srcdoc=&quot;&amp;lt;base href=&amp;quot;http://ghostinthemodels.com/&amp;quot;&amp;gt;&amp;lt;img src=&amp;quot;https:/evil.invalid&amp;quot;&amp;gt;&quot;&gt;&lt;/iframe&gt;"></iframe>';
  assert.ok(inspect(text).resource_hosts.includes(host));
});
for(const separator of [';',','])for(const marker of ['','url=',' URL \t= '])for(const quote of ['',"'",'"']) {
  test('refresh grammar '+JSON.stringify({separator,marker,quote}),()=>{
    const destination=` \t1.5 ${separator} \n${marker}${quote}https://evil.invalid/a${quote} \r`;
    assert.ok(inspect(refresh(destination)).resource_hosts.includes(host));
    assert.throws(()=>inspect(comment+refresh(destination),'html',options));
    const declared=inspect(comment+refresh(destination.replace('evil.invalid','fonts.gstatic.com')),'html',options);
    assert.ok(declared.resource_hosts.includes('fonts.gstatic.com'));
  });
}
for(const content of ['0,url','0;url https://evil.invalid/a','0,urlhttps://evil.invalid/a',',url=https://evil.invalid/a','later,url=https://evil.invalid/a','0:url=https://evil.invalid/a','0 url=https://evil.invalid/a','0,,url=https://evil.invalid/a','0;;url=https://evil.invalid/a','0,url="https://evil.invalid/a','0,url="https://evil.invalid/a" trailing'])test('unsupported refresh fails closed '+content.slice(0,18),()=>assert.throws(()=>inspect(comment+refresh(content),'html',options)));
for(const content of ['0','1.5','0;','0,','0;url=','0,url=""'])test('same-page refresh keeps inert exception '+content,()=>assert.ok(!inspect(comment+refresh(content),'html',options).hosts.includes(host)));
test('refresh retains URL punctuation and userinfo',()=>assert.ok(inspect(refresh('0,url="https://fonts.gstatic.com;@evil.invalid/a?one=1,two=2"')).hosts.includes(host)));
for(const [kind,text] of [
 ['html',comment],['html','<p>https://evil.invalid/reference</p>'],
 ['css','/* https://evil.invalid/reference */'],['js','// https://evil.invalid/reference'],
 ['js',String.raw`// https:\/\/evil.invalid/a`],['js',String.raw`// https:\x2f\x2fevil.invalid/a`],
 ['js',String.raw`// https:\u002f\u002fevil.invalid/a`],['css',String.raw`/* https:\2f \2f evil.invalid/a */`],
 ['html','<!-- https&colon;&sol;&sol;evil.invalid/a -->'],
 ['html','<!-- //evil.invalid/a -->'],['html','<!-- ftp://evil.invalid/a -->'],
])test('independent backstop catches '+kind+' '+text.slice(0,24),()=>assert.ok(inspect(text,kind).hosts.includes(host)));
test('a reviewed inert mention passes but active or unused entries fail',()=>{
  assert.ok(!inspect(comment,'html',options).hosts.includes(host));
  assert.throws(()=>inspect('<img src="https://evil.invalid/a">','html',options));
  assert.throws(()=>inspect('','html',options));
  assert.throws(()=>inspectSources([source(comment,'html','privacy.html')],options));
});
test('split network prefix fails instead of accepting a partial URL',()=>assert.throws(()=>inspect('fetch("https://"+"evil.invalid/a")','js')));
test('backstop keeps source token boundaries while WHATWG removes internal URL newlines',()=>{
  assert.deepEqual([...backstopHosts('generated:\n// 847 lines of code')],[]);
  assert.ok(backstopHosts('https://ev\nil.invalid/a').has(host));
});
test('dynamic external template fails explicitly',()=>assert.throws(()=>inspect('fetch(`https://${host}/a`)','js')));
const valid={base:null,references:[{kind:'url',value:'/local',resource:true}],decodedText:'x'};
for(const mutant of [null,[],{}, {...valid,base:false},{...valid,references:{}},{...valid,decodedText:false},{...valid,extra:[]},{...valid,references:[{kind:'url',value:'/x'}]},{...valid,references:[{kind:'url',value:'/x',resource:'true'}]},{...valid,references:[{kind:'unknown',value:'/x',resource:false}]},{...valid,references:[null]}])test('helper schema fails closed '+JSON.stringify(mutant),()=>assert.throws(()=>validateHtmlHelperOutput(mutant)));
test('helper schema accepts exact supported shapes',()=>{
  assert.equal(validateHtmlHelperOutput(valid),valid);
  assert.deepEqual(validateHtmlHelperOutput({decodedText:'x'},true),{decodedText:'x'});
  assert.throws(()=>validateHtmlHelperOutput({base:null,decodedText:'x'},true));
});
for(const mutant of [{...mention,reason:''},{...mention,file:'*'},{...mention,file:'../site.js'},{...mention,host:'https://evil.invalid'},{...mention,extra:true}])test('invalid mention entry '+JSON.stringify(mutant),()=>assert.throws(()=>validateMentions({version:1,mentions:[mutant]})));
test('actual CLI diagnostics redact input URLs and synthetic userinfo',()=>{
  const payload={sources:[source('<img src="https://sample-reader:example-only@">')],mentions:{version:1,mentions:[]}};
  const result=spawnSync(process.execPath,[fileURLToPath(new URL('./privacy-hosts.mjs',import.meta.url))],{input:JSON.stringify(payload),encoding:'utf8'});
  assert.equal(result.status,1);assert.doesNotMatch(result.stdout+result.stderr,/https?:|\/\/|sample-reader|example-only|@/i);
});
for(const [label,payload] of [
  ['missing base',[{references:[],decodedText:'x'}]],
  ['false base',[{base:false,references:[],decodedText:'x'}]],
  ['empty decoded output',[{base:null,references:[],decodedText:''}]],
  ['wrong batch length',[]],
  ['unknown role',[{base:null,references:[{kind:'url',value:'/',resource:'yes'}],decodedText:'x'}]],
])test('actual checker rejects malformed batch helper output: '+label,async()=>{
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'gitm-parser-schema-'));
  // Keep fixtures in the test temporary directory; no site code is executed.
  await fs.writeFile(path.join(directory,'package.json'),'{"type":"module"}');
  for(const name of ['privacy-hosts.mjs','privacy-source-references.mjs','privacy-backstop.mjs','privacy-data-documents.mjs'])await fs.copyFile(fileURLToPath(new URL(name,import.meta.url)),path.join(directory,name));
  await fs.writeFile(path.join(directory,'privacy-html-references.py'),'import sys\nsys.stdout.write('+JSON.stringify(JSON.stringify(payload))+')\n');
  const input={sources:[source('<img src="https://evil.invalid/a">')],mentions:{version:1,mentions:[]}};
  const result=spawnSync(process.execPath,[path.join(directory,'privacy-hosts.mjs')],{input:JSON.stringify(input),encoding:'utf8'});
  assert.equal(result.status,1);assert.doesNotMatch(result.stdout+result.stderr,/https?:|\/\/|evil\.invalid/i);
});
const retained=JSON.parse(await fs.readFile(new URL('./fixtures/privacy-review-regressions.json',import.meta.url),'utf8'));
for(const row of retained.cases)test('Photography retained review case '+row.id,()=>{
  let failed=false;
  try {
    const kind=path.extname(row.file).slice(1);
    const result=inspectSources([{name:row.file,kind,source:row.source,baseURL:row.base}]);
    const allowed=new Set([new URL(row.base).hostname,...row.allowedHosts]);
    failed=result.hosts.some(host=>!allowed.has(host));
  } catch {failed=true;}
  assert.equal(failed,row.expected==='fail','Retained review case '+row.id);
});
