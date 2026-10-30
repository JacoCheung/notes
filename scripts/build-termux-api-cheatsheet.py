#!/usr/bin/env python3
"""Build a compact, single-page reference for the v0.60.0 Termux:API scripts."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = '9e7f1531e1aa4a9c1e261a2dbde4de93653c366e'
SOURCE = f'https://github.com/termux/termux-api-package/blob/{REV}/scripts/'
GROUPS = [
    ('device', '设备与显示', 'Device and display'),
    ('files', '剪贴板与文件', 'Clipboard and files'),
    ('ui', '通知与交互', 'Notifications and UI'),
    ('media', '相机与音频', 'Camera and audio'),
    ('network', '网络与定位', 'Network and location'),
    ('phone', '联系人与电话', 'Contacts and telephony'),
    ('hardware', '传感器与外设', 'Sensors and peripherals'),
    ('saf', 'SAF 文档访问', 'SAF document access'),
    ('automation', '任务、服务与密钥', 'Jobs, services, and keys'),
]

# group, suffix, purpose zh/en, copyable example, compact note zh/en
COMMANDS = [
    ('device', 'battery-status', '读取电量与充电状态', 'Read battery and charging status',
     'termux-battery-status',
     'JSON：电量、充电状态', 'JSON: battery level and charging state'),
    ('device', 'brightness', '设置屏幕亮度', 'Set display brightness',
     'termux-brightness 128\ntermux-brightness auto',
     '0–255 / auto；需“修改系统设置”授权', '0–255 / auto; Modify system settings access'),
    ('device', 'torch', '开关手电筒', 'Toggle the flashlight',
     'termux-torch on\ntermux-torch off',
     'on / off；相机权限与闪光灯硬件', 'on / off; camera permission and flash hardware'),
    ('device', 'vibrate', '控制振动', 'Vibrate the device',
     'termux-vibrate -d 200',
     '-d 毫秒；-f 忽略静音模式', '-d milliseconds; -f overrides silent mode'),
    ('device', 'volume', '查询或调整音量', 'Inspect or change volume',
     'termux-volume\ntermux-volume music 5',
     '先查 max_volume；music / ring / alarm / call 等', 'Check max_volume; music / ring / alarm / call, etc.'),
    ('device', 'audio-info', '查询音频设备状态', 'Inspect audio state',
     'termux-audio-info',
     '', ''),
    ('device', 'wallpaper', '设置桌面或锁屏壁纸', 'Set home or lock-screen wallpaper',
     'termux-wallpaper -f "$HOME/wallpaper.jpg"',
     '-f 文件 / -u URL；-l 锁屏（Android 7+）', '-f file / -u URL; -l lock screen (Android 7+)'),
    ('files', 'clipboard-get', '读取剪贴板文本', 'Read clipboard text',
     'termux-clipboard-get',
     '受 Android 后台访问限制', 'Subject to Android background-access limits'),
    ('files', 'clipboard-set', '写入剪贴板文本', 'Write clipboard text',
     'printf %s "hello from Termux" | termux-clipboard-set',
     '文本参数或 stdin', 'Text arguments or stdin'),
    ('files', 'share', '调用 Android 分享或查看', 'Open Android share or view UI',
     'termux-share -a send "$HOME/report.txt"',
     '-a send / view；-c MIME；支持 stdin', '-a send / view; -c MIME; accepts stdin'),
    ('files', 'download', '交给系统下载管理器', 'Use the system download manager',
     'termux-download -t "Example page" https://example.com/',
     '-p 目标路径需系统下载管理器可写', '-p destination must be writable by DownloadManager'),
    ('files', 'storage-get', '通过文件选择器导入文件', 'Import a file through the picker',
     'termux-storage-get "$HOME/imported.txt"',
     '系统选择器 → 本地文件', 'System picker → local file'),
    ('ui', 'toast', '显示短提示', 'Display a toast',
     'termux-toast -s -g bottom "任务完成"',
     '-s 短提示；-g top / middle / bottom', '-s short; -g top / middle / bottom'),
    ('ui', 'dialog', '用系统对话框取得输入', 'Collect input with a dialog',
     'termux-dialog text -t "备注" -i "输入内容"',
     '-l 列出控件；text / confirm / date 等', '-l lists widgets; text / confirm / date, etc.'),
    ('ui', 'notification', '发布或更新通知', 'Post or update a notification',
     'termux-notification --id 42 --title "任务完成" --content "结果已保存"',
     '相同 --id 更新；--action 点击动作', 'Same --id updates; --action handles taps'),
    ('ui', 'notification-list', '列出可读取的系统通知', 'List accessible system notifications',
     'termux-notification-list',
     '需单独开启“通知访问”', 'Requires notification-listener access'),
    ('ui', 'notification-remove', '移除指定通知', 'Remove a notification by ID',
     'termux-notification-remove 42',
     '使用发布通知时的 --id', 'Use the ID supplied when posting'),
    ('ui', 'notification-channel', '管理通知渠道', 'Manage notification channels',
     'termux-notification-channel tasks "任务通知"',
     'Android 8+；--channel tasks 发布；-d tasks 删除', 'Android 8+; post with --channel tasks; delete with -d tasks'),
    ('media', 'camera-info', '列出相机信息', 'List camera information',
     'termux-camera-info',
     '相机权限；返回可用 camera ID', 'Camera permission; lists available camera IDs'),
    ('media', 'camera-photo', '拍照并保存', 'Capture a photo',
     'termux-camera-photo -c 0 "$HOME/photo.jpg"',
     '-c 使用 camera-info 的 ID；需相机权限', '-c uses an ID from camera-info; camera permission'),
    ('media', 'media-player', '播放本地媒体', 'Play local media',
     'termux-media-player play "$HOME/music.mp3"',
     'info / pause / stop；play 无路径恢复', 'info / pause / stop; play without a path resumes'),
    ('media', 'media-scan', '刷新系统媒体索引', 'Refresh the media index',
     'termux-media-scan -r "$HOME/storage/shared/Pictures"',
     '-r 递归；-v 详细输出', '-r recursive; -v verbose'),
    ('media', 'microphone-record', '录制麦克风音频', 'Record microphone audio',
     'termux-microphone-record -f "$HOME/clip.m4a" -l 10 -e aac',
     '-l 秒（0 不限）；-i 状态；-q 停止；录音权限', '-l seconds (0 unlimited); -i status; -q stop; microphone access'),
    ('media', 'speech-to-text', '语音识别', 'Recognize speech',
     'termux-speech-to-text',
     '需语音识别服务与录音权限', 'Requires a recognition service and microphone access'),
    ('media', 'tts-engines', '列出语音合成引擎', 'List text-to-speech engines',
     'termux-tts-engines',
     '引擎名用于 tts-speak -e', 'Engine names for tts-speak -e'),
    ('media', 'tts-speak', '朗读文本', 'Speak text',
     'termux-tts-speak -l zh -n CN "任务已经完成"',
     '-r 语速；-p 音调；支持 stdin', '-r rate; -p pitch; accepts stdin'),
    ('network', 'wifi-connectioninfo', '当前 Wi-Fi 连接信息', 'Inspect the current Wi-Fi connection',
     'termux-wifi-connectioninfo',
     'SSID 等字段受系统权限限制', 'SSID and other fields depend on system permissions'),
    ('network', 'wifi-scaninfo', '获取 Wi-Fi 扫描结果', 'Read Wi-Fi scan results',
     'termux-wifi-scaninfo',
     '定位授权与开关；可能返回缓存扫描', 'Location access and enabled location; results may be cached'),
    ('network', 'wifi-enable', '请求开关 Wi-Fi', 'Request Wi-Fi on or off',
     'termux-wifi-enable true',
     'true / false；受 Android / target SDK 限制', 'true / false; Android / target SDK restrictions apply'),
    ('network', 'location', '取得定位结果', 'Request location',
     'termux-location -p gps -r once',
     '-p gps / network / passive；-r once / last / updates；定位权限', '-p gps / network / passive; -r once / last / updates; location access'),
    ('network', 'telephony-cellinfo', '读取蜂窝小区信息', 'Read cell information',
     'termux-telephony-cellinfo',
     '需电话 / 定位授权与蜂窝硬件', 'Phone / location access and cellular hardware'),
    ('network', 'telephony-deviceinfo', '读取电话设备信息', 'Read telephony device information',
     'termux-telephony-deviceinfo',
     'IMEI 等标识可能被系统隐藏', 'Identifiers such as IMEI may be restricted'),
    ('phone', 'contact-list', '读取联系人', 'Read contacts',
     'termux-contact-list',
     '联系人读取权限', 'Contacts permission'),
    ('phone', 'call-log', '读取通话记录', 'Read the call log',
     'termux-call-log -l 10 -o 0',
     '-l 条数；-o 偏移；通话记录权限', '-l limit; -o offset; call-log permission'),
    ('phone', 'sms-list', '查询短信或会话', 'Query SMS messages or conversations',
     'termux-sms-list -t inbox -l 10 -o 0',
     '-t 类型；-c 会话；-f 号码；短信读取权限', '-t type; -c conversations; -f number; SMS read access'),
    ('phone', 'sms-send', '发送短信', 'Send an SMS',
     'termux-sms-send -n "$PHONE_NUMBER" "测试消息"',
     '先设 PHONE_NUMBER；-s SIM slot；实际发送，可能收费', 'Set PHONE_NUMBER; -s SIM slot; sends a real SMS, charges may apply'),
    ('phone', 'telephony-call', '发起电话呼叫', 'Place a phone call',
     'termux-telephony-call "$PHONE_NUMBER"',
     '先设 PHONE_NUMBER；实际拨号，需呼叫权限', 'Set PHONE_NUMBER; places a real call; call permission'),
    ('phone', 'sms-inbox', '已废弃的入口', 'Retired command',
     'termux-sms-list -t inbox -l 10',
     '已废弃；下方为替代命令', 'Retired; replacement shown below'),
    ('hardware', 'sensor', '列出和读取传感器', 'List and sample sensors',
     'termux-sensor -l\ntermux-sensor -s "$SENSOR_NAME" -n 1',
     '先设 SENSOR_NAME；-n 次数；-d 毫秒；-c 清理', 'Set SENSOR_NAME; -n count; -d ms; -c cleanup'),
    ('hardware', 'usb', '列出或授权 USB 设备', 'List or authorize USB devices',
     'termux-usb -l',
     '-r 授权；-e command 接收 fd；-E 用 TERMUX_USB_FD', '-r requests access; -e command receives fd; -E uses TERMUX_USB_FD'),
    ('hardware', 'infrared-frequencies', '查询红外发射频段', 'List IR carrier frequency ranges',
     'termux-infrared-frequencies',
     '需红外发射器', 'Requires an IR emitter'),
    ('hardware', 'infrared-transmit', '发送红外脉冲', 'Transmit an IR pulse pattern',
     'termux-infrared-transmit -f 38000 9000,4500,560,560',
     '-f Hz；脉冲时长 μs；仅示范语法，编码按设备协议', '-f Hz; pulse durations in μs; syntax only, use the device’s protocol'),
    ('hardware', 'nfc', '读写 NDEF 标签', 'Read or write NDEF tags',
     'termux-nfc -r full',
     '-r short / full；-w -t 文本写入；需开启 NFC', '-r short / full; -w -t text writes; enable NFC'),
    ('hardware', 'fingerprint', '请求指纹认证', 'Request fingerprint authentication',
     'termux-fingerprint -t "验证身份"',
     '需指纹硬件和已录入指纹', 'Requires supported hardware and an enrolled fingerprint'),
    ('saf', 'saf-managedir', '授权一个文档目录', 'Grant access to a document tree',
     'DIR_URI=$(termux-saf-managedir)',
     '选择目录 → DIR_URI；取消可返回空值', 'Pick a folder → DIR_URI; cancellation may return empty'),
    ('saf', 'saf-dirs', '列出已授权目录', 'List authorized document trees',
     'termux-saf-dirs',
     '列出已授权的 content:// 目录', 'Lists authorized content:// directory URIs'),
    ('saf', 'saf-ls', '列出目录内容', 'List a document tree',
     'termux-saf-ls "$DIR_URI"',
     'DIR_URI 为目录 URI，非文件路径', 'DIR_URI is a folder URI, not a filesystem path'),
    ('saf', 'saf-mkdir', '创建文档目录', 'Create a document directory',
     'termux-saf-mkdir "$DIR_URI" notes',
     '在已授权父目录下创建', 'Creates within an authorized parent tree'),
    ('saf', 'saf-create', '创建文档文件', 'Create a document file',
     'FILE_URI=$(termux-saf-create -t text/plain "$DIR_URI" note.txt)',
     '返回 FILE_URI；重名可能自动改名', 'Returns FILE_URI; name collisions may be renamed'),
    ('saf', 'saf-read', '读取文档内容', 'Read document contents',
     'termux-saf-read "$FILE_URI"',
     '原始内容 → stdout', 'Raw contents → stdout'),
    ('saf', 'saf-write', '覆盖文档内容', 'Overwrite document contents',
     'printf %s "hello" | termux-saf-write "$FILE_URI"',
     'stdin → 覆盖已有文件；不是追加', 'stdin → replace existing contents; not append'),
    ('saf', 'saf-stat', '查询文档属性', 'Inspect document metadata',
     'termux-saf-stat "$FILE_URI"',
     '名称、类型等元数据', 'Name, type, and other metadata'),
    ('saf', 'saf-rm', '删除文档', 'Delete a document',
     'termux-saf-rm "$FILE_URI"',
     '删除前用 saf-stat 确认 URI', 'Confirm the URI with saf-stat before deleting'),
    ('automation', 'job-scheduler', '安排后台脚本任务', 'Schedule background scripts',
     'termux-job-scheduler --script "$HOME/bin/check.sh" --job-id 7 --period-ms 900000 --network any',
     '脚本需可执行；--pending；--cancel --job-id 7；周期 ≥15 分钟（Android 7+），非准点', 'Executable script required; --pending; --cancel --job-id 7; period ≥15 min on Android 7+, approximate'),
    ('automation', 'api-start', '启动 API 保活服务', 'Start the API keep-alive service',
     'termux-api-start',
     'KeepAliveService；不授予权限', 'KeepAliveService; does not grant permissions'),
    ('automation', 'api-stop', '停止 API 保活服务', 'Stop the API keep-alive service',
     'termux-api-stop',
     '停止 KeepAliveService', 'Stops KeepAliveService'),
    ('automation', 'keystore', '管理 Android Keystore 密钥', 'Manage Android Keystore keys',
     'termux-keystore list -d',
     'generate / sign / verify / delete；RSA / EC', 'generate / sign / verify / delete; RSA / EC'),
]

def codeblock(text, lang, source='', name=''):
    label = 'Copy' if lang == 'en' else '复制'
    code = escape(text)
    if source and name in text:
        code = code.replace(name, f'<a class="command-name" href="{source}" target="_blank" rel="noopener">{name}</a>', 1)
    return f'<div class="termux-code"><pre><code>{code}</code></pre><button type="button" class="termux-copy">{label}</button></div>'


def command_groups(lang):
    en = lang == 'en'
    output = []
    for key, zh, english in GROUPS:
        title = english if en else zh
        rows = []
        for group, suffix, purpose_zh, purpose_en, example, note_zh, note_en in COMMANDS:
            if group != key:
                continue
            name = 'termux-' + suffix
            source = f'{SOURCE}{name}.in'
            purpose = purpose_en if en else purpose_zh
            note = note_en if en else note_zh
            # Keep the retired command searchable and visible beside its replacement.
            retired = f'<a class="command-name retired-command" href="{source}" target="_blank" rel="noopener"><code>{name}</code></a>' if name not in example else ''
            note_html = f'<p class="command-note">{escape(note)}</p>' if note else ''
            rows.append(f'<div class="command-row" data-command="{name}"><div class="command-purpose">{escape(purpose)}{retired}</div>{codeblock(example, lang, source, name)}{note_html}</div>')
        output.append(f'<section class="command-group" data-category="{key}" aria-labelledby="{lang}-termux-{key}"><header class="command-group-heading"><h2 id="{lang}-termux-{key}">{title}</h2><span>{len(rows):02d}</span></header>{"".join(rows)}</section>')
    return '<div class="termux-grid">' + ''.join(output) + '</div>'


def body(lang):
    en = lang == 'en'
    options = ''.join(f'<option value="{key}">{english if en else zh}</option>' for key,zh,english in GROUPS)
    title = 'Termux:API Command Cheatsheet' if en else 'Termux:API 命令速查'
    lead = '57 command entry points · 9 categories · termux-api 0.60.0' if en else '57 个命令入口 · 9 类用途 · termux-api 0.60.0'
    setup = ('Install the <a href="https://f-droid.org/en/packages/com.termux.api/">Termux:API app</a> from the same source as Termux.' if en else '先安装与 Termux 同来源的 <a href="https://f-droid.org/en/packages/com.termux.api/">Termux:API 插件</a>。')
    controls = f'''<div class="termux-toolbar"><label class="termux-search"><span class="termux-sr-only">{'Search commands' if en else '搜索命令'}</span><input type="search" data-termux-search placeholder="{'Search command, task, flag…' if en else '搜索命令、用途、参数…'}"></label><label><span class="termux-sr-only">{'Category' if en else '分类'}</span><select data-termux-category><option value="all">{'All categories' if en else '全部分类'}</option>{options}</select></label><button type="button" data-termux-reset>{'Reset' if en else '重置'}</button><button type="button" data-termux-print>{'Print / PDF' if en else '打印 / PDF'}</button><span class="termux-results" role="status" aria-live="polite">57 / 57</span></div><p class="termux-empty" hidden>{'No matching commands.' if en else '没有匹配的命令。'}</p>'''
    footer = ('''<span>Grant the corresponding Android permissions. Device and background restrictions apply.</span><span>SAF uses content:// URIs; set named variables before use.</span>''' if en else '''<span>按命令授予 Android 权限；功能受硬件与系统后台限制。</span><span>SAF 使用 content:// URI；变量需先赋值。</span>''')
    sources = f'''<a href="https://github.com/termux/termux-api-package/tree/{REV}">{'v0.60.0 source' if en else 'v0.60.0 源码'}</a><a href="https://github.com/termux-play-store">{'Google Play differences' if en else 'Google Play 分支差异'}</a>'''
    return f'''<div class="lang-{lang}"><div class="termux-sheet" data-language="{lang}"><h1>{title}</h1><p class="lead">{lead}</p><div class="termux-setup"><span>{setup}</span>{codeblock('pkg install termux-api',lang)}</div>{controls}{command_groups(lang)}<footer class="termux-footer">{footer}<span>{sources}</span></footer></div></div>'''


def main():
    names = ['termux-'+r[1] for r in COMMANDS]
    assert len(names) == len(set(names)) == 57
    metadata = {
        'title':'Termux:API 命令速查','title_en':'Termux:API Command Cheatsheet',
        'slug':'cheatsheet-termux-api','date':'2026-10-30',
        'tags':'Termux, Android, CLI, Cheatsheet','tags_en':'Termux, Android, CLI, Cheatsheet',
        'reading':'速查表','reading_en':'Reference sheet',
        'summary':'57 个 Termux:API 命令的紧凑分栏速查，涵盖设备、文件、通知、音频、定位与任务，支持搜索、复制和打印。',
        'summary_en':'A compact, multi-column reference for 57 Termux:API commands, with examples, search, copying, and printing.',
        'series':'cheatsheets','series_title':'Cheatsheets','series_title_en':'Cheatsheets','series_order':'9',
    }
    meta = '\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in metadata.items())
    page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Termux:API 命令速查</title>
{meta}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/cheatsheets/termux-api.css?v=compact-2">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/cheatsheets/termux-api.js?v=compact-2" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">
{body('zh')}{body('en')}
</main></div></body></html>\n'''
    path = ROOT/'posts/cheatsheet-termux-api.html'
    path.write_text(page)
    print('Wrote',path)


if __name__ == '__main__':
    main()
