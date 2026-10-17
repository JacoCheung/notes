#!/usr/bin/env python3
"""Render diagrams for the Networking Fundamentals series."""
from html import escape
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/networking-basics'
spec = importlib.util.spec_from_file_location('proxy_diagrams', ROOT / 'scripts/render-http-proxy-diagrams.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.OUT = OUT


def canvas(title, height, desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" viewBox="0 0 1080 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
            '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#253449}a:hover text{text-decoration:underline}a:focus{outline:2px solid #2563eb}</style>',
            f'<rect width="1080" height="{height}" rx="12" fill="#fff"/>',
            f'<text x="30" y="40" font-size="24" font-weight="700">{escape(title)}</text>']


def text(svg, x, y, lines, size=17, color='#253449', bold=False):
    for i, line in enumerate(lines.split('\n')):
        svg.append(f'<text x="{x}" y="{y+i*25}" font-size="{size}" font-weight="{700 if bold else 400}" style="fill:{color}">{escape(line)}</text>')


def box(svg, x, y, w, h, fill='#f1f5f9', stroke='#cbd5e1'):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>')


def link(svg, x, y, label, url):
    svg.append(f'<a href="{escape(url,quote=True)}" target="_blank" rel="noopener">')
    text(svg,x,y,label,15,'#2563eb')
    svg.append('</a>')


def save(name, svg):
    (OUT / f'{name}.svg').write_text('\n'.join(svg + ['</svg>'])+'\n')


def vpn_stack():
    svg=canvas('VPN encapsulation: an IP packet inside another IP path',800,
               'A virtual tunnel interface receives an inner IP packet. WireGuard encrypts it and sends outer UDP/IP through a physical interface. The gateway recovers and routes the inner packet.')
    text(svg,30,70,'Example: HTTPS over a layer-3 WireGuard VPN. Read each packet from outside to inside.',16,'#64748b')
    box(svg,30,105,480,255,'#eff6ff','#9bbcf5')
    text(svg,50,139,'Before VPN encapsulation',21,bold=True)
    text(svg,50,169,'utun / wg interface: inner IP packet',18,'#2563eb')
    for y,label in [(190,'Inner IP: tunnel client → origin'),(240,'TCP: client ↔ origin'),(290,'TLS → HTTP')]:
        box(svg,50,y,440,42,'#fff','#9bbcf5');text(svg,67,y+28,label,18)
    box(svg,550,105,500,400,'#fff5e8','#d6a86f')
    text(svg,570,139,'On the physical interface',21,bold=True)
    text(svg,570,169,'Outer transport: client → VPN peer',18,'#a45b07')
    for y,label in [(190,'Ethernet / Wi-Fi frame'),(240,'Outer IP: client → VPN gateway'),(290,'UDP: WireGuard endpoints')]:
        box(svg,570,y,460,42,'#fff','#d6a86f');text(svg,587,y+28,label,18)
    box(svg,570,345,460,140,'#ebf8f2','#7dbba4')
    text(svg,588,376,'WireGuard encrypted payload',19,'#087f68',True)
    text(svg,588,409,'Whole inner IP packet',18)
    text(svg,588,438,'Inner IP → TCP → TLS → HTTP',18)
    text(svg,50,399,'VPN encrypts the whole inner packet.',18,'#a45b07',True)
    text(svg,50,433,'The original TCP state stays with\nthe client and origin in this routed model.',17)
    box(svg,30,535,1020,180,'#f1f5f9','#cbd5e1')
    text(svg,50,570,'At the VPN gateway',21,bold=True)
    text(svg,50,605,'Remove outer encapsulation → recover inner IP → route to origin; apply NAT if configured.',18)
    text(svg,50,641,'The origin sees the routed packet, not the outer UDP / WireGuard wrapper.',18)
    text(svg,50,677,'A VPN interface name such as utun4 does not identify the outer VPN protocol.',17)
    link(svg,30,755,'WireGuard protocol ↗',base.VPN)
    link(svg,270,755,'WireGuard routing ↗','https://www.wireguard.com/#cryptokey-routing')
    link(svg,520,755,'Apple utun implementation ↗','https://github.com/apple-oss-distributions/xnu/blob/main/bsd/net/if_utun.c')
    save('vpn-stack',svg)


def route_cases():
    svg=canvas('Application proxy selection × IP routing',880,
               'Five viable path classes for a private application proxy P1 reachable only over VPN, a public system proxy P2, and a public origin O. This is a path model, not packet capture.')
    text(svg,30,73,'Scope: new external IPv4/TCP connections; no extra proxy chains or per-app routing rules.',16,'#64748b')
    box(svg,30,100,1020,90)
    text(svg,50,133,'1. The request implementation selects P₁, P₂ or DIRECT.',19,bold=True)
    text(svg,50,165,'2. The OS routes that socket destination. DIRECT can still use the VPN.',19)
    rows=[('A','Private proxy P₁','Mac → VPN → P₁ → proxy-side egress → origin','#fff5e8','#a45b07'),
          ('B','Public proxy P₂','Mac → ordinary network → P₂ → proxy-side egress → origin','#eff6ff','#2563eb'),
          ('C','Public proxy P₂','Mac → VPN → P₂ → proxy-side egress → origin','#fff5e8','#a45b07'),
          ('D','DIRECT','Mac → ordinary network → origin','#eff6ff','#2563eb'),
          ('E','DIRECT','Mac → VPN → origin','#fff5e8','#a45b07')]
    for i,(key,choice,path,fill,color) in enumerate(rows):
        y=210+i*92
        box(svg,30,y,1020,78,fill,color)
        text(svg,50,y+46,key,28,color,True)
        text(svg,105,y+30,choice,18,color,True)
        text(svg,105,y+59,path,19)
    box(svg,30,688,1020,117,'#fff1f2','#e5a2ac')
    text(svg,50,720,'P₁ over the ordinary network: unreachable under the stated premise.',18,'#a3293d',True)
    text(svg,50,753,'A fixed private proxy does not automatically fall back to the public system proxy.',17)
    text(svg,50,781,'DNS, IPv6, UDP, local connections and explicit fallback lists need separate analysis.',17)
    link(svg,30,847,'Electron proxy modes ↗','https://www.electronjs.org/docs/latest/api/structures/proxy-config')
    link(svg,310,847,'Chromium proxy selection ↗','https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md')
    save('routing-cases',svg)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    vpn_stack()
    route_cases()
    base.render('proxy-over-vpn','Private HTTP proxy over VPN: two application TCP legs',
                [('Client','Mac · VPN + proxy config'),('VPN gateway','packet routing / decapsulation'),('Private proxy','10.77.0.10:18888'),('Origin','example.com:443')],940,
                [(0,170,835,'tcp'),(1,180,835,'vpn'),(2,255,835,'control'),(3,510,835,'tcp')],[
                    (0,1,195,'Outer WireGuard packet\ncontains inner TCP SYN to proxy','vpn',base.VPN,False),
                    (1,2,275,'Route inner TCP SYN\nto private proxy','tcp',base.VPN,False),
                    (2,0,355,'TCP A established (logical)\nclient ↔ proxy, via VPN','tcp',base.CONNECT,True),
                    (0,2,440,'CONNECT example.com:443\ncarried over TCP A + VPN','control',base.CONNECT,False),
                    (2,3,530,'TCP B → origin:443\nproxy-side route and egress','tcp',base.CONNECT,False),
                    (2,0,620,'200 Connection established\nreturned over TCP A + VPN','control',base.CONNECT,True),
                    (0,3,720,'Client-origin TLS (logical)\nproxy relays TCP A ↔ TCP B','tls',base.TLS,True),
                    (2,3,810,'Relay origin TLS bytes\non the separate TCP B','tls',base.CONNECT,False)
                ],bands=[(160,65,'#fff5e8'),(390,75,'#f7f2fc'),(670,170,'#ebf8f2')],
                notes=[(30,872,'VPN gateway routes packets; the proxy opens TCP B. Long arrows denote logical endpoints.')],
                legend='Blue: TCP setup · purple: CONNECT control · green: origin TLS · amber: encrypted VPN transport')
    base.render('ssh-remote-forward','ssh -R: remote listener, client-side target connection',
                [('Visitor','curl on VM'),('sshd','VM · listens on :18080'),('SSH client','Mac · initiates SSH'),('HTTP service','Mac · 127.0.0.1:8000')],1040,
                [(0,365,930,'tcp'),(1,170,930,'ssh'),(2,170,930,'ssh'),(3,545,930,'tcp')],[
                    (2,1,195,'SSH connection\ninitiated by the Mac','ssh',base.SSH,False),
                    (2,1,290,'tcpip-forward request\nVM loopback listener :18080','ssh','https://www.rfc-editor.org/rfc/rfc4254.html#section-7.1',False),
                    (0,1,385,'TCP A → VM :18080','tcp',base.SSH,False),
                    (1,2,470,'Open forwarded-tcpip channel\non the existing SSH connection','ssh',base.SSH,False),
                    (2,3,560,'TCP C → Mac :8000\nopened by SSH client','tcp',base.SSH,False),
                    (0,1,645,'HTTP request bytes','control',base.SSH,False),
                    (1,2,730,'Encrypted SSH channel data\nservice traffic toward the Mac','ssh',base.SSH,False),
                    (2,3,815,'Original HTTP request bytes','control',base.SSH,False),
                    (3,0,920,'Response relayed back (logical)\nthrough the same three TCP legs','control',base.SSH,True)
                ],bands=[(680,75,'#fff5e8')],
                notes=[(30,980,'SSH TCP B was initiated Mac → VM; the forwarded request uses it in the opposite direction.')])


if __name__=='__main__':
    main()
