"""Fail-closed CSS source-role cascade for the publication's colour contract.

This evaluates selector probes, not browser layout or image pixels. Every
colour-affecting rule is probed, including background-only and focus rules.
Unsupported colour syntax/selectors are errors, not untested passing pairs.
"""
from dataclasses import dataclass, field
from functools import lru_cache
import re
from contrast_colours import split, colour, over, ratio, resolve, backgrounds


class Unsupported(ValueError):pass
class InvalidVariable(ValueError):pass


def balanced(source,start,opening='(',closing=')'):
    depth=1;quote=None;i=start+1
    while i<len(source):
        c=source[i]
        if quote:
            if c=='\\':i+=2;continue
            if c==quote:quote=None
        elif c in "\"'":quote=c
        elif c==opening:depth+=1
        elif c==closing:
            depth-=1
            if not depth:return source[start+1:i],i+1
        i+=1
    raise Unsupported('Unclosed CSS block/function')


@lru_cache(None)
def compounds(selector):
    parts=[];start=0;depth=0;brackets=0;quote=None;join=' ';i=0
    while i<len(selector):
        c=selector[i]
        if quote:
            if c==quote:quote=None
        elif c in "\"'":quote=c
        elif c=='(':depth+=1
        elif c==')':depth-=1
        elif c=='[':brackets+=1
        elif c==']':brackets-=1
        elif not depth and not brackets and (c.isspace() or c in '>+~'):
            token=selector[start:i].strip()
            if token:parts.append((join,token));join=' '
            if c in '>+~':join=c
            start=i+1
        i+=1
    token=selector[start:].strip()
    if token:parts.append((join,token))
    if not parts:raise Unsupported('Empty selector')
    return tuple(parts)


@lru_cache(None)
def atoms(compound):
    result=[];i=0
    while i<len(compound):
        c=compound[i]
        if c in '.#':
            m=re.match(r'[\w-]+',compound[i+1:])
            if not m:raise Unsupported('Unsupported escaped selector')
            result.append(('class' if c=='.' else 'id',m[0]));i+=len(m[0])+1
        elif c=='[':
            raw,end=balanced(compound,i,'[',']')
            m=re.fullmatch(r'''([\w-]+)(?:\s*(=|~=|\^=|\$=|\*=|\|=)\s*["']?([^"']*?)["']?)?''',raw.strip())
            if not m:raise Unsupported('Unsupported attribute selector: '+raw)
            result.append(('attr',m.groups()));i=end
        elif c==':':
            element=compound.startswith('::',i);i+=2 if element else 1
            m=re.match(r'[\w-]+',compound[i:])
            if not m:raise Unsupported('Unsupported pseudo selector')
            name=m[0];i+=len(name);arg=None
            if i<len(compound) and compound[i]=='(':arg,i=balanced(compound,i)
            if name in {'is','where'} or name=='has' and any(s.strip().startswith(('>','+','~')) for s in split(arg)):
                raise Unsupported('Selector needs an explicit fixture: '+name)
            if name not in {'root','hover','focus','focus-visible','active','first-child','last-child','first-of-type','last-of-type','not','has','is','where','before','after','first-letter','selection','marker','-webkit-details-marker','view-transition-old','view-transition-new'}:
                raise Unsupported('Unsupported pseudo selector: '+name)
            result.append(('pseudo-element' if element or name=='first-letter' else 'pseudo',(name,arg)))
        elif c=='*':result.append(('tag','*'));i+=1
        else:
            m=re.match(r'[a-zA-Z][\w-]*',compound[i:])
            if not m:raise Unsupported('Unsupported selector: '+compound)
            result.append(('tag',m[0].lower()));i+=len(m[0])
    return tuple(result)


@lru_cache(None)
def specificity(selector):
    a=b=c=0
    for _,part in compounds(selector):
        for kind,value in atoms(part):
            if kind=='id':a+=1
            elif kind in {'class','attr'}:b+=1
            elif kind=='tag':c+=value!='*'
            elif kind=='pseudo-element':c+=1
            else:
                name,arg=value
                if name in {'not','has','is'}:
                    x,y,z=max(specificity(s) for s in split(arg));a+=x;b+=y;c+=z
                elif name!='where':b+=1
    return a,b,c


@dataclass(eq=False)
class Node:
    tag:str='div'
    classes:set=field(default_factory=set)
    attrs:dict=field(default_factory=dict)
    ident:str=''
    state:set=field(default_factory=set)
    parent:object=None
    children:list=field(default_factory=list)
    pseudo:str|None=None
    def add(self,node):node.parent=self;self.children.append(node);return node


def simple_matches(node,part):
    for kind,value in atoms(part):
        if kind=='tag' and value not in {'*',node.tag}:return False
        if kind=='id' and node.ident!=value:return False
        if kind=='class' and value not in node.classes:return False
        if kind=='attr':
            name,op,wanted=value;actual=node.attrs.get(name)
            if actual is None:return False
            if op=='=' and actual!=wanted:return False
            if op=='~=' and wanted not in actual.split():return False
            if op=='^=' and not actual.startswith(wanted):return False
            if op=='$=' and not actual.endswith(wanted):return False
            if op=='*=' and wanted not in actual:return False
            if op=='|=' and actual!=wanted and not actual.startswith(wanted+'-'):return False
        if kind=='pseudo-element' and node.pseudo!=value[0]:return False
        if kind=='pseudo':
            name,arg=value
            if name=='root' and node.tag!='html':return False
            if name in {'hover','focus','focus-visible','active'} and name not in node.state:return False
            if name in {'first-child','first-of-type'} and node.parent and node.parent.children[0] is not node:return False
            if name in {'last-child','last-of-type'} and node.parent and node.parent.children[-1] is not node:return False
            if name=='not' and any(matches(node,s) for s in split(arg)):return False
            if name in {'is','where'} and not any(matches(node,s) for s in split(arg)):return False
            if name=='has':
                descendants=[];pending=list(node.children)
                while pending:
                    item=pending.pop();descendants.append(item);pending+=item.children
                if not any(matches(child,s) for child in descendants for s in split(arg)):return False
    return True


def matches(node,selector):
    parts=compounds(selector)
    def visit(n,i):
        if n is None or not simple_matches(n,parts[i][1]):return False
        if i==0:return True
        join=parts[i][0]
        if join=='>':return visit(n.parent,i-1)
        if join in {'+','~'}:
            if not n.parent:return False
            earlier=n.parent.children[:n.parent.children.index(n)]
            return any(visit(s,i-1) for s in (earlier[-1:] if join=='+' else earlier))
        parent=n.parent
        while parent:
            if visit(parent,i-1):return True
            parent=parent.parent
        return False
    return visit(node,len(parts)-1)


def declarations(source):
    result=[]
    for text in split(source,';'):
        if not text.strip():continue
        if ':' not in text:raise Unsupported('Invalid declaration')
        name,value=text.split(':',1);name=name.strip();value=value.strip()
        important=bool(re.search(r'!\s*important\s*$',value,re.I))
        value=re.sub(r'!\s*important\s*$','',value,flags=re.I).strip()
        result.append((name,value,important))
    return result


COLOUR_PROPERTIES={'color','background','background-color','background-image','opacity','outline','outline-color','content','display','visibility','background-clip','-webkit-background-clip','filter','mix-blend-mode','mask-image','-webkit-mask-image','-webkit-text-fill-color','all','background-blend-mode','fill','stroke'}
def parse(source):
    source=re.sub(r'/\*.*?\*/','',source,flags=re.S);rules=[];excluded=[]
    def walk(text,conditions=()):
        i=0
        while i<len(text):
            while i<len(text) and text[i].isspace():i+=1
            if i==len(text):break
            start=text.find('{',i)
            if start<0:
                if text[i:].strip():raise Unsupported('Unsupported CSS statement: '+text[i:i+60])
                break
            header=text[i:start].strip();body,end=balanced(text,start,'{','}');i=end
            if header.startswith('@'):
                if header.startswith('@keyframes') or header.startswith('@view-transition'):
                    excluded.append((header,'animation frames / non-colour navigation metadata'));continue
                if not header.startswith(('@media','@supports','@container')):raise Unsupported('Unsupported CSS conditional: '+header)
                before=len(rules)
                walk(body,conditions+(header,))
                if header.startswith(('@supports','@container')):
                    for nested,values,_,_ in rules[before:]:
                        if any((name in COLOUR_PROPERTIES and name not in {'display','visibility'} or name.startswith('--')) and not (nested in {'[data-reveal]','[data-reveal].is-visible'} and name=='opacity' and value in {'0','1'}) for name,value,_ in values):
                            raise Unsupported('Colour-bearing feature/container branch needs an explicit scenario: '+header)
                continue
            dec=declarations(body)
            for selector in split(header):
                specificity(selector)  # Validate even rules later classified as layout.
                rules.append((selector,dec,conditions,len(rules)))
    walk(source)
    return rules,excluded


def relevant(dec):return any(k in COLOUR_PROPERTIES or k.startswith('--') for k,_,_ in dec)


def gradient_colours(value,t):
    layers=[]
    for part in split(value):
        if re.match(r'(?:linear|radial|conic)-gradient\(',part):
            inside,end=balanced(part,part.index('('));stops=[]
            for index,stop in enumerate(split(inside)):
                m=re.match(r'(#[0-9a-fA-F]{3,8}\b|transparent\b|currentColor\b|(?:oklch|rgba?|color-mix)\()',stop)
                if not m:
                    if index==0 and re.match(r'(?:to\b|from\b|circle\b|ellipse\b|[\d.-]+(?:deg|px|%))',stop):continue
                    raise Unsupported('Unsupported gradient colour stop: '+stop)
                token=m[0]
                if token.endswith('('):_,finish=balanced(stop,len(token)-1);token=stop[:finish]
                stops.append(colour(token,t))
            if not stops:raise Unsupported('Gradient has no supported colour stops')
            layers.append(stops)
        else:layers.append([colour(part,t)])
    accumulated=[[0,0,0,0]]
    for layer in reversed(layers):accumulated=[composite(f,b,1) for b in accumulated for f in layer]
    return accumulated


@lru_cache(None)
def media_bounds(condition):
    if not condition.startswith('@media'):return ()
    query=condition[len('@media'):].strip()
    bounds=[]
    for term in re.split(r'\s+and\s+',query):
        match=re.fullmatch(r'\(\s*(min|max)-width\s*:\s*(\d+(?:\.\d+)?)px\s*\)',term)
        if match:bounds.append((match[1],float(match[2])));continue
        if term=='(prefers-reduced-motion: reduce)':continue
        raise Unsupported('Unsupported media condition: '+condition)
    return tuple(bounds)


def viewport_widths(rules):
    widths={320,390,768,1024,1280}
    # Include every parsed width breakpoint, including layout/container blocks.
    for _,_,conditions,_ in rules:
        for condition in conditions:
            if condition.startswith('@media'):media_bounds(condition)
            for value in re.findall(r'(?:min|max)-width\s*:\s*(\d+(?:\.\d+)?)px',condition):
                point=float(value)
                widths.update({max(1,point-1),max(1,point),point+1})
    return sorted(widths)


@lru_cache(None)
def active(conditions,width):
    for condition in conditions:
        if condition.startswith('@supports') and not re.fullmatch(r'@supports(?: not)? \(animation-timeline: (?:scroll|view)\(\)\)',condition):raise Unsupported('Unsupported feature condition: '+condition)
        for bound,value in media_bounds(condition):
            if bound=='min' and width<value or bound=='max' and width>value:return False
        # The current feature/container branches contain layout/reveal controls;
        # their colour-bearing extensions are rejected below rather than masked.
    return True


def expand(value,variables,seen=()):
    while 'var(' in value:
        start=value.index('var(');inside,end=balanced(value,start+3);parts=split(inside);key=parts[0]
        if not re.fullmatch(r'--[\w-]+',key) or '\\' in key:raise Unsupported('Unsupported custom-property identifier')
        if key in seen:raise Unsupported('Cyclic custom property: '+key)
        try:
            if key not in variables:raise InvalidVariable(key)
            replacement=expand(variables[key],variables,seen+(key,))
        except InvalidVariable:
            if len(parts)<2:raise
            replacement=expand(','.join(parts[1:]),variables,seen)
        value=value[:start]+replacement+value[end:]
    return value


def create(part,state):
    node=Node(state=set(state))
    for kind,value in atoms(part):
        if kind=='tag' and value!='*':node.tag=value
        elif kind=='class':node.classes.add(value)
        elif kind=='id':node.ident=value
        elif kind=='attr':node.attrs[value[0]]=value[2] or ''
        elif kind=='pseudo-element':node.pseudo=value[0]
        elif kind=='pseudo':
            name,arg=value
            if name=='root':node.tag='html'
            elif name in {'hover','focus','focus-visible','active'}:node.state.add(name)
            elif name=='not':
                for _,term in compounds(arg):
                    for k,v in atoms(term):
                        if k=='pseudo' and v[0] in node.state:node.state.remove(v[0])
            elif name=='has':
                child=create(compounds(split(arg)[0])[-1][1],state);node.add(child)
            elif name in {'is','where'}:
                probe=create(compounds(split(arg)[0])[-1][1],state);node.classes|=probe.classes;node.attrs.update(probe.attrs)
    return node


def probe(selector,theme,voices,state):
    html=Node(tag='html',state=set(state));body=html.add(Node(tag='body',classes={'voiced'} if voices else set(),attrs={'data-voice':theme} if voices and theme!='neutral' else {},state=set(state)))
    if selector==':root' or selector=='html':return html
    parts=compounds(selector);parent=body
    # Canonical inherited reading surfaces are part of the tested source roles.
    if voices and any(word in selector for word in ['reader','source','margin','diff','checks','crossnote','room-essay','tone']) and not selector.startswith('body'):
        if not any('.gitm-reader'==term for _,term in parts):parent=parent.add(Node(classes={'gitm-reader'},state=set(state)))
        if not any('.gitm-reader__body'==term for _,term in parts):parent=parent.add(Node(classes={'gitm-reader__body'},state=set(state)))
    if '.gitm-tone-popover' in selector and 'hint-help' not in selector:
        parent=parent.add(Node(classes={'gitm-claude-reader__hint-help'},state=set(state)))
    if voices and '.gitm-card__' in selector and not any('.gitm-card'==term for _,term in parts):
        grid=parent.add(Node(classes={'gitm-tetraptych'},state=set()))
        if 'sibling-hover' in state:grid.add(Node(classes={'gitm-card'},attrs={'data-voice':'grok' if theme!='grok' else 'claude'},state={'hover'}))
        parent=grid.add(Node(classes={'gitm-card'},attrs={'data-voice':theme} if theme!='neutral' else {},state=set() if 'sibling-hover' in state else set(state)))
    if not voices and '.voice-name' in selector:parent=parent.add(Node(classes={'voice-card',theme},state=set(state)))
    target=body
    for index,(join,part) in enumerate(parts):
        if part in {'body','body.voiced'}:
            target=body;parent=body;continue
        node=create(part,state)
        if 'author-profile' in node.classes or 'voice-card' in node.classes:node.classes.add(theme)
        if join in {'+','~'}:
            if not parent.parent:raise Unsupported('Cannot build sibling probe')
            target=parent.parent.add(node)
        else:target=parent.add(node)
        parent=target
    return target


def computed(node,rules,width,cache,inventory):
    if node in cache:return cache[node]
    parent=computed(node.parent,rules,width,cache,inventory) if node.parent else dict(variables={},color=[1,1,1,1],opacity=1,bg=[[0,0,0,0]],properties={})
    winners={}
    for selector,dec,conditions,order in rules:
        if active(conditions,width) and matches(node,selector):
            for name,value,important in dec:
                priority=(important,specificity(selector),order)
                if name not in winners or priority>=winners[name][0]:winners[name]=(priority,value)
    variables=dict(parent['variables']);variables.update({k:v[1] for k,v in winners.items() if k.startswith('--')})
    props={}
    for name,(_,value) in winners.items():
        if name.startswith('--'):continue
        if name in COLOUR_PROPERTIES:
            try:props[name]=expand(value,variables)
            except InvalidVariable:inventory.add((name,value,'invalid computed value; CSS inheritance/initial value applies'))
    if props.get('mix-blend-mode','normal')!='normal':raise Unsupported('Non-text blend artwork needs an explicit named exception')
    if props.get('background-blend-mode','normal')!='normal' or any(k in props for k in {'all','fill','stroke'}):raise Unsupported('Colour reset/blend/SVG paint needs an explicit fixture')
    if '-webkit-text-fill-color' in props:raise Unsupported('Independent text-fill colour requires a rendered measurement')
    if any(k in props and props[k]!='none' for k in ['mask-image','-webkit-mask-image']):
        if 'gitm-lifewire__viewport' not in node.classes:raise Unsupported('Position-dependent mask requires a rendered measurement')
        inventory.add(('mask','lifewire viewport','explicit edge-crop artwork; pixels require rendered acceptance'))
    ink=parent['color']
    if props.get('color') not in {None,'inherit','unset','currentColor'}:
        if props['color']=='initial':ink=[0,0,0,1]
        else:
            try:ink=colour(props['color'],{'__ink':'#ffffff'})
            except ValueError as exc:raise Unsupported(str(exc)) from exc
    t={'__ink':'rgba('+','.join(str(v*255) for v in ink[:3])+','+str(ink[3])+')'}
    candidates=[(winners[k][0],props[k]) for k in ['background','background-color'] if k in winners and k in props]
    bgvalue=max(candidates)[1] if candidates else 'transparent'
    if 'background-image' in props and ('background' not in winners or winners['background-image'][0]>winners['background'][0]):
        if props['background-image']!='none':bgvalue=props['background-image']+', '+bgvalue
    if 'bottom left / 0% 1px' in bgvalue:bgvalue='transparent';inventory.add(('background',props.get('background'),'text underline paint, not a text surface'))
    try:
        if 'gradient(' in bgvalue:
            bgs=gradient_colours(bgvalue,t)
        elif bgvalue.startswith('url('):
            raise Unsupported('Image surface requires a rendered contrast measurement')
        elif bgvalue=='inherit':bgs=[list(pixel) for pixel in parent['bg']]
        elif bgvalue in {'unset','initial'}:bgs=[[0,0,0,0]]
        else:bgs=[colour(bgvalue,t)]
        opacity=float(props.get('opacity','1'))
    except ValueError as exc:raise Unsupported(str(exc)) from exc
    if not 0<=opacity<=1:raise Unsupported('Unsupported opacity value')
    result=dict(variables=variables,color=ink,opacity=opacity,bg=bgs,properties=props)
    cache[node]=result;return result


# Named, reviewed non-text paint rules. No substring filters: focus on portrait
# links and all new selectors still enter the contrast checks.
DECORATIVE={'.atmosphere::before','.atmosphere::after','.noise','.reading-progress','.logo a::before','.nav-links a::after','.btn::after','.btn:hover::after','.voice-card::before','.dispatch-poster::before','.post-card::before','.post-card:hover::before','.author-badge::before','.author-profile::before','.dispatch-feature::before','body.voiced::before','.gitm-topbar__mark','.gitm-topbar__crumb-sep','.gitm-lifewire__dot','.gitm-lifewire__dot--claude','.gitm-lifewire__dot--gemini','.gitm-lifewire__dot--codex','.gitm-lifewire__dot--grok','.gitm-tone__bar','.gitm-tone__fill[data-tone="factual"]','.gitm-tone__fill[data-tone="reflective"]','.gitm-tone__fill[data-tone="argumentative"]','.gitm-tone__fill[data-tone="hedged"]'}


def pairs_for(node,rules,width,inventory):
    cache={};style=computed(node,rules,width,cache,inventory);props=style['properties']
    if props.get('display')=='none' or props.get('visibility')=='hidden':return [],'explicitly hidden'
    if node.attrs.get('aria-disabled')=='true':return [],'disabled control exception'
    if style['opacity']==0:return [],'zero-opacity hidden state'
    fgs=[style['color']]
    if fgs[0][3]==0 and 'gradient(' in props.get('background','') and (props.get('background-clip')=='text' or props.get('-webkit-background-clip')=='text'):
        fgs=style['bg'];style['bg']=[[0,0,0,0]]
    chain=[];current=node
    while current:
        chain.append(current);current=current.parent
    if any(computed(item,rules,width,cache,inventory)['opacity']==0 or computed(item,rules,width,cache,inventory)['properties'].get('display')=='none' for item in chain):return [],'explicitly hidden ancestor'
    output=[]
    for fg in fgs:
        pixels=[(fg,[0,0,0,0])]
        for item in chain:
            s=computed(item,rules,width,cache,inventory);new=[]
            for f,b in pixels:
                for bg in s['bg']:
                    # Both pixels pass through the same group opacity.
                    new.append((filtered(composite(f,bg,s['opacity']),s['properties'].get('filter','none')),filtered(composite(b,bg,s['opacity']),s['properties'].get('filter','none'))))
            pixels=new
        for f,b in pixels:output.append((ratio(over(f,[0,0,0,1]),over(b,[0,0,0,1])),4.5,'text'))
    outline=props.get('outline-color')
    if not outline and 'outline' in props:
        m=re.fullmatch(r'[\d.]+(?:px|rem|em)\s+(?:solid|dashed)\s+(.+)',props['outline'])
        if not m:raise Unsupported('Unsupported focus outline: '+props['outline'])
        outline=m[1]
    if outline:
        actual='rgba('+','.join(str(v*255) for v in style['color'][:3])+','+str(style['color'][3])+')'
        try:ink=colour(outline,{'__ink':actual})
        except ValueError as exc:raise Unsupported(str(exc)) from exc
        canvas=[0,0,0,1]
        for item in reversed(chain[1:]):
            s=cache[item];canvas=over(s['bg'][0],canvas)
        output.append((ratio(over(ink,canvas),canvas),3,'focus outline'))
    return output,None


def composite(foreground,background,opacity):
    alpha=foreground[3]+background[3]*(1-foreground[3])
    rgb=[(foreground[i]*foreground[3]+background[i]*background[3]*(1-foreground[3]))/alpha if alpha else 0 for i in range(3)]
    return rgb+[alpha*opacity]


def filtered(pixel,source):
    if source=='none':return pixel
    rest=source;rgb=pixel[:3]
    while rest.strip():
        match=re.match(r'\s*(brightness|saturate)\(\s*([\d.]+)(%?)\s*\)',rest)
        if not match:raise Unsupported('Unsupported colour filter: '+source)
        amount=float(match[2])/(100 if match[3] else 1)
        if match[1]=='brightness':rgb=[min(1,max(0,x*amount)) for x in rgb]
        else:
            base=sum(w*v for w,v in zip([.213,.715,.072],rgb));rgb=[min(1,max(0,base+(v-base)*amount)) for v in rgb]
        rest=rest[match.end():]
    return rgb+[pixel[3]]


def audit_sources(sources):
    pairs=[];exempt=[];inventory=set();unsupported=[];coverage=[];viewports={}
    for name,source in sources:
        try:
            rules,animation=parse(source)
            widths=viewport_widths(rules)
            # Reuse arithmetic only when the complete active colour cascade is
            # identical. Every boundary width still gets its own reported pairs.
            groups={}
            for width in widths:
                signature=tuple(order for _,dec,conditions,order in rules if relevant(dec) and active(conditions,width))
                groups.setdefault(signature,[]).append(width)
            viewports[name]=dict(widths=widths,distinct_colour_cascades=len(groups))
        except Unsupported as exc:unsupported.append(dict(file=name,error=str(exc)));continue
        voices=name=='voices.css';themes=['neutral','claude','gemini','codex','grok'] if voices else ['claude','gemini','codex','grok']
        coverage.extend(dict(file=name,selector=s,properties=[k for k,_,_ in d],conditions=list(c)) for s,d,c,_ in rules if relevant(d))
        exempt.extend(dict(file=name,selector=s,reason=reason) for s,reason in animation)
        for selector,dec,conditions,_ in rules:
            if not relevant(dec):continue
            if selector in DECORATIVE:
                # Unknown/redefined foreground/focus content is never exempt.
                if any(k in {'color','outline','outline-color'} for k,_,_ in dec):
                    unsupported.append(dict(file=name,selector=selector,error='A decorative paint selector gained foreground/focus semantics'));continue
                exempt.append(dict(file=name,selector=selector,reason='named non-text artwork paint'));continue
            for theme in themes:
                for equivalent in groups.values():
                    width=equivalent[0]
                    if not active(conditions,width):continue
                    for state in [set(),{'hover','focus','focus-visible'},{'sibling-hover'}]:
                        try:
                            target=probe(selector,theme,voices,state)
                            found,reason=pairs_for(target,rules,width,inventory)
                            if reason:exempt.append(dict(file=name,selector=selector,theme=theme,width=width,reason=reason))
                            for value,threshold,role in found:
                                for sampled_width in equivalent:
                                    pairs.append(dict(file=name,selector=selector,theme=theme,width=sampled_width,state='sibling-hover' if 'sibling-hover' in state else 'interactive' if state else 'normal',role=role,ratio=round(value,5),threshold=threshold))
                        except (ValueError,KeyError) as exc:unsupported.append(dict(file=name,selector=selector,theme=theme,width=width,error=str(exc)))
    if not pairs and not unsupported:unsupported.append(dict(error='No colour pairs were examined; empty coverage cannot pass'))
    return dict(declarations=coverage,pairs=pairs,failures=[p for p in pairs if p['ratio']+.00001<p['threshold']],unsupported=unsupported,exceptions=exempt,computed_value_notes=sorted(inventory),viewports=viewports)
