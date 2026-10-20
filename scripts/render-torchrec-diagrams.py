#!/usr/bin/env python3
"""Render twelve original row-wise sequences and three pipeline sequences.

The adjacent JSON preserves original actors, steps, trace annotations, provenance,
explicit activation scopes, and source-grounded H2D / host-sync expansions.
Sample activity IDs, sizes and backend kernels are not universal guarantees.
Uses only the Python 3.8+ standard library; run from any directory.
"""
from html import escape
import json
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/torchrec-row-wise-sharding-pipeline'
DATA = json.loads(Path(__file__).with_name('torchrec-row-wise-sequences.json').read_text())
REV = DATA['revision']
COLORS = {kind:f'var(--{kind})' for kind in ('call','return','comm','h2d','host','wait','dep','boundary')}
FILLS = {kind:f'var(--{kind}-fill)' for kind in ('comm','h2d','host','wait','dep')}
FILLS['call']='var(--surface)'
FILLS['return']='var(--surface)'
TAGS = {'h2d':('H','H2D · host metadata / batch → CUDA'),
        'host':('D','D2H / HOST SYNC · CPU needs CUDA values'),
        'comm':('A','ALLTOALL · collective launch'),
        'wait':('W','WAIT · consume request; not a blanket host barrier'),
        'dep':('S','STREAM DEPENDENCY · GPU ordering')}
PLOT_LEFT = 48
PLOT_RIGHT = 1552
SVG_STYLE = '''
:root{color-scheme:light dark;--surface:#fdfdfe;--header:#f3f5f7;--ink:#202936;--muted:#526071;--rule:#dce1e7;--lifeline:#5b708b;--actor-border:#445c79;--activation:#e3e8ee;--activation-stroke:#445c79;--nested:#c5d0dc;--tag-ink:#fdfdfe;--link:#4b5f78;--call:#344256;--return:#59697c;--comm:#6f42a8;--h2d:#245cb4;--host:#b63838;--wait:#885c14;--dep:#187264;--boundary:#b63838;--comm-fill:#f3eff9;--h2d-fill:#edf3fc;--host-fill:#fcf0ef;--wait-fill:#fbf6e9;--dep-fill:#edf7f3}
DARK_TOKENS
svg{fill:var(--ink)}text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
.mono,.source-link text,.step-number{font-family:ui-monospace,"SFMono-Regular",Consolas,"Liberation Mono",monospace;font-variant-ligatures:none}
.muted{fill:var(--muted)}.source-link text{fill:var(--link)}
a{cursor:pointer}a:focus{outline:none}a:hover text,a:focus-visible text{text-decoration:underline;text-underline-offset:4px}
.activation,.pending-request,.annotation-bg{pointer-events:none}
.message-link:hover .message-bg,.message-link:focus-visible .message-bg{stroke:var(--lifeline)}
.source-link:hover text,.source-link:focus-visible text{fill:var(--ink)}
.source-link:focus-visible .source-bg{stroke:var(--lifeline)}
'''
DARK_TOKENS = '--surface:#171b22;--header:#202631;--ink:#e7ebf1;--muted:#aeb9c9;--rule:#343d4b;--lifeline:#8ea3bf;--actor-border:#a1bad7;--activation:#303d4e;--activation-stroke:#a1bad7;--nested:#52647b;--tag-ink:#171b22;--link:#bac8dd;--call:#c4d0df;--return:#aab8cb;--comm:#c4a6ed;--h2d:#9dbff2;--host:#f0aaa5;--wait:#dfc086;--dep:#94ceb8;--boundary:#f0aaa5;--comm-fill:#282235;--h2d-fill:#1d293c;--host-fill:#322327;--wait-fill:#2e291f;--dep-fill:#1c2e2b'
SVG_STYLE = SVG_STYLE.replace('DARK_TOKENS', ':root[data-theme="dark"]{'+DARK_TOKENS+'}\n@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){'+DARK_TOKENS+'}}')


def wrapped(text, limit):
    return textwrap.wrap(text,width=limit,break_long_words=False,break_on_hyphens=False) or ['']


def source_label(url):
    path,anchor=url.rsplit('#',1)
    return path.rsplit('/',1)[-1]+':'+anchor.replace('L','')


def link(url,title,cls):
    return (f'<a class="{cls}" href="{escape(url,quote=True)}" xlink:href="{escape(url,quote=True)}" '
            f'target="_blank" rel="noopener noreferrer" tabindex="0" aria-label="{escape(title,quote=True)}">'
            f'<title>{escape(title)}</title>')


def wrap_to(text, width, unit):
    # Conservative glyph widths; long identifiers can wrap inside their link.
    return textwrap.wrap(text, width=max(12, int(width/unit)),
                         break_long_words=True, break_on_hyphens=False)


def wrap_message(text, width):
    """Prefer call/argument boundaries to splitting identifiers like row_wise."""
    limit=max(12,int(width/10.2));lines=[];line=''
    for part in re.split(r'(?<=[(\[,])|(?=[(\[])|(\s+)',text):
        if not part:continue
        if len(line+part)<=limit:
            line+=part
        else:
            if line.strip():lines.append(line.rstrip())
            chunks=textwrap.wrap(part.lstrip(),width=limit,break_on_hyphens=False)
            lines.extend(chunks[:-1]);line=chunks[-1] if chunks else ''
    if line.strip():lines.append(line.rstrip())
    return lines


def annotation_layout(row, width):
    # Put event metadata above its message, in the same activation-free window.
    # A dedicated full-height label column otherwise looks like an empty actor.
    tag=None;label_top=28
    if row['kind'] in TAGS:
        heading,detail=TAGS[row['kind']][1].split(' · ',1)
        badge_width=max(36,len(row.get('tag',''))*8+12)
        headings=wrap_to(row.get('tag_heading',heading),width-badge_width-20,8.0)
        # Definitions live in the shared legend and event tooltip. Only custom
        # per-step data (e.g. the input/output collective counts) repeats here.
        details=wrap_to(row.get('tag_detail',''),width-10,7.7)
        detail_top=28+20*len(headings)
        tag_bottom=(detail_top+20*(len(details)-1)) if details else detail_top-20
        comm_lines=[];comm_top=tag_bottom+22
        if row.get('also_comm'):
            comm_lines=wrap_to('Then AllToAll: lengths + ID payloads',width-18,7.8)
            tag_bottom=comm_top+20*(len(comm_lines)-1)+6
        tag=dict(badge_width=badge_width,headings=headings,details=details,detail_top=detail_top,
                 comm_lines=comm_lines,comm_top=comm_top)
        label_top=tag_bottom+32
    labels=wrap_message(row['label'],width-10)
    details=wrap_to(row.get('detail',''),width-10,8.0)
    sources=[];sx=0;sy=0;line_height=0
    for url in dict.fromkeys(row['sources']):
        lines=wrap_to(source_label(url),width-12,8.2)
        bw=min(width,max(len(line)*8.2 for line in lines)+12)
        bh=19*len(lines)
        if sx and sx+bw>width:
            sx=0;sy+=line_height+7;line_height=0
        sources.append((url,lines,sx,sy,bw))
        sx+=bw+8;line_height=max(line_height,bh)
    label_bottom=label_top+23*(len(labels)-1)
    arrow=label_bottom+21
    detail_top=arrow+33
    source_top=(detail_top+20*(len(details)-1)+27) if details else arrow+33
    height=max(112,source_top+sy+line_height+20)
    used_width=max([len(line)*10.2+6 for line in labels]
                   +[len(line)*8+4 for line in details]
                   +[sx+bw for _,_,sx,_,bw in sources])
    if tag:
        used_width=max([used_width]+[tag['badge_width']+12+len(line)*8+4 for line in tag['headings']]
                       +[len(line)*7.7+4 for line in tag['details']]
                       +[len(line)*7.8+14 for line in tag['comm_lines']])
    return dict(tag=tag,label_top=label_top,labels=labels,details=details,sources=sources,arrow=arrow,
                detail_top=detail_top,source_top=source_top,height=height,used_width=used_width)


def text_windows(d, xs, step):
    """Reserve horizontal corridors for every activation / pending request.

    This is conservative for the first and last row of a scope. Using the whole
    row also keeps future label-height changes away from execution bars.
    """
    obstacles=[]
    for actor,first,last,_ in d['activations']:
        if first<=step<=last:
            obstacles.append((xs[actor]-22,xs[actor]+32))
    for actor,first,last,depth,_ in d.get('pending',[]):
        if first<=step and (last is None or step<=last):
            left=xs[actor]+23+depth*15
            obstacles.append((left-12,left+22))
    windows=[];left=PLOT_LEFT+12
    for start,end in sorted(obstacles):
        if start>left:windows.append((left,start))
        left=max(left,end)
    if left<PLOT_RIGHT-14:windows.append((left,PLOT_RIGHT-14))
    return [(a,b) for a,b in windows if b-a>=125]


def render(d):
    width=1600;top=296;rows=d['rows'];actors=d['actors']
    plot_left=PLOT_LEFT;lane=(PLOT_RIGHT-plot_left)/len(actors)
    xs=[plot_left+lane*(i+.5) for i in range(len(actors))]
    layout=[];messages={};y=top;n=0
    for row in rows:
        k=row['kind']
        if k in ('note','phase'):
            # Between messages, only scopes continuing past the previous
            # message may intersect this strip.
            candidates=text_windows(d,xs,n+.5)
            lx,end=max(candidates,key=lambda pair:pair[1]-pair[0])
            available=end-lx-8
            lines=wrap_to(row['label'],available,8.4)
            h=max(54,30+21*len(lines))
            item=dict(row=row,y=y,height=h,x=lx,lines=lines)
        else:
            n+=1;a,b=row['a'],row['b']
            preferred=min(xs[a],xs[b])+28
            candidates=[]
            for left,right in text_windows(d,xs,n):
                # Keep annotations close to their calls, including self-calls
                # on the last actor. Cap long prose lines for easier scanning.
                full=annotation_layout(row,min(850,right-left-8))
                aligned=max(left,min(preferred,right-full['used_width']-12))
                for lx in {left,max(left,min(preferred,right-260)),aligned}:
                    available=min(850,right-lx-8)
                    ann=annotation_layout(row,available)
                    end=lx+ann['used_width']
                    distance=max(lx-preferred,preferred-end,0)
                    score=ann['height']+abs(lx-preferred)*.10+distance*.10
                    candidates.append((score,lx,ann))
            _,lx,ann=min(candidates,key=lambda item:item[0])
            h=ann['height']
            item=dict(row=row,y=y,height=h,x=lx,number=n,annotation=ann)
            messages[n]=item
        layout.append(item);y+=h
    notes=[line for note in d['notes'] for line in wrapped(note,156)]
    height=y+100+len(notes)*23;scopes=d['activations']
    for a,first,last,_ in scopes:
        assert 0<=a<len(actors) and first<=last and last in messages,(d['slug'],a,first,last)
    def arrow_y(number):
        item=messages[number]
        return item['y']+item['annotation']['arrow']
    description=d['subtitle']+' Solid bars: logical execution/access scopes; hollow dashed bars: unconsumed requests. Blue H2D, red D2H/host sync, purple AllToAll, amber request wait, green stream dependency. '
    description+=' '.join(r['label']+' '+r.get('detail','') for r in rows)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="group" aria-labelledby="title desc">',
         f'<title id="title">{escape(d["title"])}</title><desc id="desc">{escape(description)}</desc>',
         '<style>'+SVG_STYLE+'</style><defs>']
    for k,c in COLORS.items():
        out.append(f'<marker id="{k}" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="{c}"/></marker>')
    out+=['</defs><rect class="canvas" width="100%" height="100%" fill="var(--surface)"/>',
          f'<text x="48" y="43" font-size="26" font-weight="600">{escape(d["title"])}</text>',
          f'<text class="muted" x="48" y="72" font-size="15">{escape(d["subtitle"])}</text>']
    for x,k,label in [(48,'h2d','H2D'),(210,'host','D2H / host sync'),(480,'comm','AllToAll'),(720,'wait','Request wait'),(1000,'dep','Stream dependency')]:
        out.append(f'<rect x="{x}" y="97" width="22" height="14" rx="3" fill="{FILLS[k]}"/><rect x="{x}" y="97" width="4" height="14" rx="2" fill="{COLORS[k]}"/><text class="muted" x="{x+32}" y="109" font-size="14">{label}</text>')
    out+=['<rect x="48" y="129" width="12" height="20" rx="2" fill="var(--activation)" stroke="var(--activation-stroke)"/><text class="muted" x="72" y="144" font-size="13.5">Activation / access scope; nested bars = self-calls</text>',
          '<rect x="540" y="129" width="10" height="20" rx="2" fill="var(--comm-fill)" stroke="var(--comm)" stroke-dasharray="3 4"/><text class="muted" x="564" y="144" font-size="13.5">Pending request, not GPU duration</text>',
          '<text class="muted" x="1000" y="144" font-size="13.5">Messages and file references link to source ↗</text>']
    explanation=('Example activity IDs and sizes vary by execution; source links identify TorchRec callsites for backend work.' if d.get('trace')
                 else 'Host submission order and logical dependencies; bar lengths are not measured execution times.')
    out.append(f'<text class="muted" x="48" y="174" font-size="13.5">{explanation}</text>')
    # Explicit SVG painter order: ALL structural backgrounds precede lifelines
    # and activations. Event labels share the message's safe text window.
    out.append('<g class="background-layer">')
    for i in range(len(actors)):
        out.append(f'<rect class="actor-lane" x="{plot_left+lane*i}" y="200" width="{lane}" height="{y-200}" fill="none"/>')
    counters={k:0 for k in TAGS}
    for item in layout:
        row=item['row'];ry=item['y'];h=item['height'];k=row['kind']
        if k in TAGS:
            counters[k]+=1;item['tag']=row.get('tag',TAGS[k][0]+str(counters[k]))
            out.append(f'<rect class="highlight highlight-{k}" data-kind="{k}" x="48" y="{ry+4}" width="{width-96}" height="{h-8}" rx="5" fill="{FILLS[k]}"/><rect x="48" y="{ry+4}" width="3" height="{h-8}" rx="1.5" fill="{COLORS[k]}"/>')
        elif k in ('note','phase'):
            fill='var(--header)' if k=='phase' else 'var(--surface)'
            out.append(f'<rect class="{k}-bg" x="48" y="{ry+2}" width="{width-96}" height="{h-4}" rx="4" fill="{fill}"/>')
    out.append('</g><g class="lifeline-layer">')
    for x,actor in zip(xs,actors):
        out.append(f'<line class="lifeline" x1="{x}" y1="276" x2="{x}" y2="{y}" stroke="var(--lifeline)" stroke-width="1.8" stroke-dasharray="6 6"/>')
        out.append(f'<rect class="actor-header" x="{x-lane/2+5}" y="200" width="{lane-10}" height="76" rx="5" fill="var(--header)" stroke="var(--actor-border)" stroke-width="1.8"/>')
        name=actor['name'];parts=[name]
        if len(name)>25:
            words=re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z0-9_]*|[^A-Z]+',name)
            if len(words)>1:
                split=min(range(1,len(words)),key=lambda k:abs(len(''.join(words[:k]))-len(''.join(words[k:]))))
                parts=[''.join(words[:split]),''.join(words[split:])]
        for k,line in enumerate(parts):
            fs=min(16,(lane-26)/(max(len(line),1)*.59))
            out.append(f'<text x="{x}" y="{225+k*19 if len(parts)>1 else 234}" text-anchor="middle" font-size="{fs:.1f}" font-weight="600">{escape(line)}</text>')
        fs=min(13,(lane-26)/(max(len(actor["type"]),1)*.55))
        out.append(f'<text class="muted" x="{x}" y="263" text-anchor="middle" font-size="{fs:.1f}">{escape(actor["type"])}</text>')
    out.append('</g><g class="activation-layer">')
    for a,first,last,depth,label in d.get('pending',[]):
        sy=arrow_y(first);ey=arrow_y(last) if last else y-8
        out.append(f'<rect class="pending-request" x="{xs[a]+23+depth*15}" y="{sy}" width="10" height="{ey-sy}" rx="2" fill="var(--comm-fill)" stroke="var(--comm)" stroke-dasharray="3 4"><title>{escape(label)}; pending handle, not execution duration</title></rect>')
    for a,first,last,kind in scopes:
        sy=arrow_y(first)-8;ey=arrow_y(last)+24
        out.append(f'<rect class="activation" data-actor="{a}" data-start="{first}" data-end="{last}" x="{xs[a]-8}" y="{sy}" width="16" height="{ey-sy}" rx="2" fill="var(--activation)" stroke="var(--activation-stroke)" stroke-width="1.5"><title>{escape(actors[a]["name"])}: scope {first}-{last}</title></rect>')
    for number,item in messages.items():
        row=item['row'];a,b=row['a'],row['b'];ay=arrow_y(number)
        if a==b and row['kind']!='boundary':
            out.append(f'<rect class="activation nested" x="{xs[a]}" y="{ay-5}" width="16" height="23" rx="2" fill="var(--nested)" stroke="var(--activation-stroke)" stroke-width="1.5"/>')
    out.append('</g><g class="message-layer">')
    for item in layout:
        row=item['row'];ry=item['y'];h=item['height'];k=row['kind'];lx=item['x']
        out.append(f'<g class="row-content" data-top="{ry}" data-bottom="{ry+h}">')
        if k in ('phase','note'):
            for idx,line in enumerate(item['lines']):
                fill='var(--header)' if k=='phase' else 'var(--surface)'
                out.append(f'<rect class="annotation-bg" x="{lx-3}" y="{ry+12+21*idx}" width="{len(line)*8.4+6}" height="21" rx="2" fill="{fill}"/>')
                out.append(f'<text x="{lx}" y="{ry+28+21*idx}" font-size="15" font-weight="{600 if k=="phase" else 400}" fill="var(--ink)">{escape(line)}</text>')
            out.append('</g>');continue
        n=item['number'];ann=item['annotation'];a,b=row['a'],row['b'];color=COLORS[k];fill=FILLS.get(k,'var(--surface)')
        if k in TAGS:
            tag=ann['tag']
            badge_width=tag['badge_width']
            out.append(f'<g class="event-tag"><title>{escape(TAGS[k][1])}</title><rect x="{lx}" y="{ry+10}" width="{badge_width}" height="24" rx="4" fill="{color}"/><text class="mono" x="{lx+badge_width//2}" y="{ry+27}" text-anchor="middle" font-size="13" font-weight="600" fill="var(--tag-ink)">{item["tag"]}</text>')
            for idx,line in enumerate(tag['headings']):
                ty=ry+28+20*idx
                out.append(f'<rect class="annotation-bg" x="{lx+badge_width+10}" y="{ty-14}" width="{len(line)*8+4}" height="19" fill="{fill}"/><text x="{lx+badge_width+12}" y="{ty}" font-size="13" font-weight="600" fill="{color}">{escape(line)}</text>')
            for idx,line in enumerate(tag['details']):
                ty=ry+tag['detail_top']+20*idx
                out.append(f'<rect class="annotation-bg" x="{lx-2}" y="{ty-14}" width="{len(line)*7.7+4}" height="19" fill="{fill}"/><text x="{lx}" y="{ty}" font-size="14" fill="{color}">{escape(line)}</text>')
            if tag['comm_lines']:
                cy=ry+tag['comm_top'];cw=max(map(len,tag['comm_lines']))*7.8+14
                out.append(f'<rect class="highlight highlight-comm" data-kind="comm" x="{lx-2}" y="{cy-15}" width="{cw}" height="{20*len(tag["comm_lines"])+6}" rx="4" fill="var(--comm-fill)"/>')
                for idx,line in enumerate(tag['comm_lines']):
                    out.append(f'<text x="{lx+4}" y="{cy+20*idx}" font-size="13.5" font-weight="600" fill="var(--comm)">{escape(line)}</text>')
            out.append('</g>')
        else:
            out.append(f'<text class="step-number muted" x="20" y="{ry+28}" font-size="12">{n:02}</text>')
        ay=arrow_y(n);direction=1 if b>=a else -1
        def edge(actor,sign):
            return xs[actor]+(8*sign if any(ac==actor and first<=n<=last for ac,first,last,_ in scopes) else 0)
        x1,x2=edge(a,direction),edge(b,-direction)
        out.append(f'<g class="message" data-step="{n}" data-kind="{k}">')
        out.append(link(row['sources'][0],row['label'],'message-link'))
        for idx,line in enumerate(ann['labels']):
            ty=ry+ann['label_top']+23*idx;tw=len(line)*10.2+6
            out.append(f'<rect class="annotation-bg message-bg" x="{lx-3}" y="{ty-17}" width="{tw}" height="22" rx="3" fill="{fill}"/><text class="mono" x="{lx}" y="{ty}" font-size="16" font-weight="500" fill="{color}">{escape(line)}</text>')
        path=f'M{x1} {ay} H{xs[a]+42} V{ay+16} H{xs[a]+16}' if a==b else f'M{x1} {ay} H{x2}'
        dash=' stroke-dasharray="6 4"' if k in ('return','boundary') else ''
        marker=f' marker-end="url(#{k})"' if k!='boundary' else ''
        out.append(f'<path d="{path}" stroke="{color}" stroke-width="1.6" fill="none"{dash}{marker}/></a>')
        if k=='boundary':out.append(f'<path d="M{x2-5} {ay-5} l10 10 m0 -10 l-10 10" stroke="{color}" stroke-width="2"/>')
        for idx,line in enumerate(ann['details']):
            dy=ry+ann['detail_top']+20*idx
            out.append(f'<rect class="annotation-bg" x="{lx-2}" y="{dy-14}" width="{len(line)*8+4}" height="19" fill="{fill}"/><text class="muted" x="{lx}" y="{dy}" font-size="14">{escape(line)}</text>')
        for url,lines,offset_x,offset_y,bw in ann['sources']:
            sx=lx+offset_x;sy=ry+ann['source_top']+offset_y
            out.append(link(url,'TorchRec '+url.split('/torchrec/')[-1],'source-link'))
            out.append(f'<rect class="annotation-bg source-bg" x="{sx-2}" y="{sy-14}" width="{bw}" height="{19*len(lines)+3}" rx="3" fill="{fill}"/>')
            for idx,line in enumerate(lines):
                out.append(f'<text x="{sx}" y="{sy+19*idx}" font-size="13">{escape(line)}</text>')
            out.append('</a>')
        out.append('</g></g>')
    out.append('</g>')
    out.append(f'<line x1="48" y1="{y+18}" x2="1552" y2="{y+18}" stroke="var(--rule)"/>')
    for idx,note in enumerate(notes):
        out.append(f'<text class="muted" x="48" y="{y+45+idx*23}" font-size="14">{escape(note)}</text>')
    out.append(f'<text class="muted" x="48" y="{height-27}" font-size="12.5">TorchRec {REV[:12]} / Logical scopes, not measured durations. Request wait consumes a handle; stream dependencies order GPU work.</text></svg>')
    return '\n'.join(out)+'\n'


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for diagram in DATA['diagrams']:
        (OUT/(diagram['slug']+'.svg')).write_text(render(diagram),encoding='utf-8')
    print(f'Rendered {len(DATA["diagrams"])} diagrams; {sum(sum("a" in r for r in d["rows"]) for d in DATA["diagrams"])} linked messages.')
