// Complete references first, WHATWG URL parsing second. No hostname regex.
import {pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';
import {htmlReferences, batchReferences, cssReferences, jsReferenceEntries, srcsetReferences} from './privacy-source-references.mjs';
import {backstopHosts,validateMentions} from './privacy-backstop.mjs';
import {decodeDataURL,MAX_DOCUMENT_DEPTH} from './privacy-data-documents.mjs';

const BASE='https://ghostinthemodels.com/';
const fail=message=>{throw Error(message);};

function literals(source,kind) {
  if(kind==='js')return jsReferenceEntries(source);
  if(kind==='css')return cssReferences(source).map(value=>({value,resource:true}));
  if(kind==='srcset')return srcsetReferences(source).map(value=>({value,resource:true}));
  if(kind==='url')return [{value:source,resource:false}];
  if(kind==='load-url'||kind==='document-url')return [{value:source,resource:true,document:kind==='document-url'}];
  if(kind==='text') {
    // Text/XML/Markdown discovery files are navigation/metadata. Extract complete
    // element text, attribute values or Markdown link destinations, never an
    // authority substring. The loading surfaces use the parsers above.
    const values=[];
    for(const m of source.matchAll(/\]\(([^)]+)\)|(?:^|>)\s*((?:https?:)?\/\/[^<\r\n]+)|["']((?:https?:)?\/\/[^"']+)["']/gm))values.push({value:(m[1]||m[2]||m[3]).trim(),resource:false});
    for(const line of source.split(/\r?\n/)) {
      const m=line.match(/^(?:Contact:|Canonical:)?\s*((?:https?:)?\/\/\S+)\s*$/i);
      if(m)values.push({value:m[1],resource:false});
    }
    return values;
  }
  fail('Unsupported reference source kind');
}

function complete(value,base) {
  if(typeof value!=='string')fail('Non-string URL reference');
  const clean=value.replace(/[\t\n\r]/g,'').replace(/^[\x00-\x20]+|[\x00-\x20]+$/g,'');
  // Never treat a partial external template as a valid relative reference.
  if(clean.includes('${') && /(?:https?:|wss?:|^[\\/]{2})/i.test(clean))fail('Dynamic external URL template requires explicit review');
  let url;
  try{url=new URL(value,base);}catch{fail('Malformed complete URL reference');}
  if(!url.hostname && /^(?:https?:|wss?:|[\\/]{2})/i.test(clean))fail('External reference has no hostname');
  return url;
}

export function inspectSources(sources,{mentions={version:1,mentions:[]}}={}) {
  if(!Array.isArray(sources)||sources.some(file=>!file||typeof file.name!=='string'||typeof file.source!=='string'||!['html','js','css','text','url'].includes(file.kind)||file.baseURL!==undefined&&typeof file.baseURL!=='string'))fail('Invalid public source batch');
  const exceptions=validateMentions(mentions),used=new Set();
  const extracted=batchReferences(sources);
  const all=new Set(),resources=new Set(),references=[];
  for(const [index,file] of sources.entries()) {
    const initial=file.baseURL || new URL(file.name || '',BASE).href;
    const structured=new Set();
    function remember(url,resource=false) {
      if(url.hostname){structured.add(url.hostname);all.add(url.hostname);if(resource)resources.add(url.hostname);}
    }
    function activeBackstop(source,base,resource=true) {
      // Inside a parsed CSS/JS or decoded data view, even a backstop-only host
      // cannot inherit an inert mention. Conservatively give it a resource role.
      for(const host of backstopHosts(source,{baseURL:base})) {
        structured.add(host);all.add(host);if(resource)resources.add(host);
      }
    }
    function document(parsed,initialBase,depth) {
      if(depth>MAX_DOCUMENT_DEPTH)fail('Nested HTML exceeds the inspection limit');
      const base=complete(parsed.base??initialBase,initialBase);
      remember(base);
      for(const ref of parsed.references) {
        if(ref.kind==='html'){document(htmlReferences(ref.value),base.href,depth+1);continue;}
        for(const entry of literals(ref.value,ref.kind))inspect({...entry,resource:ref.resource||entry.resource,local:['url','load-url','document-url','srcset','css'].includes(ref.kind)},base,depth);
      }
    }
    function inspect(entry,base,depth=0) {
      if(depth>MAX_DOCUMENT_DEPTH)fail('Unsupported recursive reference template');
      const value=entry.value;
      // HTML built by a JS string is parsed as HTML before its attribute URLs.
      if(/<[a-z!][\s\S]*>/i.test(value) && !/^data:/i.test(value.replace(/[\t\n\r]/g,'').replace(/^[\x00-\x20]+/,''))) {
        document(htmlReferences(value),base.href,depth+1);
        return;
      }
      const url=complete(value,base);
      if(entry.resource&&url.protocol==='data:'){
        const embedded=decodeDataURL(url.href,{resource:true});
        if(embedded.kind){
          if(depth>=MAX_DOCUMENT_DEPTH)fail('Data resource exceeds the inspection limit');
          activeBackstop(embedded.source,base.href,embedded.kind!=='html');
          if(embedded.kind==='html')document(htmlReferences(embedded.source),base.href,depth+1);
          else for(const ref of literals(embedded.source,embedded.kind))inspect({...ref,resource:true,local:true},base,depth+1);
        }
      }
      remember(url,entry.resource);
      if(entry.local || file.kind==='css')references.push({name:file.name || '',url:url.href});
    }
    const base=complete(initial,BASE);
    if(file.kind==='html')document(extracted[index],base.href,0);
    else {remember(base);for(const entry of literals(file.source,file.kind))inspect(entry,base);}
    // Script-relative contact JSON is an actual same-origin fetch, unlike an
    // arbitrary string literal. Keep its source URL as the resolution base.
    if(file.kind==='js')for(const m of file.source.matchAll(/new URL\(\s*(['"])([^'"]+)\1\s*,\s*document\.currentScript\.src\s*\)/g)) {
      const url=complete(m[2],initial);references.push({name:file.name,url:url.href});
    }
    const decodedHosts=new Set();
    const swept=backstopHosts(file.source,{baseURL:base.href,decodedText:extracted[index].decodedText,decodedHosts});
    for(const host of decodedHosts)structured.add(host);
    for(const host of swept) {
      const exception=exceptions.find(entry=>entry.file===file.name&&entry.host===host);
      if(exception&&!structured.has(host))used.add(exception);
      else all.add(host);
    }
    // An entry is never allowed to excuse an active host, even when that host
    // is also reviewed elsewhere in the inventory. Require its removal.
    if(exceptions.some(entry=>entry.file===file.name&&structured.has(entry.host)))fail('Active reference cannot use a non-request mention exception');
  }
  if(exceptions.some(entry=>!used.has(entry)))fail('Unused non-request mention exception');
  return {hosts:[...all].sort(),resource_hosts:[...resources].sort(),references};
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try{
    const payload=JSON.parse(readFileSync(0,'utf8'));
    if(!payload||Array.isArray(payload)||Object.keys(payload).sort().join('|')!=='mentions|sources')fail('Invalid inspection input');
    process.stdout.write(JSON.stringify(inspectSources(payload.sources,{mentions:payload.mentions}))+'\n');
  }
  catch{console.error('Cannot parse complete public references; malformed or unsupported input');process.exitCode=1;}
}
