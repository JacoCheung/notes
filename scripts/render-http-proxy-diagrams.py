#!/usr/bin/env python3
"""Render the proxy article's source-linked sequence and protocol-stack diagrams."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'assets/http-proxy-macos-ssh-socks'
HTTP = 'https://www.rfc-editor.org/rfc/rfc9112.html#section-3.2.2'
CONNECT = 'https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6'
SOCKS = 'https://www.rfc-editor.org/rfc/rfc1928.html#section-4'
SSH = 'https://www.rfc-editor.org/rfc/rfc4254.html#section-7.2'
TLS = 'https://www.rfc-editor.org/rfc/rfc8446.html#section-2'
COLORS = {'tcp': '#2563eb', 'control': '#7540b8', 'tls': '#087f68', 'ssh': '#a45b07'}
VPN = 'https://www.wireguard.com/protocol/'
COLORS['vpn'] = '#a45b07'


def render(name, title, actors, height, bars, messages, bands=(), notes=(), legend=None):
    xs = [120 + i * 840 / (len(actors) - 1) for i in range(len(actors))]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" viewBox="0 0 1080 {height}" role="img" aria-labelledby="title desc">',
           f'<title id="title">{escape(title)}</title>',
           '<desc id="desc">Time runs downward. Narrow activation bars show handling or relay intervals, not CPU utilization. Each message links to its protocol specification. TCP connections and logical TLS endpoints are labeled separately.</desc>',
           '<defs>']
    for key, color in COLORS.items():
        svg.append(f'<marker id="{key}" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 Z" fill="{color}"/></marker>')
    svg += ['</defs>', '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#253449} .message{font-size:17px} a:hover text{text-decoration:underline} a:focus{outline:2px solid #2563eb}</style>',
            f'<rect width="1080" height="{height}" rx="12" fill="#fff"/>',
            f'<text x="30" y="36" font-size="23" font-weight="700">{escape(title)}</text>',
            '<text x="30" y="62" font-size="14" fill="#64748b">Time ↓ · bars = handling / relay intervals · click messages for protocol references ↗</text>']
    for y, h, color in bands:
        svg.append(f'<rect x="24" y="{y}" width="1032" height="{h}" rx="8" fill="{color}"/>')
    for x, (label, detail) in zip(xs, actors):
        svg += [f'<line x1="{x}" x2="{x}" y1="140" y2="{height-65}" stroke="#a8b5c6" stroke-dasharray="5 6"/>',
                f'<rect x="{x-104}" y="85" width="208" height="55" rx="7" fill="#f1f5f9" stroke="#94a3b8"/>',
                f'<text x="{x}" y="108" text-anchor="middle" font-size="18" font-weight="700">{escape(label)}</text>',
                f'<text x="{x}" y="128" text-anchor="middle" font-size="14">{escape(detail)}</text>']
    for actor, y, end, kind in bars:
        svg.append(f'<rect x="{xs[actor]-7}" y="{y}" width="14" height="{end-y}" fill="#fff" stroke="{COLORS[kind]}" stroke-width="1.6"/>')
    for src, dst, y, label, kind, url, dashed in messages:
        x1, x2 = xs[src], xs[dst]
        color = COLORS[kind]
        svg.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener"><title>{escape(label.replace(chr(10), " "))} · protocol reference</title>')
        lines = label.split('\n')
        if src == dst:
            svg.append(f'<path d="M{x1+7},{y} h40 v22 h-40" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#{kind})"/>')
            tx, anchor = x1+58, 'start'
        else:
            direction = 1 if x2 > x1 else -1
            dash = ' stroke-dasharray="6 4"' if dashed else ''
            svg.append(f'<line x1="{x1+direction*7}" y1="{y}" x2="{x2-direction*8}" y2="{y}" stroke="{color}" stroke-width="2"{dash} marker-end="url(#{kind})"/>')
            tx = (x1+x2)/2 if abs(src-dst) == 1 else (xs[min(src, dst)] + xs[min(src, dst)+1])/2
            anchor = 'middle'
        for i, line in enumerate(lines):
            svg.append(f'<text class="message" x="{tx}" y="{y-12-(len(lines)-1-i)*21}" text-anchor="{anchor}" style="fill:{color}">{escape(line)}</text>')
        svg.append('</a>')
    for x, y, label in notes:
        for i, line in enumerate(label.split('\n')):
            svg.append(f'<text x="{x}" y="{y+i*22}" font-size="16" fill="#475569">{escape(line)}</text>')
    legend = legend or 'Blue: TCP setup · purple: proxy control / HTTP · green: origin TLS · amber: encrypted SSH channel'
    svg += [f'<text x="30" y="{height-22}" font-size="14">{escape(legend)}</text>', '</svg>']
    (OUT / (name + '.svg')).write_text('\n'.join(svg) + '\n')


def render_protocol_stack(lang):
    """Align TCP/IP layers; keep setup and relay phases distinct within each stack."""
    zh = lang == 'zh'
    title = 'HTTP、SOCKS5 与 SSH 的协议栈' if zh else 'HTTP, SOCKS5 and SSH in the protocol stack'
    subtitle = ('TCP/IP 四层模型 · HTTP/1.1、SOCKS5 CONNECT 与 SSH -L / -D' if zh else
                'TCP/IP model · HTTP/1.1, SOCKS5 CONNECT and SSH -L / -D')
    desc = ('三者都运行在 TCP 之上。应用层框内区分建立连接与数据传输两个阶段；SSH 加密 channel 承载应用字节，SOCKS5 的 L5 标注是功能类比。' if zh else
            'All three run above TCP. Application-layer boxes distinguish connection setup from data transfer. SSH channels carry application bytes. SOCKS5 at OSI L5 is a functional analogy.')
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="860" viewBox="0 0 1080 860" role="img" aria-labelledby="title desc">',
           f'<title id="title">{escape(title)}</title>', f'<desc id="desc">{escape(desc)}</desc>',
           '<style>text{font-family:Arial,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:#253449}a:hover text{text-decoration:underline}a:focus{outline:2px solid #2563eb}</style>',
           '<rect width="1080" height="860" rx="12" fill="#fff"/>']

    def text(x, y, lines, size=17, color='#253449', bold=False):
        for i, line in enumerate(lines.split('\n')):
            svg.append(f'<text x="{x}" y="{y + i * 24}" font-size="{size}" font-weight="{700 if bold else 400}" style="fill:{color}">{escape(line)}</text>')

    def box(x, y, w, h, fill, stroke):
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>')

    text(30, 38, title, 25, bold=True)
    text(30, 68, subtitle, 17, '#64748b')
    text(30, 122, 'TCP/IP 层次' if zh else 'TCP/IP layer', 18, bold=True)
    text(30, 202, '应用层' if zh else 'Application', 20, bold=True)
    text(30, 230, '≈ OSI L5–L7', 16, '#64748b')
    text(30, 274, '① 建立连接' if zh else '① Setup', 16)
    text(30, 378, '② 数据传输' if zh else '② Transfer', 16)
    text(30, 522, '传输层' if zh else 'Transport', 20, bold=True)
    text(30, 546, 'OSI L4', 16, '#64748b')
    text(30, 596, '网络层 · L3' if zh else 'Internet · L3', 18, bold=True)
    text(30, 658, '链路层 · L2' if zh else 'Link · L2', 18, bold=True)

    columns = [
        ('HTTP proxy', CONNECT, '#7540b8', '#f7f2fc',
         '客户端 → HTTP 代理' if zh else 'Client → HTTP proxy',
         '应用层协议 · OSI L7' if zh else 'Application protocol · OSI L7',
         'HTTP 代理请求' if zh else 'HTTP proxy request',
         'GET absolute-URI\n或 CONNECT host:port' if zh else 'GET absolute-URI\nor CONNECT host:port',
         'HTTP 请求 / 响应\n或 CONNECT 后的源站 TLS 字节' if zh else 'HTTP request / response\nor origin TLS after CONNECT'),
        ('SOCKS5', SOCKS, '#7540b8', '#f7f2fc',
         '客户端 → SOCKS 代理' if zh else 'Client → SOCKS proxy',
         'TCP/IP 应用层 · OSI L5*' if zh else 'TCP/IP application · OSI L5*',
         'SOCKS5 握手' if zh else 'SOCKS5 handshake',
         '认证方法协商\nCONNECT 目标地址与端口' if zh else 'Method negotiation\nCONNECT target host:port',
         '转发应用字节流\n可承载源站 TLS 字节' if zh else 'Relayed application bytes\ncan carry origin TLS bytes'),
        ('SSH tunnel', SSH, '#a45b07', '#fff5e8',
         'SSH 客户端 → sshd' if zh else 'SSH client → sshd',
         '应用层协议 · OSI L7' if zh else 'Application protocol · OSI L7',
         'SSH 连接与 channel' if zh else 'SSH connection and channel',
         '密钥交换 / 认证\n打开 direct-tcpip channel' if zh else 'Key exchange / authentication\nOpen a direct-tcpip channel',
         'SSH 加密 channel data\n内部可承载源站 TLS 字节' if zh else 'Encrypted SSH channel data\ncan contain origin TLS bytes'),
    ]
    for x, (name, url, color, fill, peer, layer, setup, handshake, payload) in zip([186, 482, 778], columns):
        text(x + 12, 122, peer, 17, bold=True)
        box(x, 168, 272, 300, fill, color)
        svg.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">')
        text(x + 16, 202, name + ' ↗', 23, color, bold=True)
        svg.append('</a>')
        text(x + 16, 230, layer, 16, color)
        text(x + 16, 274, setup, 17, bold=True)
        text(x + 16, 302, handshake, 16)
        svg.append(f'<line x1="{x+16}" x2="{x+256}" y1="350" y2="350" stroke="{color}" opacity=".35"/>')
        text(x + 16, 380, payload, 16)
        box(x, 492, 272, 66, '#eff6ff', '#9bbcf5')
        text(x + 16, 521, 'TCP', 21, '#2563eb', bold=True)
        text(x + 16, 546, peer.replace('→', '↔'), 16, '#2563eb')
        box(x, 568, 272, 50, '#f1f5f9', '#cbd5e1')
        text(x + 16, 600, 'IP', 21, bold=True)
        box(x, 628, 272, 50, '#f1f5f9', '#cbd5e1')
        text(x + 16, 660, 'Ethernet / Wi-Fi', 19)
    notes = ([
        '① → ② 是时间顺序：CONNECT / SOCKS5 握手头不会附加在后续每段应用数据上。',
        '* SOCKS5 的 L5 是功能类比；RFC 1928 将其描述为应用层与传输层之间的 shim。',
        'ssh -D 的 SOCKS 握手在本地 SSH 客户端终止；到 sshd 的链路承载 SSH channel。',
        'SSH channel 转发应用字节，不包含应用连接的完整 TCP / IP 包。',
    ] if zh else [
        '① → ② is a phase change: CONNECT / SOCKS5 setup headers do not wrap each later chunk of data.',
        '* OSI L5 is a functional analogy; RFC 1928 describes a shim between application and transport.',
        'With ssh -D, SOCKS terminates at the local SSH client; the remote hop carries SSH channels.',
        'SSH channel data carries application bytes, not the application connection’s complete TCP / IP packets.',
    ])
    for i, note in enumerate(notes):
        text(30, 719 + i * 28, note, 16, '#475569')
    for x, label, url in [(30, 'HTTP CONNECT ↗', CONNECT), (235, 'SOCKS5 ↗', SOCKS),
                           (382, 'SSH channels ↗', SSH), (582, 'SSH encryption ↗', 'https://www.rfc-editor.org/rfc/rfc4253.html#section-6')]:
        svg.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">')
        text(x, 839, label, 15, '#2563eb')
        svg.append('</a>')
    svg.append('</svg>')
    (OUT / f'protocol-stack-{lang}.svg').write_text('\n'.join(svg) + '\n')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ('zh', 'en'):
        render_protocol_stack(lang)
    render('http-forward', 'HTTP forward proxy: two separate TCP connections',
           [('Application', 'Mac · HTTP client'), ('HTTP proxy', 'proxy.example:18888'), ('Origin', 'example.com:80')], 760,
           [(0, 166, 660, 'tcp'), (1, 180, 660, 'control'), (2, 405, 595, 'tcp')], [
               (0, 1, 185, 'TCP connection A → proxy', 'tcp', HTTP, False),
               (0, 1, 265, 'GET http://example.com/docs HTTP/1.1\nHost: example.com', 'control', HTTP, False),
               (1, 1, 340, 'Resolve example.com', 'control', HTTP, False),
               (1, 2, 410, 'TCP connection B → origin', 'tcp', HTTP, False),
               (1, 2, 485, 'GET /docs HTTP/1.1\nHost: example.com', 'control', HTTP, False),
               (2, 1, 560, 'HTTP response', 'control', HTTP, True),
               (1, 0, 635, 'HTTP response', 'control', HTTP, True),
           ], bands=[(215, 452, '#f7f2fc')], notes=[(30, 700, 'The proxy parses HTTP. TCP A and TCP B have independent sequence numbers and flow control.')])
    render('https-connect', 'HTTPS through an HTTP proxy: CONNECT, then origin TLS',
           [('Application', 'TLS client'), ('HTTP proxy', 'TCP relay after CONNECT'), ('Origin', 'example.com:443 · TLS server')], 900,
           [(0, 166, 798, 'tcp'), (1, 180, 798, 'control'), (2, 365, 798, 'tcp')], [
               (0, 1, 185, 'TCP connection A → proxy', 'tcp', CONNECT, False),
               (0, 1, 265, 'CONNECT example.com:443 HTTP/1.1\nHost: example.com:443', 'control', CONNECT, False),
               (1, 1, 325, 'Resolve example.com', 'control', CONNECT, False),
               (1, 2, 375, 'TCP connection B → origin:443', 'tcp', CONNECT, False),
               (1, 0, 450, 'HTTP/1.1 200 Connection established', 'control', CONNECT, True),
               (0, 1, 560, 'TLS handshake bytes', 'tls', TLS, False),
               (1, 2, 620, 'Relay TLS handshake bytes', 'tls', CONNECT, False),
               (2, 0, 700, 'TLS handshake completes (logical)\nclient ↔ origin; proxy relays both ways', 'tls', TLS, True),
               (0, 2, 775, 'HTTPS inside origin TLS (logical)\ncarried over TCP A + TCP B', 'tls', CONNECT, True),
           ], bands=[(215, 261, '#f7f2fc'), (496, 307, '#ebf8f2')],
           notes=[(30, 836, 'Green end-to-end arrows show TLS endpoints, not a direct TCP connection or a third TCP leg.')])
    render('ssh-local-forward', 'ssh -L: fixed destination, original application bytes',
           [('Application', 'Mac · unmodified protocol'), ('SSH client', 'Mac · listens on :18080'), ('sshd', 'VM · encrypted SSH peer'), ('HTTP service', 'VM · 127.0.0.1:8000')], 850,
           [(0, 190, 744, 'tcp'), (1, 180, 744, 'ssh'), (2, 180, 744, 'ssh'), (3, 410, 744, 'tcp')], [
               (1, 2, 195, 'SSH connection already established\nTCP + encryption + authentication', 'ssh', SSH, True),
               (0, 1, 285, 'TCP → 127.0.0.1:18080', 'tcp', SSH, False),
               (1, 2, 350, 'Open direct-tcpip channel\nfixed target: 127.0.0.1:8000', 'ssh', SSH, False),
               (2, 3, 425, 'TCP → 127.0.0.1:8000\non the VM', 'tcp', SSH, False),
               (0, 1, 510, 'GET / HTTP/1.1\noriginal application bytes', 'control', SSH, False),
               (1, 2, 590, 'SSH channel data\nencrypted between SSH peers', 'ssh', SSH, False),
               (2, 3, 670, 'GET / HTTP/1.1\nbytes restored by sshd', 'control', SSH, False),
               (3, 0, 740, 'Response relayed back\nthrough the same three legs', 'control', SSH, True),
           ], bands=[(548, 60, '#fff5e8')],
           notes=[(30, 790, 'No proxy handshake at :18080. The command selects the destination before the application connects.')])
    render('ssh-socks', 'ssh -D: a local SOCKS server plus encrypted SSH forwarding',
           [('Application', 'Mac · SOCKS5 client'), ('SSH client', 'Mac · SOCKS at :1080'), ('sshd', 'VM · opens destination'), ('Origin', 'example.com:443')], 1100,
           [(0, 190, 990, 'tcp'), (1, 180, 990, 'ssh'), (2, 180, 990, 'ssh'), (3, 615, 990, 'tcp')], [
               (1, 2, 195, 'SSH connection already established\nTCP + encryption + authentication', 'ssh', SSH, True),
               (0, 1, 280, 'TCP → 127.0.0.1:1080', 'tcp', SOCKS, False),
               (0, 1, 350, 'SOCKS5 method negotiation', 'control', SOCKS, False),
               (1, 0, 415, 'Method selected', 'control', SOCKS, True),
               (0, 1, 485, 'SOCKS5 CONNECT\ndomain: example.com, port: 443', 'control', SOCKS, False),
               (1, 2, 555, 'Open direct-tcpip channel\nexample.com:443', 'ssh', SSH, False),
               (2, 3, 630, 'Resolve target on VM\nTCP → example.com:443', 'tcp', SSH, False),
               (1, 0, 705, 'SOCKS5 success reply', 'control', SOCKS, True),
               (0, 1, 785, 'Origin TLS bytes', 'tls', TLS, False),
               (1, 2, 860, 'Origin TLS bytes inside\nencrypted SSH channel data', 'ssh', SSH, False),
               (2, 3, 930, 'Origin TLS bytes', 'tls', TLS, False),
               (3, 0, 990, 'Origin TLS endpoints (logical)\napplication ↔ origin', 'tls', TLS, True),
           ], bands=[(308, 193, '#f7f2fc'), (743, 265, '#ebf8f2'), (817, 65, '#fff5e8')],
           notes=[(30, 1044, 'socks5h sends the hostname to the local SSH client. The VM needs sshd, not a separate SOCKS daemon.')])
    render('vpn-packets', 'Packet VPN (L3): the inner TCP connection survives the tunnel',
           [('Client TCP/IP', 'connect(origin_ip, 443)'), ('VPN interface', 'L3 packets selected by policy'), ('VPN gateway', 'decapsulation / routing / NAT'), ('Origin TCP/IP', 'TLS server on port 443')], 1020,
           [(0, 166, 917, 'tcp'), (1, 180, 917, 'vpn'), (2, 260, 917, 'vpn'), (3, 335, 917, 'tcp')], [
               (0, 1, 195, 'Inner IP / TCP SYN\ndestination = origin:443', 'tcp', VPN, False),
               (1, 2, 275, 'Encrypt whole inner IP packet\nouter UDP → VPN gateway', 'vpn', VPN, False),
               (2, 3, 355, 'Route inner TCP SYN\noptional NAT on source', 'tcp', VPN, False),
               (3, 2, 435, 'TCP SYN-ACK response', 'tcp', VPN, True),
               (2, 1, 515, 'Encrypt return IP packet\nouter UDP → VPN client', 'vpn', VPN, True),
               (1, 0, 595, 'Restore inner IP / SYN-ACK', 'tcp', VPN, True),
               (0, 3, 685, 'ACK follows tunnel path\ninner TCP established', 'tcp', VPN, True),
               (0, 1, 760, 'IP / TCP / origin TLS', 'tls', TLS, False),
               (1, 2, 835, 'Whole IP packet encrypted\ninside VPN transport', 'vpn', VPN, False),
               (2, 3, 910, 'IP / TCP / origin TLS', 'tls', TLS, False),
           ], bands=[(228, 62, '#fff5e8'), (468, 62, '#fff5e8'), (785, 66, '#fff5e8')],
           notes=[(30, 958, 'Routing / NAT gateway: forwards packets; it does not open a second application TCP connection.')],
           legend='Blue: inner TCP establishment · amber: encrypted VPN packets · green: origin TLS carried inside TCP')


if __name__ == '__main__':
    main()
