"""Dependency-free WCAG source-colour guard, including late CSS overrides.

Inventories all colour/background/opacity declarations in assets/*.css. Tests
text roles on their theme surfaces and gradient endpoints in sRGB, including
alpha compositing, OKLCH conversion, tinted controls and interaction states.
This is a source-pair test, not a DOM cascade/rendered-pixel accessibility audit.
Decorative lines, artwork, hidden animation frames and disabled controls have no
text contrast requirement. Borders that alone identify a control need manual
assessment; focus outlines are checked at 3:1 here.
"""
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def split(value, delimiter=','):
    parts=[]; depth=0; start=0
    for i,c in enumerate(value):
        if c=='(': depth+=1
        if c==')': depth-=1
        if c==delimiter and depth==0: parts.append(value[start:i].strip()); start=i+1
    return parts+[value[start:].strip()]


def rules(text):
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    result={}
    tokens={}
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}',text):
        dec={}
        for item in split(m[2],';'):
            if ':' in item:
                k,v=item.split(':',1); dec[k.strip()]=v.strip().replace(' !important','')
        if m[1].strip()==':root': tokens.update({k:v for k,v in dec.items() if k.startswith('--')})
        for selector in split(m[1]): result.setdefault(selector,{}).update(dec)
    return tokens,result


def resolve(value,tokens):
    while 'var(' in value:
        start=value.rfind('var(');depth=1;end=start+4
        while depth:
            if value[end]=='(':depth+=1
            if value[end]==')':depth-=1
            if depth:end+=1
        parts=split(value[start+4:end]);key=parts[0]
        value=value[:start]+tokens.get(key,','.join(parts[1:]) if len(parts)>1 else 'transparent')+value[end+1:]
    return value


def colour(value,tokens):
    value=resolve(value,tokens).strip().lower()
    if value in ('inherit','currentcolor'): return colour(tokens['__ink'],tokens)
    if value in ('transparent','none'): return [0,0,0,0]
    if value in ('black','white'): return [0,0,0,1] if value=='black' else [1,1,1,1]
    if value.startswith('#'):
        h=value[1:];h=''.join(c*2 for c in h) if len(h) in (3,4) else h
        c=[int(h[i:i+2],16)/255 for i in range(0,len(h),2)]
        return c+[1] if len(c)==3 else c
    if value.startswith('color-mix('):
        mode,a,b=split(value[10:-1]);m=re.fullmatch(r'(.*?)\s+([\d.]+)%',a)
        weight=float(m[2])/100 if m else .5
        first=colour(m[1] if m else a,tokens);second=colour(b,tokens)
        alpha=first[3]*weight+second[3]*(1-weight)
        return [(first[i]*first[3]*weight+second[i]*second[3]*(1-weight))/alpha if alpha else 0 for i in range(3)]+[alpha]
    if value.startswith('oklch('):
        terms=value[6:-1].replace('/',' ').split();light=float(terms[0].rstrip('%'))/(100 if '%' in terms[0] else 1)
        c=float(terms[1]);angle=math.radians(float(terms[2]));a=c*math.cos(angle);b=c*math.sin(angle)
        l=(light+.3963377774*a+.2158037573*b)**3
        m=(light-.1055613458*a-.0638541728*b)**3
        s=(light-.0894841775*a-1.291485548*b)**3
        linear=[4.0767416621*l-3.3077115913*m+.2309699292*s,-1.2684380046*l+2.6097574011*m-.3413193965*s,-.0041960863*l-.7034186147*m+1.707614701*s]
        rgb=[max(0,min(1,12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055)) for x in linear]
        return rgb+[float(terms[3]) if len(terms)>3 else 1]
    if value.startswith(('rgb(','rgba(')):
        terms=re.split(r'[, /]+',value[value.index('(')+1:-1])
        return [float(x)/255 for x in terms[:3]]+[float(terms[3]) if len(terms)>3 else 1]
    raise ValueError('Unrecognised colour: '+value)


def over(a,b): return [a[i]*a[3]+b[i]*(1-a[3]) for i in range(3)]+[1]
def luminance(c):
    a=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c[:3]]
    return sum(v*w for v,w in zip(a,[.2126,.7152,.0722]))
def ratio(a,b):
    x,y=sorted([luminance(a),luminance(b)])
    return (y+.05)/(x+.05)


def backgrounds(value,tokens,base):
    value=resolve(value,tokens)
    if 'gradient(' in value:
        # Endpoints bound the solid source colours. Spatial overlays need a render.
        stops=re.findall(r'#[0-9a-fA-F]{3,8}\b|(?:oklch|rgba?|color-mix)\([^()]*\)',value)
        return [over(colour(c,tokens),base) for c in stops] or [base]
    if value.startswith('url('): return [base]
    return [over(colour(value,tokens),base)]


def audit():
    pairs=[];inventory=[]
    for path in sorted((ROOT/'assets').glob('*.css')):
        tokens,rs=rules(path.read_text(encoding='utf-8'))
        voices=path.name=='voices.css'
        contexts=['neutral','claude','gemini','codex','grok'] if voices else ['claude','gemini','codex','grok']
        for selector,dec in rs.items():
            if any(k in dec for k in ['color','background','background-color','opacity']): inventory.append(dict(file=path.name,selector=selector,declarations={k:v for k,v in dec.items() if k in ['color','background','background-color','opacity']}))
        for context in contexts:
            t=dict(tokens)
            if voices:
                t.update({k:v for k,v in rs['body'].items() if k.startswith('--')})
                if context!='neutral':t.update({k:v for k,v in rs[f'[data-voice="{context}"]'].items() if k.startswith('--')})
                t['__ink']='var(--ink)';surface=colour('var(--paper)',t)
            else:
                t['__ink']='var(--text)';t['--author-color']=t['--'+context]
                surface=colour('var(--void)',t)
            for selector,dec in rs.items():
                if selector.startswith('@') or selector in ['from','to','0%','100%'] or 'aria-disabled' in selector: continue
                if re.search(r'\[data-voice="([^\"]+)"\]',selector) and f'data-voice="{context}"' not in selector:continue
                if 'color' not in dec and 'opacity' not in dec and ':focus' not in selector:continue
                # Artwork/animation and non-text separators are explicitly incidental.
                if any(x in selector for x in ['::before','::after','.noise','.atmosphere','.reading-progress','[data-reveal]','__portrait','__mark','__dot','__crumb-sep','__source-node','__num']):continue
                opacity=float(dec.get('opacity','1')) if re.fullmatch(r'[\d.]+',dec.get('opacity','1')) else 1
                if opacity==0:continue
                fg=colour(dec.get('color','inherit'),t)
                bases=[surface]
                if not voices:
                    # Legacy small text may sit on any of the shared dark surfaces.
                    bases += [colour('var(--surface-2)',t),over(colour('var(--glass-strong)',t),surface)]
                else:
                    if selector.startswith(('.gitm-diff__','.gitm-diff ')) or '__code' in selector or selector.endswith(' pre'):bases=[colour('#000',t)]
                    if selector=='.gitm-diff__n':bases=[colour('#000',t),over(colour('color-mix(in srgb, var(--accent) 12%, transparent)',t),colour('#000',t))]
                    if selector.startswith('.gitm-lifewire__'):opacity*=.92
                    if selector=='.gitm-crossnote__who':bases=[over(colour('color-mix(in srgb, var(--neutral-accent) 8%, transparent)',t),surface)]
                bgvalue=dec.get('background-color',dec.get('background'))
                if selector in ['.btn:hover','.step-number'] and not bgvalue:bgvalue=rs['.btn']['background']
                for base in bases:
                    bgs=backgrounds(bgvalue,t,base) if bgvalue and 'bottom left' not in bgvalue else [base]
                    fgs=backgrounds(dec['background'],t,base) if dec.get('color')=='transparent' and 'gradient(' in dec.get('background','') else [fg]
                    if dec.get('color')=='transparent':bgs=[base]
                    for f in fgs:
                        for bg in bgs:
                            value=ratio(over(f[:3]+[f[3]*opacity],bg),bg)
                            pairs.append(dict(file=path.name,theme=context,selector=selector,foreground=dec.get('color','inherit'),background=bgvalue or 'theme surface',opacity=opacity,ratio=round(value,4),threshold=4.5))
                if ':focus' in selector and 'outline' in dec:
                    value=dec['outline'].split('solid ',1)[-1]
                    pairs.append(dict(file=path.name,theme=context,selector=selector+' [focus outline]',ratio=round(ratio(colour(value,t),surface),4),threshold=3))
    return dict(declarations=inventory,pairs=pairs,failures=[p for p in pairs if p['ratio']<p['threshold']])


if __name__=='__main__':
    assert abs(ratio([1,1,1,1],[0,0,0,1])-21)<1e-9
    assert ratio(colour('#444',{}),[0,0,0,1])<4.5
    assert ratio(colour('#888',{}),[0,0,0,1])>4.5
    report=audit()
    print(json.dumps(report,indent=2))
    print(f"Contrast source contract: {len(report['declarations'])} declarations, {len(report['pairs'])} pairs, {len(report['failures'])} failures")
    raise SystemExit(bool(report['failures']))
