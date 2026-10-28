"""Vista de diseño suavizada; no modifica la rasterización física del solver."""
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageChops
from ..model.domain import active_mask


def source_hit(source,x,y):
    if source.geometry=='Circular':
        return (x-source.x)**2+(y-source.y)**2<=(source.width/2)**2
    return abs(x-source.x)<=source.width/2 and abs(y-source.y)<=source.height/2


def gesture_bounds(start,end,tool):
    xmin,xmax=sorted((start[0],end[0]));ymin,ymax=sorted((start[1],end[1]))
    if tool=='Fuente circular':
        diameter=min(xmax-xmin,ymax-ymin)
        cx,cy=(xmin+xmax)/2,(ymin+ymax)/2
        xmin,xmax=cx-diameter/2,cx+diameter/2
        ymin,ymax=cy-diameter/2,cy+diameter/2
    return xmin,xmax,ymin,ymax


def preview_image(s,regions,sources,width,height,supersample=3):
    g=s.grid;active=active_mask(s)
    rgb=np.full((*g.shape,3),(210,219,224),dtype=np.uint8)
    x,y=g.coordinates()
    for i,r in enumerate(regions):
        hit=(x>=r.xmin)&(x<=r.xmax)&(y>=r.ymin)&(y<=r.ymax)
        rgb[hit]=((110,175,205),(150,205,145),(200,170,125))[i%3]
    rgb[~active]=(16,21,34)
    w,h=width*supersample,height*supersample
    ix=np.rint(np.linspace(0,g.nx-1,w)).astype(int)
    iy=np.rint(np.linspace(g.ny-1,0,h)).astype(int)
    image=Image.fromarray(rgb[iy[:,None],ix]).convert('RGBA')
    clip=Image.fromarray((active[iy[:,None],ix]*255).astype(np.uint8))
    if s.domain.boundary.kind=='Adiabático' and not np.all(active):
        # Rayado sólo en la banda exterior junto al contorno aislado.
        small=clip.resize((width,height),Image.Resampling.NEAREST)
        band=ImageChops.subtract(small.filter(ImageFilter.MaxFilter(13)),small)
        band=band.resize((w,h),Image.Resampling.NEAREST)
        yy,xx=np.indices((h,w))
        stripes=Image.fromarray((((xx+yy)%(10*supersample))<supersample*1.3).astype(np.uint8)*255)
        hatch=ImageChops.multiply(band,stripes)
        image.paste((145,158,174,255),(0,0),hatch)
    for source in sources:
        overlay=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(overlay)
        bounds=((source.x-source.width/2)*w/g.lx,(g.ly-source.y-source.height/2)*h/g.ly,
                (source.x+source.width/2)*w/g.lx,(g.ly-source.y+source.height/2)*h/g.ly)
        color=(245,150,65,180) if source.intensity>=0 else (80,150,245,180)
        shape=draw.ellipse if source.geometry=='Circular' else draw.rectangle
        shape(bounds,fill=color,outline=(90,55,25,255),width=supersample)
        image=Image.composite(Image.alpha_composite(image,overlay),image,clip)
    return image.convert('RGB').resize((width,height),Image.Resampling.LANCZOS)
