"""CSS colour-space conversion and premultiplied interpolation.

Coordinates stay unclipped during interpolation; gamut clipping happens only
when the final colour is painted into the source guard's sRGB canvas.
"""
import math
import re


def linear(value):
    return value/12.92 if abs(value)<=.04045 else math.copysign(((abs(value)+.055)/1.055)**2.4,value)


def encoded(value):
    return value*12.92 if abs(value)<=.0031308 else math.copysign(1.055*abs(value)**(1/2.4)-.055,value)


def lab_to_linear(lab):
    light,a,b=lab
    l=(light+.3963377774*a+.2158037573*b)**3
    m=(light-.1055613458*a-.0638541728*b)**3
    s=(light-.0894841775*a-1.291485548*b)**3
    return [4.0767416621*l-3.3077115913*m+.2309699292*s,
            -1.2684380046*l+2.6097574011*m-.3413193965*s,
            -.0041960863*l-.7034186147*m+1.707614701*s]


def linear_to_lab(rgb):
    r,g,b=rgb
    cube=lambda v:math.copysign(abs(v)**(1/3),v)
    l=cube(.4122214708*r+.5363325363*g+.0514459929*b)
    m=cube(.2119034982*r+.6806995451*g+.1073969566*b)
    s=cube(.0883024619*r+.2817188376*g+.6299787005*b)
    return [.2104542553*l+.7936177850*m-.0040720468*s,
            1.9779984951*l-2.4285922050*m+.4505937099*s,
            .0259040371*l+.7827717662*m-.8086757660*s]


def convert(coords,source,target):
    if source not in {'srgb','srgb-linear','oklab','oklch'} or target not in {'srgb','srgb-linear','oklab','oklch'}:raise ValueError('Unsupported colour space')
    if len(coords)!=3 or not all(math.isfinite(v) for v in coords):raise ValueError('Non-finite colour coordinate')
    if source==target:return list(coords)
    if source=='oklch':
        light,chroma,hue=coords;angle=math.radians(hue)
        coords=[light,chroma*math.cos(angle),chroma*math.sin(angle)];source='oklab'
    if source=='oklab':rgb=lab_to_linear(coords)
    elif source=='srgb':rgb=[linear(v) for v in coords]
    elif source=='srgb-linear':rgb=list(coords)
    else:raise ValueError('Unsupported interpolation colour space: '+source)
    if target=='srgb-linear':return rgb
    if target=='srgb':return [encoded(v) for v in rgb]
    lab=linear_to_lab(rgb)
    if target=='oklab':return lab
    if target=='oklch':return [lab[0],math.hypot(lab[1],lab[2]),math.degrees(math.atan2(lab[2],lab[1]))%360]
    raise ValueError('Unsupported interpolation colour space: '+target)


def mix(header,first,second,weight1,weight2):
    match=re.fullmatch(r'in\s+(srgb|srgb-linear|oklab|oklch)(?:\s+(shorter|longer|increasing|decreasing)\s+hue)?',header)
    if not match:raise ValueError('Unsupported color-mix interpolation space or hue method: '+header)
    space,method=match.groups();method=method or 'shorter'
    if match[2] and space!='oklch':raise ValueError('Hue methods require a polar colour space')
    if weight1 is None and weight2 is None:weight1=weight2=50
    elif weight1 is None:weight1=100-weight2
    elif weight2 is None:weight2=100-weight1
    if not 0<=weight1<=100 or not 0<=weight2<=100 or weight1+weight2==0:raise ValueError('Invalid color-mix weights')
    total=weight1+weight2;w1,w2=weight1/total,weight2/total
    a=convert(first[1],first[0],space);b=convert(second[1],second[0],space)
    alpha=first[2]*w1+second[2]*w2
    if alpha==0:return space,[0,0,0],0
    coords=[(a[i]*first[2]*w1+b[i]*second[2]*w2)/alpha for i in range(3)]
    if space=='oklch':
        # Hue is not premultiplied. A powerless/transparent endpoint borrows
        # the other hue, rather than pulling the mix towards arbitrary zero.
        h1,h2=a[2]%360,b[2]%360
        powerless1=abs(a[1])<1e-7 or first[2]==0
        powerless2=abs(b[1])<1e-7 or second[2]==0
        if powerless1:h1=h2
        if powerless2:h2=h1
        difference=h2-h1
        if method=='shorter':
            if difference>180:difference-=360
            elif difference < -180:difference+=360
        elif method=='longer':
            if 0<difference<180:difference-=360
            elif -180<difference<=0:difference+=360
        elif method=='increasing' and difference<0:difference+=360
        elif method=='decreasing' and difference>0:difference-=360
        coords[2]=(h1+difference*w2)%360
    return space,coords,alpha*min(1,total/100)
