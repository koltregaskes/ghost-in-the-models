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
