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
COLORS = {'call':'#475569','return':'#64748b','comm':'#7c3aed','h2d':'#2563eb',
          'host':'#dc2626','wait':'#a16207','dep':'#087f68','boundary':'#b91c1c'}
FILLS = {'comm':'#f5f3ff','h2d':'#eff6ff','host':'#fef2f2','wait':'#fffbeb',
         'dep':'#ecfdf5','call':'#ffffff','return':'#ffffff'}
TAGS = {'h2d':('H','H2D · host metadata / batch → CUDA'),
        'host':('D','D2H / HOST SYNC · CPU needs CUDA values'),
        'comm':('A','ALLTOALL · collective launch'),
        'wait':('W','WAIT · consume request; not a blanket host barrier'),
        'dep':('S','STREAM DEPENDENCY · GPU ordering')}


def wrapped(text, limit):
    return textwrap.wrap(text,width=limit,break_long_words=False,break_on_hyphens=False) or ['']


def source_label(url):
    path,anchor=url.rsplit('#',1)
    return path.rsplit('/',1)[-1]+':'+anchor.replace('L','').replace('-','–')


def link(url,title,cls):
    return (f'<a class="{cls}" href="{escape(url,quote=True)}" xlink:href="{escape(url,quote=True)}" '
            f'target="_blank" rel="noopener noreferrer" tabindex="0" aria-label="{escape(title,quote=True)}">'
            f'<title>{escape(title)}</title>')


def wrap_to(text, width, unit):
    # Conservative Arial widths; long identifiers can wrap inside their link.
    return textwrap.wrap(text, width=max(12, int(width/unit)),
                         break_long_words=True, break_on_hyphens=False)


def annotation_layout(row, width):
    labels=wrap_to(row['label']+' ↗',width-10,8.2)
    details=wrap_to(row.get('detail',''),width-10,7.0)
    sources=[];sx=0;sy=0;line_height=0
    for url in dict.fromkeys(row['sources']):
        lines=wrap_to(source_label(url)+' ↗',width-12,7.1)
        bw=min(width,max(len(line)*7.1 for line in lines)+12)
        bh=15*len(lines)
        if sx and sx+bw>width:
            sx=0;sy+=line_height+7;line_height=0
        sources.append((url,lines,sx,sy,bw))
        sx+=bw+8;line_height=max(line_height,bh)
    label_bottom=25+18*(len(labels)-1)
    arrow=label_bottom+18
    detail_top=arrow+34
    source_top=(detail_top+16*(len(details)-1)+23) if details else arrow+34
    height=max(110,source_top+sy+line_height+14)
    return dict(labels=labels,details=details,sources=sources,arrow=arrow,
                detail_top=detail_top,source_top=source_top,height=height)


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
    windows=[];left=300
    for start,end in sorted(obstacles):
        if start>left:windows.append((left,start))
        left=max(left,end)
    if left<1546:windows.append((left,1546))
    return [(a,b) for a,b in windows if b-a>=125]


def render(d):
    width=1600;top=270;rows=d['rows'];actors=d['actors']
    plot_left=288;lane=(1560-plot_left)/len(actors)
    xs=[plot_left+lane*(i+.5) for i in range(len(actors))]
    layout=[];messages={};y=top;n=0
    for row in rows:
        k=row['kind']
        if k in ('note','phase'):
            if k=='phase' and len(row['label'])<32:
                lx,available=60,200
            else:
                # Between messages, only scopes continuing past the previous
                # message may intersect this strip.
                candidates=text_windows(d,xs,n+.5)
                lx,end=max(candidates,key=lambda pair:pair[1]-pair[0])
                available=end-lx-8
            lines=wrap_to(row['label'],available,7.8)
            h=max(46,26+18*len(lines))
            item=dict(row=row,y=y,height=h,x=lx,lines=lines)
        else:
            n+=1;a,b=row['a'],row['b']
            preferred=min(xs[a],xs[b])+28
            candidates=[]
            for left,right in text_windows(d,xs,n):
                ann=annotation_layout(row,right-left-8)
                # Prefer compact labels close to their message's left endpoint.
                score=ann['height']+abs(left-preferred)*.12
                candidates.append((score,left,ann))
            _,lx,ann=min(candidates,key=lambda item:item[0])
            tag_detail=row.get('tag_detail',TAGS[k][1].split(' · ',1)[-1]) if k in TAGS else ''
            tag_lines=wrap_to(tag_detail,151,6.7) if k in TAGS else []
            tag_height=47+16*len(tag_lines)+(48 if row.get('also_comm') else 0)
            h=max(ann['height'],tag_height+18)
            item=dict(row=row,y=y,height=h,x=lx,number=n,annotation=ann,tag_lines=tag_lines)
            messages[n]=item
        layout.append(item);y+=h
    notes=[line for note in d['notes'] for line in wrapped(note,174)]
    height=y+66+len(notes)*21;scopes=d['activations']
    for a,first,last,_ in scopes:
        assert 0<=a<len(actors) and first<=last and last in messages,(d['slug'],a,first,last)
    def arrow_y(number):
        item=messages[number]
        return item['y']+item['annotation']['arrow']
    description=d['subtitle']+' Solid bars: logical execution/access scopes; hollow dashed bars: unconsumed requests. Blue H2D, red D2H/host sync, purple AllToAll, amber request wait, green stream dependency. '
    description+=' '.join(r['label']+' '+r.get('detail','') for r in rows)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="group" aria-labelledby="title desc">',
         f'<title id="title">{escape(d["title"])}</title><desc id="desc">{escape(description)}</desc>',
         '<style>text{font-family:Arial,Helvetica,sans-serif}a{cursor:pointer}a:hover text,a:focus text{text-decoration:underline}.source-link text{text-decoration:underline;text-underline-offset:2px}.activation,.pending-request{pointer-events:none}.message-link:hover .message-bg,.message-link:focus .message-bg{stroke:#93c5fd;fill:#eff6ff}</style><defs>']
    for k,c in COLORS.items():
        out.append(f'<marker id="{k}" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="{c}"/></marker>')
    out+=['</defs><rect width="100%" height="100%" fill="#fff"/>',
          f'<text x="40" y="38" font-size="24" font-weight="700" fill="#0f172a">{escape(d["title"])}</text>',
          f'<text x="40" y="66" font-size="14" fill="#64748b">{escape(d["subtitle"])}</text>']
    for x,k,label in [(40,'h2d','H2D'),(255,'host','D2H / host sync'),(590,'comm','AllToAll'),(845,'wait','Request wait'),(1170,'dep','Stream dependency')]:
        out.append(f'<rect x="{x}" y="84" width="28" height="20" rx="3" fill="{FILLS[k]}" stroke="{COLORS[k]}"/><text x="{x+39}" y="99" font-size="14" fill="#334155">{label}</text>')
    out+=['<rect x="40" y="120" width="14" height="23" fill="#dbeafe" stroke="#2563eb"/><text x="66" y="137" font-size="13" fill="#475569">Activation / access scope; nested bars = self-calls</text>',
          '<rect x="530" y="120" width="12" height="23" fill="#faf5ff" stroke="#7c3aed" stroke-dasharray="4 3"/><text x="555" y="137" font-size="13" fill="#475569">Pending request, not GPU duration</text>',
          '<text x="1010" y="137" font-size="13" fill="#1d4ed8">Click messages or file:line links to open TorchRec ↗</text>']
    explanation=('Example activity IDs and sizes vary by execution; source links identify TorchRec callsites for backend work.' if d.get('trace')
                 else 'Host submission order and logical dependencies; bar lengths are not measured execution times.')
    out.append(f'<text x="40" y="164" font-size="12" fill="#64748b">{explanation}</text>')
    # Explicit SVG painter order: ALL structural backgrounds precede lifelines
    # and activations. The annotation gutter has no execution lifelines.
    out.append('<g class="background-layer">')
    for i in range(len(actors)):
        out.append(f'<rect x="{plot_left+lane*i}" y="182" width="{lane}" height="{y-182}" fill="{"#f8fafc" if i%2 else "#f1f5f9"}" fill-opacity=".55" stroke="#cbd5e1"/>')
    counters={k:0 for k in TAGS}
    for item in layout:
        row=item['row'];ry=item['y'];h=item['height'];k=row['kind']
        if k in TAGS:
            counters[k]+=1;item['tag']=row.get('tag',TAGS[k][0]+str(counters[k]))
            out.append(f'<rect class="highlight highlight-{k}" data-kind="{k}" x="48" y="{ry+3}" width="{width-96}" height="{h-7}" rx="6" fill="{FILLS[k]}" stroke="{COLORS[k]}" stroke-opacity=".45"/>')
        elif k in ('note','phase'):
            fill='#e2e8f0' if k=='phase' else '#f8fafc'
            out.append(f'<rect class="{k}-bg" x="48" y="{ry+2}" width="{width-96}" height="{h-4}" rx="4" fill="{fill}"/>')
        else:
            out.append(f'<line x1="48" y1="{ry+h-1}" x2="{width-48}" y2="{ry+h-1}" stroke="#e2e8f0"/>')
    out.append('</g><g class="lifeline-layer">')
    for x,actor in zip(xs,actors):
        out.append(f'<line class="lifeline" x1="{x}" y1="249" x2="{x}" y2="{y}" stroke="#94a3b8" stroke-dasharray="5 6"/>')
        out.append(f'<rect x="{x-lane/2+6}" y="189" width="{lane-12}" height="60" rx="5" fill="#f8fafc" stroke="#64748b"/>')
        name=actor['name'];parts=[name]
        if len(name)>25:
            words=re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z0-9_]*|[^A-Z]+',name)
            if len(words)>1:
                split=min(range(1,len(words)),key=lambda k:abs(len(''.join(words[:k]))-len(''.join(words[k:]))))
                parts=[''.join(words[:split]),''.join(words[split:])]
        for k,line in enumerate(parts):
            fs=min(14,(lane-22)/(max(len(line),1)*.61))
            out.append(f'<text x="{x}" y="{209+k*16 if len(parts)>1 else 216}" text-anchor="middle" font-size="{fs:.1f}" font-weight="700" fill="#0f172a">{escape(line)}</text>')
        fs=min(11.5,(lane-22)/(max(len(actor["type"]),1)*.55))
        out.append(f'<text x="{x}" y="239" text-anchor="middle" font-size="{fs:.1f}" fill="#64748b">{escape(actor["type"])}</text>')
    out.append('</g><g class="activation-layer">')
    for a,first,last,depth,label in d.get('pending',[]):
        sy=arrow_y(first);ey=arrow_y(last) if last else y-8
        out.append(f'<rect class="pending-request" x="{xs[a]+23+depth*15}" y="{sy}" width="10" height="{ey-sy}" fill="#faf5ff" stroke="#7c3aed" stroke-dasharray="4 4"><title>{escape(label)}; pending handle, not execution duration</title></rect>')
    for a,first,last,kind in scopes:
        sy=arrow_y(first)-8;ey=arrow_y(last)+24
        out.append(f'<rect class="activation" data-actor="{a}" data-start="{first}" data-end="{last}" x="{xs[a]-8}" y="{sy}" width="16" height="{ey-sy}" fill="#ffffff" stroke="#2563eb" stroke-width="1.5"><title>{escape(actors[a]["name"])}: scope {first}–{last}</title></rect>')
    for number,item in messages.items():
        row=item['row'];a,b=row['a'],row['b'];ay=arrow_y(number)
        if a==b and row['kind']!='boundary':
            out.append(f'<rect class="activation nested" x="{xs[a]}" y="{ay-5}" width="16" height="23" fill="#dbeafe" stroke="#2563eb"/>')
    out.append('</g><g class="message-layer">')
    for item in layout:
        row=item['row'];ry=item['y'];h=item['height'];k=row['kind'];lx=item['x']
        out.append(f'<g class="row-content" data-top="{ry}" data-bottom="{ry+h}">')
        if k in ('phase','note'):
            for idx,line in enumerate(item['lines']):
                out.append(f'<text x="{lx}" y="{ry+24+18*idx}" font-size="14" font-weight="{600 if k=="phase" else 400}" fill="#334155">{escape(line)}</text>')
            out.append('</g>');continue
        n=item['number'];ann=item['annotation'];a,b=row['a'],row['b'];color=COLORS[k];fill=FILLS.get(k,'#fff')
        if k in TAGS:
            out.append(f'<rect x="56" y="{ry+12}" width="34" height="21" rx="3" fill="{color}"/><text x="73" y="{ry+27}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">{item["tag"]}</text>')
            heading=row.get('tag_heading',TAGS[k][1].split(' · ',1)[0])
            out.append(f'<text x="99" y="{ry+27}" font-size="11.5" font-weight="700" fill="{color}">{escape(heading)}</text>')
            for idx,line in enumerate(item['tag_lines']):
                out.append(f'<text x="99" y="{ry+47+16*idx}" font-size="11.5" fill="{color}">{escape(line)}</text>')
            if row.get('also_comm'):
                cy=ry+53+16*len(item['tag_lines'])
                out.append(f'<rect class="highlight highlight-comm" data-kind="comm" x="58" y="{cy}" width="208" height="37" rx="3" fill="#f5f3ff" stroke="#7c3aed"/><text x="67" y="{cy+15}" font-size="11" font-weight="700" fill="#7c3aed">THEN ALLTOALL</text><text x="67" y="{cy+29}" font-size="11" fill="#7c3aed">lengths + ID payloads</text>')
        else:
            out.append(f'<text x="62" y="{ry+25}" font-size="12" fill="#94a3b8">{n:02}</text>')
        ay=arrow_y(n);direction=1 if b>=a else -1
        def edge(actor,sign):
            return xs[actor]+(8*sign if any(ac==actor and first<=n<=last for ac,first,last,_ in scopes) else 0)
        x1,x2=edge(a,direction),edge(b,-direction)
        out.append(f'<g class="message" data-step="{n}" data-kind="{k}">')
        out.append(link(row['sources'][0],row['label'],'message-link'))
        for idx,line in enumerate(ann['labels']):
            ty=ry+25+18*idx;tw=len(line)*8.2+4
            out.append(f'<rect class="annotation-bg message-bg" x="{lx-2}" y="{ty-14}" width="{tw}" height="18" rx="2" fill="{fill}"/><text x="{lx}" y="{ty}" font-size="13.5" font-weight="600" fill="{color}">{escape(line)}</text>')
        path=f'M{x1} {ay} H{xs[a]+42} V{ay+16} H{xs[a]+16}' if a==b else f'M{x1} {ay} H{x2}'
        dash=' stroke-dasharray="6 4"' if k in ('return','boundary') else ''
        marker=f' marker-end="url(#{k})"' if k!='boundary' else ''
        out.append(f'<path d="{path}" stroke="{color}" stroke-width="1.7" fill="none"{dash}{marker}/></a>')
        if k=='boundary':out.append(f'<path d="M{x2-5} {ay-5} l10 10 m0 -10 l-10 10" stroke="{color}" stroke-width="2"/>')
        for idx,line in enumerate(ann['details']):
            dy=ry+ann['detail_top']+16*idx
            out.append(f'<rect class="annotation-bg" x="{lx-2}" y="{dy-12}" width="{len(line)*7+4}" height="15" fill="{fill}"/><text x="{lx}" y="{dy}" font-size="12" fill="#475569">{escape(line)}</text>')
        for url,lines,offset_x,offset_y,bw in ann['sources']:
            sx=lx+offset_x;sy=ry+ann['source_top']+offset_y
            out.append(link(url,'TorchRec '+url.split('/torchrec/')[-1],'source-link'))
            out.append(f'<rect class="annotation-bg source-bg" x="{sx-2}" y="{sy-12}" width="{bw}" height="{15*len(lines)+2}" rx="2" fill="{fill}"/>')
            for idx,line in enumerate(lines):
                out.append(f'<text x="{sx}" y="{sy+15*idx}" font-size="11.5" fill="#1d4ed8">{escape(line)}</text>')
            out.append('</a>')
        out.append('</g></g>')
    out.append('</g>')
    for idx,note in enumerate(notes):
        out.append(f'<text x="40" y="{y+27+idx*21}" font-size="12" fill="#475569">{escape(note)}</text>')
    out.append(f'<text x="40" y="{height-15}" font-size="11" fill="#64748b">TorchRec {REV[:12]} · logical scopes, not measured durations · blue H2D / red host sync / purple AllToAll</text></svg>')
    return '\n'.join(out)+'\n'


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for diagram in DATA['diagrams']:
        (OUT/(diagram['slug']+'.svg')).write_text(render(diagram),encoding='utf-8')
    print(f'Rendered {len(DATA["diagrams"])} diagrams; {sum(sum("a" in r for r in d["rows"]) for d in DATA["diagrams"])} linked messages.')
