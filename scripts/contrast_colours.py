"""WCAG sRGB/OKLCH colour arithmetic used by the fail-closed cascade guard."""
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


def interpolation_colour(value,tokens):
    from colour_spaces import mix
    value=resolve(value,tokens).strip().lower()
    if value in ('inherit','currentcolor'):return interpolation_colour(tokens['__ink'],tokens)
    if value in ('transparent','none'):return 'srgb',[0,0,0],0
    if value in ('black','white'):return 'srgb',([0,0,0] if value=='black' else [1,1,1]),1
    if value.startswith('#'):
        h=value[1:]
        if len(h) not in {3,4,6,8} or not re.fullmatch('[0-9a-f]+',h):raise ValueError('Invalid hex colour')
        if len(h) in {3,4}:h=''.join(c*2 for c in h)
        c=[int(h[i:i+2],16)/255 for i in range(0,len(h),2)]
        return 'srgb',c[:3],c[3] if len(c)==4 else 1
    if value.startswith('color-mix(') and value.endswith(')'):
        parts=split(value[10:-1])
        if len(parts)!=3:raise ValueError('color-mix requires two colours')
        parsed=[]
        for part in parts[1:]:
            match=re.fullmatch(r'(.*?)\s+([\d.]+)%',part)
            parsed.append((interpolation_colour(match[1] if match else part,tokens),float(match[2]) if match else None))
        return mix(parts[0],parsed[0][0],parsed[1][0],parsed[0][1],parsed[1][1])
    if value.startswith(('oklab(','oklch(')) and value.endswith(')'):
        name=value[:5];terms=value[6:-1].replace('/',' ').split()
        if len(terms) not in {3,4} or any('%' in v for v in terms[1:]):raise ValueError('Unsupported OKLab/OKLCH syntax')
        light=float(terms[0].rstrip('%'))/(100 if '%' in terms[0] else 1)
        coords=[light,float(terms[1]),float(terms[2])]
        return name,coords,float(terms[3]) if len(terms)==4 else 1
    if value.startswith(('rgb(','rgba(')) and value.endswith(')'):
        terms=re.split(r'[, /]+',value[value.index('(')+1:-1])
        if len(terms) not in {3,4}:raise ValueError('Unsupported RGB syntax')
        return 'srgb',[float(x)/255 for x in terms[:3]],float(terms[3]) if len(terms)==4 else 1
    raise ValueError('Unrecognised colour: '+value)


def colour(value,tokens):
    from colour_spaces import convert
    space,coords,alpha=interpolation_colour(value,tokens)
    if not 0<=alpha<=1:raise ValueError('Unsupported alpha outside 0..1')
    rgb=convert(coords,space,'srgb')
    return [max(0,min(1,v)) for v in rgb]+[alpha]


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
