import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectSources} from './privacy-hosts.mjs';

const allowed=new Set(['ghostinthemodels.com','fonts.googleapis.com','fonts.gstatic.com','www.nasa.gov']);
function inspect(source,kind='html'){return inspectSources([{name:'index.html',kind,source}]);}
function rejected(source,kind='html') {
  try{return inspect(source,kind).hosts.some(host=>!allowed.has(host));}
  catch{return true;}
}
const attacks={
  'numeric HTML tab in host':'<img src="https://ev&#9;il.example/a">',
  'named HTML tab in host':'<img src="https://ev&Tab;il.example/a">',
  'semicolon userinfo':'<img src="https://fonts.googleapis.com;@evil.example/a">',
  'allowed host as userinfo':'<img src="https://fonts.googleapis.com@evil.example/a">',
  'fragment cannot change host':'<img src="https://evil.example#@fonts.googleapis.com/a">',
  'browser backslash authority':'<img src="https://evil.example\\@fonts.googleapis.com/a">',
  'protocol relative':'<img src="//evil.example/a">',
  'bare HTTPS':'<img src="https://">',
  'invalid port':'<img src="https://fonts.googleapis.com:invalid/a">',
  'meta refresh':'<meta http-equiv="refresh" content="0; url=https://evil.example/a">',
  'srcset candidates':'<img srcset="https://fonts.googleapis.com/a 1x, //evil.example/b 2x">',
  'srcset internal comma remains in userinfo':'<img srcset="https://fonts.googleapis.com,@evil.example/a 1x">',
  'CSS import':'<style>@import "https://evil.example/a";</style>',
  'CSS full url argument':'<style>body{background:url(https://fonts.googleapis.com;@evil.example/a)}</style>',
  'CSS escaped URL':String.raw`<style>body{background:url("\68 ttps://evil.example/a")}</style>`,
  'JS literal':'<script>const u="https://evil.example/a";</script>',
  'JS escaped slashes':String.raw`<script>const u="https:\/\/evil.example/a";</script>`,
  'JS Unicode URL':String.raw`<script>const u="\u0068ttps:\u002f\u002fevil.example/a";</script>`,
  'JS HTML string':String.raw`<script>const u='<img src="https://evil.example/a">';</script>`,
  'encoded host character':'<img src="https://%65vil.example/a">',
  'HTML entity quote stays inside its attribute':'<img src="https://fonts.googleapis.com&quot;@evil.example/a">',
};
for(const [name,source] of Object.entries(attacks))test(name+' is rejected',()=>assert.ok(rejected(source),name));
test('ordinary font resources pass',()=>assert.ok(!rejected('<link rel="stylesheet" href="https://fonts.googleapis.com/a"><link rel="preconnect" href="//fonts.gstatic.com">')));
test('an encoded tab is decoded once before parsing',()=>assert.ok(!rejected('<img src="https://fonts.googleapi&#9;s.com/a">')));
test('NASA is a reviewed navigation destination',()=>assert.ok(!rejected('<a href="https://www.nasa.gov/centers-and-facilities/jpl/">NASA</a>')));
test('WHATWG authority normalisation is used',()=>assert.ok(inspect('<img src="https://evil.example\\@fonts.googleapis.com/a">').hosts.includes('evil.example')));
test('HTML srcset does not split a comma inside URL userinfo',()=>assert.ok(inspect('<img srcset="https://fonts.googleapis.com,@evil.example/a 1x">').hosts.includes('evil.example')));
test('malformed references throw explicitly',()=>assert.throws(()=>inspect('<img src="https://">')));
test('unknown standalone JS host is found after decoding',()=>assert.ok(rejected(String.raw`const u="https:\/\/evil.example/a"`,'js')));
test('CSS import escapes are decoded',()=>assert.ok(rejected(String.raw`@import "\68 ttps://evil.example/a";`,'css')));
