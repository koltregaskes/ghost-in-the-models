# Privacy guard parity

Portable remediation for Ghost in the Models PR 48, based on
`d5af7d0e7d65caf3bbe09d2ab212b2a68f2a8333`. Apply the same invariants when
reviewing KT Photography PR 40, StackScout PR 39, Repo Foundry PR 33 and
Elusion Works. This document does not claim those repositories have been fixed.

Run every attack with a navigation-only host (`github.com` or `x.com`) and
again with `evil.invalid` plus a matching non-request mention. An attack passes
only if extraction rejects it, or the loading host appears in `resource_hosts`
and the complete inventory check rejects the undisclosed load. An active or
decoded-view host must never be removed by a mention. Merely finding a host in
the broader navigation inventory is insufficient.

## 1. HTML5 foreign content and CDATA

Chosen design: fail closed, without an HTML5 tree builder. Once an actual svg
or math start tag has been tokenised, reject any subsequent script, style,
title, desc, foreignObject, mi, mo, mn, ms, mtext, annotation-xml, noscript or
template, textarea, xmp, iframe, noembed, noframes or plaintext start tag in
that input. Keep this restriction even after closing the
foreign root: HTMLParser cannot prove the browser's namespace after error
recovery. Tag matching is case-insensitive. Reject CDATA markers everywhere,
including incomplete markers and apparently inert foreign CDATA.

This intentionally rejects some harmless foreign titles and scripts/styles
after a closed SVG. Element and href/src names are also compared by local name
conservatively, so XML namespace aliases cannot hide an SVG script or load.
It preserves ordinary SVG shapes, images, hrefs and the
site's existing data SVG icons/filters. It differs from StackScout's suggested
namespace-aware tokeniser by declining those ambiguous documents altogether.

Every exact input below must be **rejected**, both without an exception and
with an `evil.invalid` mention after replacing the external host:

```html
<svg><style><img src="https://github.com/a.png"></style></svg>
<math><style><img src="https://x.com/a.gif"></style></math>
<svg><title><img src="https://x.com/a.gif"></title></svg>
<![CDATA[ > <img src="https://github.com/a.png"> ]]>
<svg><![CDATA[ <img src="https://github.com/a.png"> ]]></svg>
<![CDATA[ > <img src="https://github.com/a.png">
<svg><noscript><img src="https://github.com/a.png"></noscript></svg>
<svg><template><img src="https://github.com/a.png"></template></svg>
<math><mi><svg><style><img src="https://github.com/a.png"></style></svg></mi></math>
<svg><foreignObject><img src="https://github.com/a.png"></foreignObject></svg>
<svg><desc><img src="https://github.com/a.png"></desc></svg>
<SVG><STYLE><IMG SRC="https://github.com/a.png"></STYLE></SVG>
<svg></svg><style>body{color:red}</style>
<svg><textarea><img src="https://github.com/a.png"></textarea></svg>
<math><xmp><img src="https://github.com/a.png"></xmp></math>
<svg><iframe><img src="https://github.com/a.png"></iframe></svg>
<math><noembed><img src="https://github.com/a.png"></noembed></math>
<svg><noframes><img src="https://github.com/a.png"></noframes></svg>
<math><plaintext><img src="https://github.com/a.png"></plaintext></math>
```

These controls must remain accepted: `<svg><image href="https://fonts.gstatic.com/a.png"/></svg>`
reports `fonts.gstatic.com` as a resource; `<a href="https://x.com/t">Link</a>`
reports `x.com` as navigation only. An inert reviewed HTML comment can still
use its exact-file mention exception.

## 2. SMIL href mutation

Reject set, animate, animateColor, animateTransform and animateMotion elements
if any attribute whose local name is attributeName targets href or any
namespace-prefixed href. Compare names/targets case-insensitively after HTML
attribute decoding and ASCII whitespace trimming. Reject regardless of whether
the element uses to, from, by or semicolon-separated values, and regardless of
the current parent/target. This avoids resolving animated targets and times.

Exact minimum inputs, all **rejected**:

```html
<svg><image href="/a.png"><set attributeName="href" to="https://github.com/a.png"/></image></svg>
<svg><image href="/a.png"><animate attributeName="href" values="https://github.com/a.png"/></image></svg>
<svg><image href="/a.png"><animate attributeName="XLINK:HREF" from="https://x.com/a.png"/></image></svg>
<svg><image href="/a.png"><set attributeName="custom:HrEf" by="https://x.com/a.png"/></image></svg>
<svg><svg:animate ns:attributeName="XLINK:HrEf" values="/a;https://x.com/t"/></svg>
<svg><set a:attributeName="fill" attributeName="href" to="https://x.com/t"/></svg>
```

Repeat set/animate with each of href, HREF, xlink:href, XLINK:HREF and custom:HrEf,
and each of to/from/by/values. Non-URL animation such as
`<svg><animate attributeName="fill" to="red"/></svg>` remains supported.

## 3. Data resources, MIME syntax and mention scope

Decode percent and base64 payloads before extraction, recursively through
HTML/SVG documents, CSS imports and JavaScript resource references. Use the
existing complete CSS and JS extractors; never fetch or execute payload bytes.
CSS references are resources. Within decoded JS, conservatively retain a
resource role on every extracted reference. Recognise direct static import,
import-from, export-from and dynamic import/fetch calls even with intervening
comments; these are direct references, not the indirect-JS limitation below.
Backstop-only hosts in decoded
CSS/JS also count as resources. Backstop hosts in decoded HTML/SVG cannot use
mentions, while namespace/metadata hosts remain distinct from actual loads.
The independent backstop also retains data-body provenance outside recognised
attributes, so a base64 body in an otherwise inert comment cannot use a mention.

Normalise the MIME essence case-insensitively and trim surrounding whitespace
and whitespace before parameters: `text/css ;charset=utf-8` is CSS. Accept
the following complete WHATWG JavaScript MIME essence list, including mixed
case, parameters and percent/base64 encodings:

```text
application/ecmascript
application/javascript
application/x-ecmascript
application/x-javascript
text/ecmascript
text/javascript
text/javascript1.0
text/javascript1.1
text/javascript1.2
text/javascript1.3
text/javascript1.4
text/javascript1.5
text/jscript
text/livescript
text/x-ecmascript
text/x-javascript
```

Supported textual data types are text/html, image/svg+xml, text/css and those
JS aliases. Unknown/potentially active loaded types are rejected, including
application/xhtml+xml, application/xml, text/plain and an omitted MIME type.
The explicit opaque allowance is image/png, image/jpeg, image/gif, image/webp,
image/avif, image/bmp, image/x-icon, image/vnd.microsoft.icon, font/woff,
font/woff2, font/ttf, font/otf, application/font-woff, application/font-sfnt and
application/vnd.ms-fontobject. It is not a prefix-based MIME allowance.

Accept only supported UTF-8/ASCII textual encodings. Malformed percent/base64,
invalid UTF-8, NUL, unsupported charset/XML declarations or CSS @charset must
fail explicitly. Preserve the 16 MiB data URL limit and shared recursion limit
of 32; exceeding either rejects, never silently truncates.

Exact HTML inputs below report `github.com` as a **resource load**, or reject
unsupported syntax. The plain and base64 stylesheet forms must be inspected:

```html
<link rel="stylesheet" href="data:text/css,@import url(https://github.com/a.css);">
<link rel="stylesheet" href="data:text/css;base64,Ym9keXtiYWNrZ3JvdW5kOnVybChodHRwczovL2dpdGh1Yi5jb20vYS5wbmcpfQ==">
<link rel="stylesheet" href="data: text/css ;charset=utf-8,%40import%20url(https%3A%2F%2Fgithub.com%2Fa.css)%3B">
<style>@import url(data:text/css,body%7Bbackground:url(https://github.com/a.png)%7D);</style>
<iframe src="data:text/html,%3Clink%20rel%3Dstylesheet%20href%3D%22data%3Atext%2Fcss%2C%40import%20url(https%3A%2F%2Fgithub.com%2Fa.css)%22%3E"></iframe>
```

The following executable fixture constructor defines exact additional inputs
without ambiguous hand-written base64. Run each independently as HTML except
the indicated standalone JS import. Expected host is always a resource; with
evil.invalid plus a mention, extraction must reject. A decoded-view comment
is deliberately over-reported and cannot use an inert exception.

```js
const data = (mime, body, b64 = false) =>
  `data:${mime}${b64 ? ';base64' : ''},${b64 ? Buffer.from(body).toString('base64') : encodeURIComponent(body)}`;
const css = data(' text/css ;charset=utf-8',
  '@import "' + data('text/css', 'a{background:url(https://github.com/a.png)}', true) + '";', true);
const html = '<iframe src="' + data('text/html', '<link rel="stylesheet" href="' + css + '">', true) + '"></iframe>';
const js = 'import(' + JSON.stringify(data('TEXT/JSCRIPT ;charset=utf-8', "fetch('https://x.com/t')", true)) + ')';
const backstopOnly = '<link rel="stylesheet" href="' + data('text/css', '/* x_https://evil.invalid/a */', true) + '">';
```

Every input in this exact failure list must be **rejected** as a loaded data
resource: `data:text/css,%GG`, `data:text/css,%ff`,
`data:text/javascript;base64,@@@`, `data:text/jscript,%00`,
`data:text/css;charset=iso-8859-1,a{}`,
`data:text/css,@charset%20%22utf-16%22;`,
`data:application/xhtml+xml,<html/>`, `data:application/xml,<x/>`,
`data:text/plain,fetch(1)`, `data:application/unknown,anything`, `data:,fetch(1)`.

## 4. Script data URLs, independent of MIME

At the HTML loading boundary, **reject every data: URL** in src, href or
xlink:href on any element whose local name is script. Apply HTML attribute
decoding, URL tab/newline removal and leading/trailing C0/space trimming before
testing the scheme. Cover all namespaces, uppercase tags, both percent and
base64 payloads, and recursive srcdoc/decoded documents. MIME recognition is
not the defence: classic scripts can execute bytes irrespective of their
declared data: MIME type. Remote script URLs keep their existing resource role.

Every exact input below is **rejected**:

```html
<script src="data:text/javascript,fetch(%27https://x.com/t%27)"></script>
<svg><script href="data:text/x-javascript,fetch(%27https://x.com/t%27)"></script></svg>
<svg><script xlink:href="data:application/x-ecmascript,fetch(%27https://x.com/t%27)"></script></svg>
<script href="data:,fetch(%27https://x.com/t%27)"></script>
<script src=" &#9;d&#97;ta&colon;text/plain,fetch(1)"></script>
<script href="da&#10;ta:,fetch(1)"></script>
<s:script x:href="data:,fetch(1)"/>
<iframe srcdoc="&lt;svg&gt;&lt;script href=&quot;data:text/jscript,fetch(%27https://x.com/t%27)&quot;&gt;&lt;/script&gt;&lt;/svg&gt;"></iframe>
```

Repeat the constructor below for every JS MIME above, text/css, text/plain,
application/unknown and an empty essence; every case must reject. This also
defines the exact namespace/attribute/srcdoc test matrix:

```js
for (const tag of ['script', 'SCRIPT', 'svg:script'])
for (const attribute of ['src', 'href', 'xlink:href']) {
  const element = `<${tag} ${attribute}="${data(mime, "fetch('https://x.com/t')", true)}"></${tag}>`;
  const attr = s => s.replaceAll('&', '&amp;').replaceAll('"', '&quot;');
  const nested = `<iframe srcdoc="${attr(element)}"></iframe>`;
  // element and nested must both reject; mime is each value listed above.
}
```

## Retained probes and verification

`scripts/fixtures/privacy-guard-parity-probes.json` retains all 99 exact inputs,
labels and mention entries from p48.mjs, p48b.mjs and p48c.mjs, without their
machine-specific imports. `scripts/test-privacy-guard-parity.mjs` runs them
against the repository inventory and adds the MIME, script, namespace,
encoding, depth, cache and compatibility matrices. The real public-artifact
checker additionally runs the 26 active p48c cases against built output.

Keep existing tests and threat-model limitations. In particular, arbitrary
indirect JavaScript such as `const u="https://x.com/t";fetch(u)` or
`img.src = u` is not proven safe by this guard. Runtime assembly, obfuscation,
remote responses and redirects still need runtime/network verification. This
patch does not lower that existing limitation or turn the source guard into
a browser sandbox.

Performance changes must preserve parser errors, exact helper schema checks,
normalisation views and host/mention semantics. This implementation caches only
validated parser results by full source/mode, with cloned results and bounded
memory. It skips full-source entity decoding only when every possible token
is a fixed point proven by the same Python decoder. Any changing token falls
back to the complete-source decoder, retaining cross-token behaviour and the
16-round entity limit. No exceptions or inventory decisions are cached.
