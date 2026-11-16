import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const htmlHelper=fileURLToPath(new URL('./privacy-html-references.py',import.meta.url));
const asciiSpace=char=>/[\t\n\f\r ]/.test(char || 'x');
const fail=()=>{throw Error('Cannot extract a complete source reference');};
// Process-local, content-keyed LRU. Cache only validated successes, never host
// decisions or mention use. Clone results so callers cannot mutate later reads.
const helperCache=new Map(),MAX_CACHE_UNITS=8*1024*1024;
let cacheUnits=0;
function cached(source,decodeOnly) {
    const key=(decodeOnly?'text:':'html:')+source,entry=helperCache.get(key);
    if(!entry)return null;
    helperCache.delete(key);helperCache.set(key,entry);
    return structuredClone(entry.parsed);
}
function retain(source,decodeOnly,parsed) {
    const key=(decodeOnly?'text:':'html:')+source;
    const units=key.length+JSON.stringify(parsed).length;
    if(units>MAX_CACHE_UNITS)return;
    if(helperCache.has(key)){cacheUnits-=helperCache.get(key).units;helperCache.delete(key);}
    while(helperCache.size&&(helperCache.size>=128||cacheUnits+units>MAX_CACHE_UNITS)){
        const oldest=helperCache.keys().next().value;
        cacheUnits-=helperCache.get(oldest).units;helperCache.delete(oldest);
    }
    helperCache.set(key,{parsed:structuredClone(parsed),units});cacheUnits+=units;
}
function retainDecoded(source,decodedText) {
    retain(source,true,{decodedText});
    // The helper returns the fixed point of bounded HTML entity decoding.
    retain(decodedText,true,{decodedText});
}

function escapeValue(source, index, kind) {
    let i=index+1;
    if(i>=source.length)fail();
    const char=source[i];
    if(char==='\n')return ['',i+1];
    if(char==='\r')return ['',i+1+(source[i+1]==='\n'?1:0)];
    if(kind==='css') {
        const hex=source.slice(i).match(/^[0-9a-f]{1,6}/i)?.[0];
        if(hex){i+=hex.length;const point=parseInt(hex,16);return [point===0||point>0x10ffff||point>=0xd800&&point<=0xdfff?'\ufffd':String.fromCodePoint(point),i+(asciiSpace(source[i])?1:0)+(source[i]==='\r'&&source[i+1]==='\n'?1:0)];}
        return [char,i+1];
    }
    const simple={b:'\b',f:'\f',n:'\n',r:'\r',t:'\t',v:'\v','0':'\0'};
    if(Object.hasOwn(simple,char))return [simple[char],i+1];
    if(char==='x'||char==='u'){
        const braced=char==='u'&&source[i+1]==='{';
        const hex=braced?source.slice(i+2).match(/^[0-9a-f]+(?=})/i)?.[0]:source.slice(i+1,i+1+(char==='x'?2:4));
        if(!hex||!new RegExp('^[0-9a-f]{'+(braced?'1,6':char==='x'?'2':'4')+'}$','i').test(hex))fail();
        const point=parseInt(hex,16);if(point>0x10ffff)fail();
        return [String.fromCodePoint(point),i+1+hex.length+(braced?2:0)];
    }
    return [char,i+1];
}

function stringAt(source,start,kind) {
    const quote=source[start];let value='',i=start+1;
    while(i<source.length){
        if(source[i]===quote)return {value,end:i+1};
        if(source[i]==='\\'){
            if(kind==='raw'){value+=source.slice(i,i+2);i+=2;}
            else {const [part,end]=escapeValue(source,i,kind);value+=part;i=end;}
        }
        else value+=source[i++];
    }
    fail();
}

function skipCommentsAndSpace(source,start) {
    let i=start;
    while(i<source.length){
        if(/\s/.test(source[i]))i++;
        else if(source.startsWith('/*',i)){const end=source.indexOf('*/',i+2);if(end<0)fail();i=end+2;}
        else break;
    }
    return i;
}

function cssIdentifier(source,start) {
    let i=start,value='';
    while(i<source.length){
        if(source[i]==='\\'){const [part,end]=escapeValue(source,i,'css');value+=part;i=end;}
        else if(/[\w-]/.test(source[i])||source.charCodeAt(i)>=128)value+=source[i++];
        else break;
    }
    return {value,end:i};
}

function cssFunctionEnd(source,start) {
    let i=start,depth=1;
    while(i<source.length){
        if(source.startsWith('/*',i)){i=skipCommentsAndSpace(source,i);continue;}
        if(source[i]==='"'||source[i]==="'"){i=stringAt(source,i,'css').end;continue;}
        if(source[i]==='\\'){i=escapeValue(source,i,'css')[1];continue;}
        if(source[i]==='(')depth++;
        if(source[i]===')'&&!--depth)return i;
        i++;
    }
    fail();
}

function imageSetReferences(body) {
    const values=cssReferences(body);let start=0,i=0;
    while(i<=body.length){
        if(i===body.length||body[i]===','){
            const first=skipCommentsAndSpace(body,start);
            if(body[first]==='"'||body[first]==="'")values.push(stringAt(body,first,'css').value);
            start=++i;continue;
        }
        if(body[i]==='"'||body[i]==="'"){i=stringAt(body,i,'css').end;continue;}
        if(body[i]==='('){i=cssFunctionEnd(body,i+1)+1;continue;}
        if(body.startsWith('/*',i)){i=skipCommentsAndSpace(body,i);continue;}
        i++;
    }
    return values;
}

export function cssReferences(source) {
    const values=[];let i=0;
    while(i<source.length){
        i=skipCommentsAndSpace(source,i);if(i>=source.length)break;
        if(source[i]==='"'||source[i]==="'"){i=stringAt(source,i,'css').end;continue;}
        if(source[i]==='@'){
            const name=cssIdentifier(source,i+1);
            if(name.value.toLowerCase()==='import'){i=skipCommentsAndSpace(source,name.end);if(source[i]==='"'||source[i]==="'"){const part=stringAt(source,i,'css');values.push(part.value);i=part.end;continue;}}
        }
        const name=cssIdentifier(source,i),open=skipCommentsAndSpace(source,name.end);
        if(['image-set','-webkit-image-set'].includes(name.value.toLowerCase())&&source[open]==='('){
            const end=cssFunctionEnd(source,open+1);
            values.push(...imageSetReferences(source.slice(open+1,end)));i=end+1;continue;
        }
        if(name.value.toLowerCase()==='url'&&source[open]==='('){
            i=skipCommentsAndSpace(source,open+1);
            let value='';
            if(source[i]==='"'||source[i]==="'"){const part=stringAt(source,i,'css');value=part.value;i=skipCommentsAndSpace(source,part.end);}
            else {
                while(i<source.length&&source[i]!==')'){
                    if(source[i]==='\\'){const [part,end]=escapeValue(source,i,'css');value+=part;i=end;}
                    else value+=source[i++];
                }
                value=value.replace(/^[\t\n\f\r ]+|[\t\n\f\r ]+$/g,'');
            }
            if(source[i]!==')')fail();
            values.push(value);i++;continue;
        }
        i=name.end>i?name.end:i+1;
    }
    return values;
}

export function jsReferences(source, roles=false) {
    const values=[];let i=0,canStartRegex=true,context='';
    while(i<source.length){
        const char=source[i];
        if(/\s/.test(char)){context+=' ';i++;continue;}
        if(source.startsWith('//',i)){const end=source.indexOf('\n',i+2);i=end<0?source.length:end;context+=' ';continue;}
        if(source.startsWith('/*',i)){const end=source.indexOf('*/',i+2);if(end<0)fail();i=end+2;context+=' ';continue;}
        if(char==='"'||char==="'"||char==='`'){
            const raw=char==='`'&&/\bString\s*\.\s*raw\s*$/.test(source.slice(0,i));
            const part=char==='`'?templateAt(source,i,raw):stringAt(source,i,raw?'raw':'js');
            for(const expression of part.expressions||[])values.push(...jsReferences(expression,roles));
            // Protocol labels in an explicit URL.protocol comparison are data,
            // not attempted requests. Do not exempt the same literal in fetch().
            const protocolComparison=/^https?:$/i.test(part.value)
                && /\[\s*(?:(['"])https?:\1\s*,\s*)*$/.test(source.slice(0,i))
                && /^(?:\s*,\s*(['"])https?:\1)*\s*\]\s*\.\s*includes\s*\(\s*[\w$.]+\.protocol\s*\)/.test(source.slice(part.end));
            const resource=/\b(?:fetch|sendBeacon|WebSocket|EventSource|import)\s*\(\s*$/.test(context)
                || /\b(?:import|export)\s+(?:[^;()]*\bfrom\s*)?$/.test(context);
            if(!protocolComparison)values.push(roles ? {value:part.value,resource} : part.value);
            context+='""';i=part.end;canStartRegex=false;continue;
        }
        if(char==='/'&&canStartRegex){
            let inClass=false;i++;
            while(i<source.length){if(source[i]==='\\'){i+=2;continue;}if(source[i]==='[')inClass=true;if(source[i]===']')inClass=false;if(source[i++]==='/'&&!inClass)break;}
            while(/[a-z]/i.test(source[i]||''))i++;
            context+='/regex/';canStartRegex=false;continue;
        }
        const word=source.slice(i).match(/^[a-z_$][\w$]*/i)?.[0];
        if(word){context+=word;i+=word.length;canStartRegex=['return','throw','case','delete','void','typeof','instanceof','in','of','yield','await'].includes(word);continue;}
        context+=char;canStartRegex=!/[\w)\]}]/.test(char);i++;
    }
    return values;
}

function interpolationEnd(source,start) {
    let i=start,depth=1;
    while(i<source.length){
        if(source.startsWith('//',i)){const end=source.indexOf('\n',i+2);if(end<0)fail();i=end+1;continue;}
        if(source.startsWith('/*',i)){i=skipCommentsAndSpace(source,i);continue;}
        if(source[i]==='"'||source[i]==="'"){i=stringAt(source,i,'js').end;continue;}
        if(source[i]==='`'){i=templateAt(source,i,false).end;continue;}
        if(source[i]==='{')depth++;
        if(source[i]==='}'&&!--depth)return i;
        i++;
    }
    fail();
}

function templateAt(source,start,raw) {
    let i=start+1,value='';const expressions=[];
    while(i<source.length){
        if(source[i]==='`')return {value,end:i+1,expressions};
        if(source.startsWith('${',i)){
            const end=interpolationEnd(source,i+2);expressions.push(source.slice(i+2,end));value+='${}';i=end+1;continue;
        }
        if(source[i]==='\\'){
            if(raw){value+=source.slice(i,i+2);i+=2;}
            else {const [part,end]=escapeValue(source,i,'js');value+=part;i=end;}
        } else value+=source[i++];
    }
    fail();
}

export function srcsetReferences(source) {
    // HTML's candidate collection keeps internal commas in a URL. Only trailing
    // commas or descriptor separators end candidates; do not split URL userinfo.
    const values=[];let i=0;
    while(i<source.length){
        while(i<source.length&&(asciiSpace(source[i])||source[i]===','))i++;
        const start=i;while(i<source.length&&!asciiSpace(source[i]))i++;
        let value=source.slice(start,i);if(!value)break;
        if(value.endsWith(',')){values.push(value.replace(/,+$/,''));continue;}
        values.push(value);
        let parentheses=0;
        while(i<source.length){const char=source[i++];if(char==='(')parentheses++;else if(char===')')parentheses=Math.max(0,parentheses-1);else if(char===','&&!parentheses)break;}
    }
    return values;
}

export function sourceReferences(source,kind) {
    if(kind==='css')return {base:null,values:cssReferences(source)};
    if(kind==='js')return {base:null,values:jsReferences(source)};
    if(['url','load-url','document-url'].includes(kind))return {base:null,values:[source]};
    if(kind==='srcset')return {base:null,values:srcsetReferences(source)};
    if(kind!=='html')fail();
    const parsed=runHtmlHelper(source);
    return {base:parsed.base,values:parsed.references.filter(ref=>ref.kind!=='html').flatMap(ref=>sourceReferences(ref.value,ref.kind).values),documents:parsed.references.filter(ref=>ref.kind==='html').map(ref=>ref.value),decodedText:parsed.decodedText};
}

const exactKeys=(value,keys)=>value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');
export function validateHtmlHelperOutput(parsed,decodeOnly=false) {
    if(!exactKeys(parsed,decodeOnly?['decodedText']:['base','references','decodedText'])||typeof parsed.decodedText!=='string')fail();
    if(!decodeOnly){
        if(parsed.base!==null&&typeof parsed.base!=='string'||!Array.isArray(parsed.references))fail();
        for(const ref of parsed.references)if(!exactKeys(ref,['kind','value','resource'])||!['url','load-url','document-url','srcset','css','js','html'].includes(ref.kind)||typeof ref.value!=='string'||typeof ref.resource!=='boolean')fail();
    }
    return parsed;
}

function runHtmlHelper(source,decodeOnly=false) {
    const hit=cached(source,decodeOnly);if(hit)return hit;
    const result=spawnSync(process.platform==='win32'?'python':'python3',[htmlHelper,...(decodeOnly?['--decode-text']:[])],{input:source,encoding:'utf8',maxBuffer:16*1024*1024});
    if(result.status!==0)throw Error('Cannot extract HTML references; Python 3 is required');
    let parsed;try{parsed=JSON.parse(result.stdout);}catch{fail();}
    validateHtmlHelperOutput(parsed,decodeOnly);
    if(source.length&&parsed.decodedText.length===0)fail();
    retain(source,decodeOnly,parsed);retainDecoded(source,parsed.decodedText);
    return parsed;
}

export function decodeReferenceText(source) {
    const hit=cached(source,true);if(hit)return hit.decodedText;
    // HTML's named references are ASCII alphanumeric; numeric references use
    // decimal/hex digits. If every possible token is a Python-proven fixed
    // point, the entire text is unchanged. If any token changes, decode the
    // complete source as before (decoding can create a reference across tokens).
    const tokens=[...new Set(source.match(/&(?:#(?:[xX][0-9a-fA-F]+|[0-9]+);?|[A-Za-z][A-Za-z0-9]*;?)/g)||[])];
    const decodedTokens=new Map(tokens.map(token=>[token,cached(token,true)]));
    const missing=tokens.filter(token=>!decodedTokens.get(token));
    if(missing.length)batchReferences(missing.map(source=>({source,kind:'text'}))).forEach((entry,index)=>decodedTokens.set(missing[index],entry));
    // Keep this invocation's results locally: a token list can exceed the LRU.
    if(tokens.every(token=>decodedTokens.get(token).decodedText===token))return source;
    return runHtmlHelper(source,true).decodedText;
}

export const jsReferenceEntries=source=>jsReferences(source,true);
export const htmlReferences=source=>runHtmlHelper(source);
export function batchReferences(sources) {
    const input=sources.map(file=>({source:file.source,html:file.kind==='html'}));
    const result=spawnSync(process.platform==='win32'?'python':'python3',[htmlHelper,'--batch'],{input:JSON.stringify(input),encoding:'utf8',maxBuffer:32*1024*1024});
    if(result.error||result.status!==0)fail();
    let parsed;try{parsed=JSON.parse(result.stdout);}catch{fail();}
    if(!Array.isArray(parsed)||parsed.length!==sources.length)fail();
    parsed.forEach((entry,index)=>{
        validateHtmlHelperOutput(entry,!input[index].html);
        if(input[index].source.length&&!entry.decodedText.length)fail();
    });
    // Do not seed until the entire batch has passed its exact schema checks.
    parsed.forEach((entry,index)=>{
        retain(input[index].source,!input[index].html,entry);
        retainDecoded(input[index].source,entry.decodedText);
    });
    return parsed;
}
