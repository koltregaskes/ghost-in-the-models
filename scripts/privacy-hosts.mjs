// Complete references first, WHATWG URL parsing second. No hostname regex.
import {spawnSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';
import {sourceReferences, cssReferences, jsReferenceEntries, srcsetReferences} from './privacy-source-references.mjs';

const BASE='https://ghostinthemodels.com/';
const helper=fileURLToPath(new URL('./privacy-html-references.py',import.meta.url));
const fail=message=>{throw Error(message);};

function htmlBatch(values) {
  if(!values.length)return [];
  const output=spawnSync(process.platform==='win32'?'python':'python3',[helper,'--batch'],{input:JSON.stringify(values),encoding:'utf8',maxBuffer:32*1024*1024});
  if(output.error || output.status!==0)fail('Cannot extract complete HTML references');
  try{return JSON.parse(output.stdout);}catch{fail('Malformed HTML extraction result');}
}

function literals(source,kind) {
  if(kind==='js')return jsReferenceEntries(source);
  if(kind==='css')return cssReferences(source).map(value=>({value,resource:true}));
  if(kind==='srcset')return srcsetReferences(source).map(value=>({value,resource:true}));
  if(kind==='url')return [{value:source,resource:false}];
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

export function inspectSources(sources) {
  const html=htmlBatch(sources.filter(s=>s.kind==='html').map(s=>s.source));let htmlIndex=0;
  const all=new Set(),resources=new Set(),references=[];
  for(const file of sources) {
    const initial=file.baseURL || new URL(file.name || '',BASE).href;
    const parsed=file.kind==='html'?html[htmlIndex++]:null;
    const base=parsed?.base===null || parsed?.base===undefined ? complete(initial,BASE) : complete(parsed.base,initial);
    if(base.hostname)all.add(base.hostname);
    const entries=parsed?parsed.references.flatMap(ref=>literals(ref.value,ref.kind).map(v=>({...v,resource:ref.resource || v.resource,local:ref.kind==='url'||ref.kind==='srcset'||ref.kind==='css'}))):literals(file.source,file.kind);
    function inspect(entry,depth=0) {
      if(depth>3)fail('Unsupported recursive reference template');
      const value=entry.value;
      // HTML built by a JS string is parsed as HTML before its attribute URLs.
      if(/<[a-z!][\s\S]*>/i.test(value) && !/^data:/i.test(value)) {
        const nested=sourceReferences(value,'html');
        for(const ref of nested.values)inspect({value:ref,resource:entry.resource},depth+1);
        return;
      }
      const url=complete(value,base);
      if(url.hostname) {
        all.add(url.hostname);
        if(entry.resource)resources.add(url.hostname);
      }
      if(entry.local || file.kind==='css')references.push({name:file.name || '',url:url.href});
    }
    for(const entry of entries)inspect(entry);
    // Script-relative contact JSON is an actual same-origin fetch, unlike an
    // arbitrary string literal. Keep its source URL as the resolution base.
    if(file.kind==='js')for(const m of file.source.matchAll(/new URL\(\s*(['"])([^'"]+)\1\s*,\s*document\.currentScript\.src\s*\)/g)) {
      const url=complete(m[2],initial);references.push({name:file.name,url:url.href});
    }
  }
  return {hosts:[...all].sort(),resource_hosts:[...resources].sort(),references};
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try{process.stdout.write(JSON.stringify(inspectSources(JSON.parse(readFileSync(0,'utf8'))))+'\n');}
  catch{console.error('Cannot parse complete public references; malformed or unsupported input');process.exitCode=1;}
}
