#!/usr/bin/env python3
"""Build the bilingual URL and DNS article, and its diagrams."""
from html import escape
from pathlib import Path
import json
import re

from post_series import render_series_nav

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/networking-basics/url-domain-dns'
REFS = json.loads((ASSETS / 'sources.json').read_text())['refs']


def link(key, label):
    return f'<a href="{escape(REFS[key]["url"], quote=True)}" target="_blank" rel="noopener">{label}</a>'


def text(x, y, value, anchor='middle', cls=''):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{escape(value)}</text>'


def svg_start(name, height, title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" width="1000" height="{height}" role="img" aria-labelledby="{name}-title"><title id="{name}-title">{escape(title)}</title>
<defs><marker id="{name}-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" class="arrow-head"/></marker></defs>'''


def figure(name, title, drawing, caption, lang):
    actual, fit = ('原始尺寸', '适应宽度') if lang == 'zh' else ('Actual size', 'Fit width')
    return f'''<figure class="network-figure" data-size="fit" id="{name}">
<div class="diagram-toolbar"><strong>{title}</strong><button type="button" data-network-size aria-pressed="false" data-actual-label="{actual}" data-fit-label="{fit}">{actual}</button></div>
<div class="diagram-viewport" tabindex="0" role="region" aria-label="{title}">{drawing}</div>
<figcaption>{caption}</figcaption></figure>'''


def dns_sequence(lang):
    zh = lang == 'zh'
    name = f'dns-sequence-{lang}'
    title = 'DNS 查询：沿委派寻找答案' if zh else 'DNS lookup: follow the delegations'
    actors = [('客户端', 'stub / browser'), ('递归解析器', 'resolver'), ('根服务器', '.'), ('顶级域服务器', 'com.'), ('权威服务器', 'example.com.')]
    if not zh:
        actors = [('Client', 'stub / browser'), ('Recursive resolver', 'resolver'), ('Root server', '.'), ('TLD server', 'com.'), ('Authoritative server', 'example.com.')]
    labels = [
        ('① 查询 dev.example.com 的 A 记录', '① Query A for dev.example.com'),
        ('② 查找 com 的委派', '② Find the delegation for com'),
        ('③ 返回 com 的服务器线索', '③ Referral to com servers'),
        ('④ 查找 example.com 的委派', '④ Find the delegation for example.com'),
        ('⑤ 返回 example.com 的服务器线索', '⑤ Referral to example.com servers'),
        ('⑥ 查询 A dev.example.com', '⑥ Query A dev.example.com'),
        ('⑦ A = 203.0.113.10；TTL = 300', '⑦ A = 203.0.113.10; TTL = 300'),
        ('⑧ 缓存记录，返回地址', '⑧ Cache records; return the address'),
    ]
    pairs = [(0,1),(1,2),(2,1),(1,3),(3,1),(1,4),(4,1),(1,0)]
    xs = [100,300,500,700,900]
    out = svg_start(name, 638, title)
    for i, (title_, subtitle) in enumerate(actors):
        x = xs[i]
        out += f'<path class="lifeline" d="M{x} 76V612"/>'
        out += f'<rect class="actor" x="{x-90}" y="16" width="180" height="60" rx="4"/>'
        out += text(x, 41, title_, cls='actor-title') + text(x, 63, subtitle, cls='muted')
    for actor, first, last in [(0,0,7),(1,0,7),(2,1,2),(3,3,4),(4,5,6)]:
        out += f'<rect class="activation" x="{xs[actor]-5}" y="{120+first*66}" width="10" height="{(last-first)*66+20}" rx="1"/>'
    for i, ((a,b), pair) in enumerate(zip(pairs, labels)):
        y=130+i*66
        x1,x2=xs[a],xs[b]
        # Message labels extend rightwards from their left participant, within the canvas.
        lx=min(x1,x2)+15
        label=pair[0 if zh else 1]
        background=min(680, sum(15 if ord(c)>255 else 8 for c in label)+12)
        cls='edge reply' if i in (2,4,6,7) else 'edge'
        out += f'<a href="{REFS["dns"]["url"]}" target="_blank" rel="noopener"><title>RFC 1034 §5.3.3</title>'
        out += f'<path class="{cls}" d="M{x1+(5 if b>a else -5)} {y}H{x2+(-6 if b>a else 6)}" marker-end="url(#{name}-arrow)"/>'
        out += f'<rect class="message-paper" x="{lx-4}" y="{y-27}" width="{background}" height="22" rx="2"/>'
        out += text(lx,y-11,label,'start')+'</a>'
    out += '</svg>'
    caption = ('无相关缓存，example.com 区域直接管理 dev。实线为查询，虚线为应答；活动条标示请求处理范围。点击消息查看解析器规范。' if zh else
               'No relevant cache; the example.com zone manages dev directly. Solid: queries. Dashed: responses. Activation bars mark request-handling scopes. Click a message for the resolver specification.')
    return figure(name,title,out,caption,lang)


def mapping(lang):
    zh=lang=='zh'
    name=f'url-mapping-{lang}'
    title='名称解析与应用路由' if zh else 'Name resolution and application routing'
    out=svg_start(name,310,title)
    for y,url,sub in [(55,'https://dev.example.com/','Host: dev.example.com · /'),(195,'https://example.com/dev','Host: example.com · /dev')]:
        out+=f'<rect class="actor" x="16" y="{y}" width="320" height="70" rx="4"/>'
        out+=text(176,y+28,url,cls='mono')+text(176,y+51,sub,cls='muted')
    out+='<rect class="actor" x="422" y="55" width="230" height="210" rx="4"/>'
    out+=text(537,101,'Web server',cls='actor-title')+text(537,131,'203.0.113.10:443',cls='mono')
    out+=text(537,187,'Host + path',cls='actor-title')+text(537,219,'路由分派' if zh else 'Route dispatch',cls='muted')
    out+='<rect class="handler" x="738" y="122" width="246" height="80" rx="4"/>'
    out+=text(861,154,'development_page()',cls='mono')+text(861,181,'同一个页面' if zh else 'One shared page',cls='muted')
    for y in (90,230):
        out+=f'<path class="edge" d="M336 {y}H420" marker-end="url(#{name}-arrow)"/>'
    out+=text(378,155,'DNS',cls='muted')
    out+=f'<path class="edge" d="M652 162H736" marker-end="url(#{name}-arrow)"/>'
    out+=text(695,145,'HTTP',cls='muted')+'</svg>'
    caption=('两个名称可以指向同一 IP；服务器再把两个 Host / path 组合映射到同一函数。' if zh else
             'Two names can resolve to one IP. The server maps both Host / path pairs to the same function.')
    return figure(name,title,out,caption,lang)


def expand(lang):
    body=(ROOT/f'scripts/content/url-domain-dns.{lang}.html').read_text()
    body=re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]', lambda m:link(m[1],m[2]),body)
    code=(ASSETS/'route_demo.py').read_text().split('def development_page():',1)[1].split('\n\nclass Handler',1)[0].rstrip()
    body=body.replace('{{route-code}}','<pre data-language="python"><code>'+escape('def development_page():'+code)+'</code></pre>')
    body=body.replace('{{dns-sequence}}',dns_sequence(lang)).replace('{{mapping-diagram}}',mapping(lang))
    assert '{{' not in body and '[[' not in body
    return body


def main():
    meta=dict(title='URL、域名与 DNS',title_en='URLs, domains, and DNS',slug='url-domain-dns',date='2026-11-12',tags='URL, DNS, 域名, HTTP',tags_en='URL, DNS, Domains, HTTP',reading='12 分钟',reading_en='12 min',summary='两个看起来不同的网址，可能打开同一个页面。域名解析负责找到服务器的网络地址，服务器根据网址中的域名和路径选择内容，重定向则让浏览器改用另一个网址。',summary_en='Different web addresses can display the same page. Name resolution finds server addresses; servers use hostnames and paths to select content, while redirects send browsers to another address.',series='networking-basics',series_title='网络入门原理',series_title_en='Networking Fundamentals',series_order='6')
    metadata='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in meta.items())
    html=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/networking-basics/url-domain-dns/style.css?v=1">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/networking-basics/url-domain-dns/page.js?v=1" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>{render_series_nav(meta,ROOT/'posts')}</aside><main class="content url-article"><div class="lang-zh">{expand('zh')}</div><div class="lang-en">{expand('en')}</div></main></div></body></html>'''
    target=ROOT/'posts/url-domain-dns.html'
    target.write_text(html)
    print('Wrote',target)


if __name__=='__main__':
    main()
