"""Extract complete HTML reference values using the standard-library HTML5 table."""
import html
from html.entities import html5
from html.parser import HTMLParser
import json
import re
import sys

ENTITY = re.compile(r"&(#(?:[xX][0-9a-fA-F]+|[0-9]+);?|[A-Za-z][A-Za-z0-9]*;?)")
ATTRIBUTE = re.compile(r'''([^\s/=<>`]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?''')
URL_ATTRIBUTES = {"href", "src", "action", "formaction", "poster", "data", "cite", "background", "longdesc", "manifest", "xlink:href"}
ASCII_SPACE = "\t\n\f\r "
# HTMLParser has no HTML5 namespace/tree builder. Once foreign content has
# appeared, do not guess when browser error recovery returns to HTML. Keeping
# this flag to end of input deliberately rejects some otherwise harmless pages.
FOREIGN_UNSUPPORTED = {"script", "style", "title", "desc", "foreignobject",
                       "mi", "mo", "mn", "ms", "mtext", "annotation-xml",
                       "noscript", "template", "textarea", "xmp", "iframe",
                       "noembed", "noframes", "plaintext"}


def reference_kind(tag, name, attrs):
    if (tag in {"iframe", "frame", "embed"} and name == "src") or (tag == "object" and name == "data"):
        return "document-url"
    if name in {"src", "poster", "data", "background", "manifest"}:
        return "load-url"
    if name in {"href", "xlink:href"} and tag in {"image", "feimage", "use", "script"}:
        return "load-url"
    if tag == "link" and name == "href" and set(attrs.get("rel", "").lower().split()) & {
        "stylesheet", "apple-touch-icon", "apple-touch-icon-precomposed", "icon",
        "modulepreload", "preload", "prefetch", "manifest", "preconnect", "dns-prefetch"
    }:
        return "load-url"
    return "url"


def refresh_destination(content):
    # Accept the supported declarative-refresh grammar explicitly. A syntax we
    # cannot classify must fail, never leave an active URL to a mention exception.
    delay = re.match(r"^[\t\n\f\r ]*[0-9]+(?:\.[0-9]+)?", content)
    if not delay:
        raise ValueError("Unsupported refresh delay")
    remainder = content[delay.end():].strip(ASCII_SPACE)
    if not remainder:
        return ""  # Delay-only refresh reloads the current document.
    if remainder[0] not in ";,":
        raise ValueError("Unsupported refresh separator")
    destination = remainder[1:].strip(ASCII_SPACE)
    if destination.startswith((";", ",")):
        raise ValueError("Unsupported refresh separator")
    if destination[:3].lower() == "url":
        marker = re.match(r"url[\t\n\f\r ]*=[\t\n\f\r ]*", destination, re.I)
        if not marker:
            raise ValueError("Unsupported refresh URL marker")
        destination = destination[marker.end():]
    if destination.startswith(('"', "'")):
        end = destination.find(destination[0], 1)
        if end < 0 or destination[end + 1:].strip(ASCII_SPACE):
            raise ValueError("Unsupported quoted refresh destination")
        destination = destination[1:end]
    return destination


def decode_attribute(value):
    # Longest HTML5 named match, in attribute context. Decode exactly once:
    # semicolonless names followed by ASCII alphanumeric or '=' stay literal.
    def replace(match):
        token = match[1]
        if token.startswith("#"):
            return html.unescape(match[0])
        for length in range(len(token), 0, -1):
            name = token[:length]
            if name not in html5:
                continue
            following = token[length:length + 1] or value[match.end():match.end() + 1]
            if not name.endswith(";") and following and (following in "=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
                return match[0]
            return html5[name] + token[length:]
        return match[0]
    return ENTITY.sub(replace, value)


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.references = []
        self.base = None
        self.raw_kind = None
        self.raw_parts = []
        self.foreign_seen = False

    def handle_starttag(self, tag, _):
        local_tag = tag.rsplit(":", 1)[-1]
        if local_tag in {"svg", "math"}:
            self.foreign_seen = True
        if self.foreign_seen and local_tag in FOREIGN_UNSUPPORTED:
            raise ValueError("Unsupported foreign-content parsing context")
        raw = self.get_starttag_text()
        raw = raw[re.match(r"<\s*[^\s/>]+", raw).end():]
        attrs = {}
        for match in ATTRIBUTE.finditer(raw):
            name = match[1].lower()
            if name not in attrs:  # HTML uses the first duplicate attribute.
                attrs[name] = decode_attribute(next((v for v in match.groups()[1:] if v is not None), ""))
        if tag.rsplit(":", 1)[-1] == "script":
            for name, value in attrs.items():
                clean = value.translate(str.maketrans("", "", "\t\n\r")).strip("".join(map(chr, range(33))))
                if name.rsplit(":", 1)[-1] in {"src", "href"} and clean.lower().startswith("data:"):
                    raise ValueError("Data URL on script element is unsupported")
        # Reject href animation, including arbitrary namespace prefixes. It
        # cannot be represented as a single static URL (values is a list).
        targets = [value for name, value in attrs.items()
                   if name.rsplit(":", 1)[-1] == "attributename"]
        if tag.rsplit(":", 1)[-1] in {"set", "animate", "animatecolor", "animatetransform", "animatemotion"} and any(target.strip(ASCII_SPACE).rsplit(":", 1)[-1].lower() == "href" for target in targets):
            raise ValueError("Unsupported SMIL href animation")
        if tag == "base" and self.base is None and "href" in attrs:
            self.base = attrs["href"]
        for name, value in attrs.items():
            local_name = name.rsplit(":", 1)[-1]
            if name in URL_ATTRIBUTES or local_name in {"src", "href"}:
                self.references.append({"kind": reference_kind(local_tag, local_name, attrs), "value": value})
            elif name in {"srcset", "imagesrcset"}:
                self.references.append({"kind": "srcset", "value": value})
            elif name == "ping":
                self.references.extend({"kind": "load-url", "value": v} for v in re.split(r"[\t\n\f\r ]+", value.strip()) if v)
            elif name == "style":
                self.references.append({"kind": "css", "value": value})
            elif name == "srcdoc":
                self.references.append({"kind": "html", "value": value})
            elif name.startswith("on"):
                self.references.append({"kind": "js", "value": value})
        if tag == "meta" and attrs.get("property", attrs.get("name", "")).lower() in {"og:url", "og:image", "twitter:image", "twitter:url"}:
            self.references.append({"kind": "url", "value": attrs.get("content", "")})
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.references.append({"kind": "load-url", "value": refresh_destination(attrs.get("content", "")), "resource": True})
        if tag in {"script", "style"}:
            self.raw_kind = "js" if tag == "script" else "css"
            self.raw_parts = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in {"script", "style"}:
            self.handle_endtag(tag)

    def unknown_decl(self, data):
        # Reject CDATA everywhere, including bogus HTML comments. HTMLParser
        # otherwise hides markup that HTML5 can reprocess as active elements.
        raise ValueError("Unsupported marked declaration")

    def handle_data(self, data):
        if self.raw_kind:
            self.raw_parts.append(data)

    def handle_endtag(self, tag):
        if self.raw_kind and tag in {"script", "style"}:
            self.references.append({"kind": self.raw_kind, "value": "".join(self.raw_parts)})
            self.raw_kind = None
            self.raw_parts = []


def extract(source, decode_only=False):
    if not isinstance(source, str):
        raise ValueError("Invalid source")
    decoded = source
    for _ in range(16):
        following = html.unescape(decoded)
        if following == decoded:
            break
        decoded = following
    else:
        raise ValueError("Entity nesting exceeds the inspection limit")
    if decode_only:
        return {"decodedText": decoded}
    if re.search(r"<!\[CDATA\[", source, re.I):
        raise ValueError("Unsupported CDATA syntax")
    parser = References()
    parser.feed(source)
    parser.close()
    references = [{**ref, "resource": ref.get("resource", False)} for ref in parser.references]
    return {"base": parser.base, "references": references, "decodedText": decoded}


if __name__ == "__main__":
    try:
        source = sys.stdin.buffer.read().decode("utf-8")
        if sys.argv[1:] == ["--batch"]:
            values = json.loads(source)
            if not isinstance(values, list):
                raise ValueError("Invalid batch")
            result = []
            for entry in values:
                if not isinstance(entry, dict) or set(entry) != {"source", "html"} or not isinstance(entry["html"], bool):
                    raise ValueError("Invalid batch entry")
                result.append(extract(entry["source"], not entry["html"]))
        elif sys.argv[1:] in ([], ["--decode-text"]):
            result = extract(source, bool(sys.argv[1:]))
        else:
            raise ValueError("Unknown helper mode")
        print(json.dumps(result))
    except Exception:
        print("Cannot extract HTML references", file=sys.stderr)
        sys.exit(1)
