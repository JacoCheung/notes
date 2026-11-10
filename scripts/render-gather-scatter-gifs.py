#!/usr/bin/env python3
"""Render GIFs from animation-model.js. Requires Node.js and Pillow.

Generate outside the worktree, then copy the finished GIFs into the article assets:
  python3.11 scripts/render-gather-scatter-gifs.py --output-dir /path/to/scratch/gifs
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageColor

ROOT = Path(__file__).resolve().parents[1]
COLORS = {'bg':'#ffffff', 'ink':'#17202d', 'muted':'#626d7b', 'border':'#b4bfcc',
          'cell':'#f6f8fb', 'flow':'#245bc2', 'read':'#eaf1ff', 'write':'#e3f4ee',
          'index':'#fff1ce', 'gold':'#a66b0a', 'green':'#168065'}


def cases():
    script = '''const m=require(process.argv[1]), result=[];
for(const op of ['gather','scatter','scatter_add']) for(const pass of ['forward','backward'])
for(const dim of [0,1]) for(const indices of ['unique','repeated']) {
 const model=m.create({op,pass,dim,indices});
 result.push({config:model.config,states:Array.from({length:19},(_,i)=>model.snapshot(i))});
} console.log(JSON.stringify(result));'''
    return json.loads(subprocess.check_output(['node', '-e', script, str(ROOT/'assets/pytorch-internals/gather-scatter/animation-model.js')]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--font', type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    font_path = args.font or Path(subprocess.check_output(['fc-match','-f','%{file}','monospace']).decode())
    fonts = {size: ImageFont.truetype(str(font_path), size) for size in [14,16,18,22,25]}
    rgb = list(dict.fromkeys(ImageColor.getrgb(v) for v in COLORS.values()))
    for color in list(rgb):
        for alpha in [.2,.4,.6,.8]:
            rgb.append(tuple(round(255*(1-alpha)+v*alpha) for v in color))
    palette = Image.new('P',(1,1))
    palette.putpalette([v for color in rgb for v in color] + [0]*(768-3*len(rgb)))

    def draw(config, state, progress=0.):
        extra = len(state['matrices']) == 4
        height = (780 if config['dim']==0 else 680) if extra else 560
        image = Image.new('RGB',(1000,height),COLORS['bg'])
        d = ImageDraw.Draw(image)
        title = f"{config['op']} / {config['pass']} / dim={config['dim']}"
        d.text((30,24),title,font=fonts[25],fill=COLORS['ink'])
        d.text((30,64),f"{config['indices']} indices | coordinate mapping, not GPU execution order",font=fonts[16],fill=COLORS['muted'])
        positions={}; right_edges={}
        for n,matrix in enumerate(state['matrices']):
            x = [30,370,710,710][n]; y = 132 if n<3 else 420
            a=matrix['values']; right_edges[matrix['key']]=x+78+(len(a[0])-1)*54
            d.text((x,y),f"{matrix['key']} [{len(a)},{len(a[0])}]",font=fonts[18],fill=COLORS['ink'])
            for j in range(len(a[0])):
                d.text((x+53+j*54,y+34),str(j),font=fonts[14],fill=COLORS['muted'],anchor='mm')
            for i,row in enumerate(a):
                d.text((x+10,y+72+i*48),str(i),font=fonts[14],fill=COLORS['muted'],anchor='mm')
                for j,value in enumerate(row):
                    rect=(x+30+j*54,y+52+i*48,x+78+j*54,y+94+i*48)
                    positions[(matrix['key'],i,j)]=rect
                    fill,stroke,width=COLORS['cell'],COLORS['border'],1
                    active=state['active']
                    if active:
                        if matrix['key']=='index' and [i,j]==active['index']:fill,stroke,width=COLORS['index'],COLORS['gold'],3
                        if state['phase']>=1 and matrix['key']==state['inputKey'] and [i,j]==active['from']:fill,stroke,width=COLORS['read'],COLORS['flow'],3
                        hit=matrix['key']==state['outputKey'] and [i,j]==active['to']
                        clear=matrix['key']=='dbase' and config['op']=='scatter' and [i,j]==active['mapped']
                        if (state['phase']>=1 and hit) or (state['phase']==2 and clear):fill,stroke,width=COLORS['write'],COLORS['green'],3
                    d.rounded_rectangle(rect,radius=3,fill=fill,outline=stroke,width=width)
                    d.text(((rect[0]+rect[2])/2,(rect[1]+rect[3])/2),'.' if value is None else str(value),font=fonts[22],fill=COLORS['ink'],anchor='mm')
        active=state['active']
        if active:
            source=f"{state['inputKey']}[{','.join(map(str,active['from']))}]"
            target=f"{state['outputKey']}[{','.join(map(str,active['to']))}]"
            add=config['op']=='gather' if config['pass']=='backward' else config['op']=='scatter_add'
            formula=f"{target} {'+=' if add else '='} {source} ({active['value']})"
            if state['phase']==0:formula=f"index[{','.join(map(str,active['index']))}] = {active['k']}"
            d.text((30,96),formula,font=fonts[18],fill=COLORS['ink'])
            label=['Select index','Read source','Update target'][state['phase']]
            d.text((30,height-104),f"Element {state['activeIndex']+1}/6 | {label} | {state['cursor']}/18",font=fonts[18],fill=COLORS['ink'])
            if state['phase']>=1:
                sr=positions[(state['inputKey'],*active['from'])];tr=positions[(state['outputKey'],*active['to'])]
                # Highlights locate the cells; the value travels through the
                # inter-panel gap without crossing unrelated cell contents.
                a=(right_edges[state['inputKey']]+24,(sr[1]+sr[3])/2);end=(686,(tr[1]+tr[3])/2)
                mid=(a[0]+end[0])/2;b=(mid,a[1]);c=(mid,end[1])
                def point(t):
                    u=1-t
                    return tuple(u**3*a[k]+3*u*u*t*b[k]+3*u*t*t*c[k]+t**3*end[k] for k in (0,1))
                points=[point(i/40) for i in range(41)]
                d.line(points,fill=COLORS['flow'],width=3)
                angle=math.atan2(end[1]-points[-2][1],end[0]-points[-2][0])
                d.polygon([end]+[(end[0]-10*math.cos(angle+s),end[1]-10*math.sin(angle+s)) for s in [-.5,.5]],fill=COLORS['flow'])
                if state['phase']==1:
                    px,py=point(progress);d.rounded_rectangle((px-21,py-17,px+21,py+17),radius=6,fill=COLORS['flow'])
                    d.text((px,py),str(active['value']),font=fonts[18],fill='white',anchor='mm')
        else:d.text((30,height-104),'Ready: output initialized; no elements processed.',font=fonts[18],fill=COLORS['ink'])
        if state['collision']:
            d.text((30,height-68),'Repeated overwrite: ? has no promised winner.',font=fonts[16],fill=COLORS['gold'])
            d.text((30,height-43),'Its returned source gradient is not a correct overwrite derivative.',font=fonts[16],fill=COLORS['gold'])
        else:d.text((30,height-56),'Gold: index    Blue: source / data flow    Green: destination',font=fonts[16],fill=COLORS['muted'])
        return image.quantize(palette=palette,dither=Image.Dither.NONE)

    for case in cases():
        config,states=case['config'],case['states']; frames=[draw(config,states[0])]; durations=[700]
        for state in states[1:]:
            fractions=[0,.25,.5,.75,1] if state['phase']==1 else [0]
            for fraction in fractions:
                frames.append(draw(config,state,fraction));durations.append(120 if state['phase']==1 else 600)
        durations[-1]=1800
        name=f"{config['op']}-{config['pass']}-dim{config['dim']}-{config['indices']}.gif"
        path=args.output_dir/name
        frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=1)
        with Image.open(path) as gif:
            assert gif.n_frames>18 and gif.info['loop']==0
            gif.seek(gif.n_frames-1)
        print(name,path.stat().st_size,flush=True)


if __name__=='__main__':
    main()
