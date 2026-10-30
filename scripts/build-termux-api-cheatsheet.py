#!/usr/bin/env python3
"""Build a native, searchable reference for all v0.60.0 Termux:API scripts."""
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

# group, command suffix, purpose zh/en, example, note zh/en
COMMANDS = [
    ('device','battery-status','读取电量与充电状态','Read battery and charging status',
     'termux-battery-status', '通常返回 JSON；字段与可用传感数据取决于设备。', 'Usually JSON; available fields depend on the device.'),
    ('device','brightness','设置屏幕亮度','Set display brightness',
     'termux-brightness 128\ntermux-brightness auto', '范围 0–255，auto 恢复自动亮度；可能需要“修改系统设置”授权。', 'Range 0–255; auto restores automatic brightness. May require Modify system settings access.'),
    ('device','torch','开关手电筒','Toggle the flashlight',
     'termux-torch on\ntermux-torch off', '需要带闪光灯的相机硬件及相机权限。', 'Requires suitable camera/flash hardware and camera permission.'),
    ('device','vibrate','控制振动','Vibrate the device',
     'termux-vibrate -d 200', '-d 单位为毫秒；-f 在静音模式下也请求振动。', '-d is in milliseconds; -f requests vibration even in silent mode.'),
    ('device','volume','查询或调整音量','Inspect or change volume',
     'termux-volume\ntermux-volume music 5', '先查各 stream 的 max_volume；支持 alarm、music、notification、ring、system、call。', 'Inspect each stream’s max_volume first. Streams: alarm, music, notification, ring, system, call.'),
    ('device','audio-info','查询音频设备状态','Inspect audio state',
     'termux-audio-info', '返回 Android 音频相关信息；不是录音命令。', 'Returns Android audio information; it does not record audio.'),
    ('device','wallpaper','设置桌面或锁屏壁纸','Set home or lock-screen wallpaper',
     'termux-wallpaper -f "$HOME/wallpaper.jpg"', '-f 本地文件，-u URL；加 -l 设置锁屏（Android 7+）。', '-f accepts a local file, -u a URL; add -l for the lock screen on Android 7+.'),

    ('files','clipboard-get','读取剪贴板文本','Read clipboard text',
     'termux-clipboard-get', 'Android 的后台剪贴板访问限制可能影响结果，先在手机前台测试。', 'Android background clipboard restrictions can apply; test with the phone UI in the foreground.'),
    ('files','clipboard-set','写入剪贴板文本','Write clipboard text',
     'printf %s "hello from Termux" | termux-clipboard-set', '也可直接传文本参数；无参数时读取 stdin。', 'Accepts text arguments, or reads stdin when none are supplied.'),
    ('files','share','调用 Android 分享或查看','Open Android share or view UI',
     'termux-share -a send "$HOME/report.txt"', '-a 可选 send / view；-c 指定 MIME 类型；无文件参数时可从 stdin 分享文本。', '-a selects send/view; -c sets MIME type. Without a file, text can come from stdin.'),
    ('files','download','交给系统下载管理器','Use the system download manager',
     'termux-download -t "Example page" https://example.com/', '-t 标题，-d 描述，-p 完整目标路径；目标必须是 Android 下载管理器可写的位置。', '-t title, -d description, -p full destination path; Android DownloadManager must be able to write there.'),
    ('files','storage-get','通过文件选择器导入文件','Import a file through the picker',
     'termux-storage-get "$HOME/imported.txt"', '在系统选择器中选择来源，复制到指定本地文件；不等于授予整个存储权限。', 'Pick a source and copy it to the local destination; this does not grant access to all storage.'),

    ('ui','toast','显示短提示','Display a toast',
     'termux-toast -s -g bottom "任务完成"', '-s 短时显示；-g 为 top / middle / bottom；也支持 stdin 文本。', '-s is short duration; -g selects top/middle/bottom. Text can also come from stdin.'),
    ('ui','dialog','用系统对话框取得输入','Collect input with a dialog',
     'termux-dialog text -t "备注" -i "输入内容"', '-l 列出 widget；支持 confirm、checkbox、counter、date、radio、sheet、spinner、speech、text、time。', '-l lists widgets: confirm, checkbox, counter, date, radio, sheet, spinner, speech, text, time.'),
    ('ui','notification','发布或更新通知','Post or update a notification',
     'termux-notification --id 42 --title "任务完成" --content "结果已保存"', '同一个 --id 更新已有通知；--action / --button1-action 可执行动作；通知显示需系统允许。', 'Reusing --id updates a notification. --action/--button1-action attach actions; notification display must be allowed.'),
    ('ui','notification-list','列出可读取的系统通知','List accessible system notifications',
     'termux-notification-list', '需要为 Termux:API 启用“通知使用权 / 通知访问”，不同于发送通知权限。', 'Requires notification-listener access for Termux:API, distinct from permission to post notifications.'),
    ('ui','notification-remove','移除指定通知','Remove a notification by ID',
     'termux-notification-remove 42', '配合自己发布通知时使用的 --id。', 'Use the ID supplied when posting your notification.'),
    ('ui','notification-channel','管理通知渠道','Manage notification channels',
     'termux-notification-channel tasks "任务通知"', 'Android 8+；--channel tasks 用于发布；-d tasks 删除该渠道。', 'Android 8+. Post with --channel tasks; -d tasks deletes that channel.'),

    ('media','camera-info','列出相机信息','List camera information',
     'termux-camera-info', '先取得 camera ID，再传给 camera-photo -c；需相机权限。', 'Obtain a camera ID before using camera-photo -c; camera permission is required.'),
    ('media','camera-photo','拍照并保存','Capture a photo',
     'termux-camera-photo -c 0 "$HOME/photo.jpg"', '将 0 换成 camera-info 返回的实际 ID；需要前台/相机访问条件满足。', 'Replace 0 with an actual camera ID; foreground and camera access rules must be satisfied.'),
    ('media','media-player','播放本地媒体','Play local media',
     'termux-media-player play "$HOME/music.mp3"', 'info 查询；pause 暂停；play 无路径为恢复；stop 停止。', 'info inspects; pause pauses; play without a path resumes; stop stops playback.'),
    ('media','media-scan','刷新系统媒体索引','Refresh the media index',
     'termux-media-scan -r "$HOME/storage/shared/Pictures"', '-r 递归，-v 显示详情；扫描不会自动赋予文件访问权限。', '-r recurses, -v is verbose; scanning does not grant file permissions.'),
    ('media','microphone-record','录制麦克风音频','Record microphone audio',
     'termux-microphone-record -f "$HOME/clip.m4a" -l 10 -e aac', '-l 秒数，0 为不限时；-i 查询，-q 停止；-b kbps、-r Hz、-c 声道数。需录音权限。', '-l seconds, 0 for no limit; -i inspects, -q stops. -b kbps, -r Hz, -c channels. Requires microphone permission.'),
    ('media','speech-to-text','语音识别','Recognize speech',
     'termux-speech-to-text', '需要系统可用的语音识别服务和麦克风权限；是否联网取决于服务。', 'Requires a speech recognition service and microphone permission; network use depends on that service.'),
    ('media','tts-engines','列出语音合成引擎','List text-to-speech engines',
     'termux-tts-engines', '取得引擎名供 tts-speak -e 使用。', 'Use an engine name with tts-speak -e.'),
    ('media','tts-speak','朗读文本','Speak text',
     'termux-tts-speak -l zh -n CN "任务已经完成"', '-r 语速、-p 音调默认均为 1.0；可从 stdin 读文本；语言包需引擎支持。', '-r rate and -p pitch default to 1.0. Accepts stdin; language support depends on installed voices.'),

    ('network','wifi-connectioninfo','当前 Wi-Fi 连接信息','Inspect the current Wi-Fi connection',
     'termux-wifi-connectioninfo', 'SSID、地址等字段可能受 Android 权限与隐私限制。', 'SSID, addresses, and other fields can be restricted by Android permissions and privacy rules.'),
    ('network','wifi-scaninfo','获取 Wi-Fi 扫描结果','Read Wi-Fi scan results',
     'termux-wifi-scaninfo', '通常需定位授权和系统定位开关；可能返回已有扫描结果，不保证每次都是新扫描。', 'Usually requires location permission and enabled location; results may come from an existing scan.'),
    ('network','wifi-enable','请求开关 Wi-Fi','Request Wi-Fi on or off',
     'termux-wifi-enable true', 'false 请求关闭；能否生效取决于 Android 版本、应用 target SDK 和厂商限制。', 'false requests off. Availability depends on Android version, app target SDK, and vendor restrictions.'),
    ('network','location','取得定位结果','Request location',
     'termux-location -p gps -r once', '-p 为 gps / network / passive；-r 为 once / last / updates；last 可能没有缓存。需定位权限。', '-p: gps/network/passive; -r: once/last/updates. last may have no cached fix. Location permission is required.'),
    ('network','telephony-cellinfo','读取蜂窝小区信息','Read cell information',
     'termux-telephony-cellinfo', '需相关电话/定位权限和蜂窝硬件；可见字段受系统限制。', 'Requires relevant phone/location permissions and cellular hardware; fields are system-restricted.'),
    ('network','telephony-deviceinfo','读取电话设备信息','Read telephony device information',
     'termux-telephony-deviceinfo', '不保证可读取 IMEI 等设备标识，Android 对这些字段另有限制。', 'Does not guarantee access to identifiers such as IMEI; Android restricts those separately.'),

    ('phone','contact-list','读取联系人','Read contacts',
     'termux-contact-list', '需要联系人读取权限；输出可能包含姓名和号码。', 'Requires Contacts access; output can contain names and numbers.'),
    ('phone','call-log','读取通话记录','Read the call log',
     'termux-call-log -l 10 -o 0', '-l 条数，-o 偏移；需要通话记录权限。', '-l limit, -o offset; requires call-log permission.'),
    ('phone','sms-list','查询短信或会话','Query SMS messages or conversations',
     'termux-sms-list -t inbox -l 10 -o 0', '-t all/inbox/sent/draft/outbox/failed/queued；-c 查询会话；-f 过滤号码。需要短信读取权限。', '-t all/inbox/sent/draft/outbox/failed/queued; -c queries conversations; -f filters sender. Requires SMS read access.'),
    ('phone','sms-send','发送短信','Send an SMS',
     'termux-sms-send -n "$PHONE_NUMBER" "测试消息"', '先设置真实的 PHONE_NUMBER；-s 选择 SIM slot。会实际发送短信，可能产生运营商费用。', 'Set PHONE_NUMBER first; -s selects a SIM slot. Sends a real SMS and may incur carrier charges.'),
    ('phone','telephony-call','发起电话呼叫','Place a phone call',
     'termux-telephony-call "$PHONE_NUMBER"', '先设置 PHONE_NUMBER；会实际发起呼叫，需呼叫权限。', 'Set PHONE_NUMBER first. Places an actual call and requires call permission.'),
    ('phone','sms-inbox','已废弃的入口','Retired command',
     'termux-sms-list -t inbox -l 10', 'v0.60.0 中原命令只打印替代提示并退出 1；使用上方替代命令。', 'In v0.60.0 the old command only prints a replacement notice and exits 1. Use the shown replacement.'),

    ('hardware','sensor','列出和读取传感器','List and sample sensors',
     'termux-sensor -l\ntermux-sensor -s "$SENSOR_NAME" -n 1', '根据列表设置 SENSOR_NAME；-d 毫秒间隔，-n 次数，-c 释放监听；默认持续监听。', 'Set SENSOR_NAME from the list. -d interval in ms, -n sample count, -c cleanup; default sampling is continuous.'),
    ('hardware','usb','列出或授权 USB 设备','List or authorize USB devices',
     'termux-usb -l', '-r 请求设备授权；-e command 传递打开的文件描述符，-E 改用 TERMUX_USB_FD 环境变量。', '-r requests device access; -e command passes an open file descriptor; -E uses TERMUX_USB_FD instead.'),
    ('hardware','infrared-frequencies','查询红外发射频段','List IR carrier frequency ranges',
     'termux-infrared-frequencies', '需要手机带红外发射器；没有硬件时命令无法提供该能力。', 'Requires a physical infrared emitter.'),
    ('hardware','infrared-transmit','发送红外脉冲','Transmit an IR pulse pattern',
     'termux-infrared-transmit -f 38000 9000,4500,560,560', '-f 为 Hz，pattern 为微秒时长列表；这里只是脉冲语法示例，实际编码取决于设备协议。', '-f is Hz; pattern durations are microseconds. This illustrates syntax; use the target device’s actual protocol.'),
    ('hardware','nfc','读写 NDEF 标签','Read or write NDEF tags',
     'termux-nfc -r full', '-r short/full 读取；-w -t "内容" 写标签；需 NFC 硬件、开启 NFC 并贴近标签。', '-r short/full reads; -w -t "text" writes. Requires NFC hardware, NFC enabled, and a nearby tag.'),
    ('hardware','fingerprint','请求指纹认证','Request fingerprint authentication',
     'termux-fingerprint -t "验证身份"', '需支持的指纹硬件和已录入指纹；返回认证结果，不读取指纹原始数据。', 'Requires supported hardware and an enrolled fingerprint. Returns authentication results, not raw fingerprint data.'),

    ('saf','saf-managedir','授权一个文档目录','Grant access to a document tree',
     'DIR_URI=$(termux-saf-managedir)', '打开系统目录选择器，返回 content:// URI；取消可能返回空字符串。', 'Opens the system folder picker and returns a content:// URI; cancellation can return an empty string.'),
    ('saf','saf-dirs','列出已授权目录','List authorized document trees',
     'termux-saf-dirs', '只列出通过 SAF 授权给 Termux:API 的目录。', 'Lists document trees authorized for Termux:API through SAF.'),
    ('saf','saf-ls','列出目录内容','List a document tree',
     'termux-saf-ls "$DIR_URI"', '参数是 SAF folder URI，不是 /sdcard 路径。', 'Takes a SAF folder URI, not a /sdcard path.'),
    ('saf','saf-mkdir','创建文档目录','Create a document directory',
     'termux-saf-mkdir "$DIR_URI" notes', '在已授权父目录下创建子目录。', 'Creates a child directory within an authorized parent tree.'),
    ('saf','saf-create','创建文档文件','Create a document file',
     'FILE_URI=$(termux-saf-create -t text/plain "$DIR_URI" note.txt)', '返回新文件 URI；同名时 provider 可能改名，用 saf-stat 核对。', 'Returns the new file URI; a provider may rename collisions. Check with saf-stat.'),
    ('saf','saf-read','读取文档内容','Read document contents',
     'termux-saf-read "$FILE_URI"', '原始内容写到 stdout，可重定向到本地文件。', 'Writes raw contents to stdout; redirect to save a local copy.'),
    ('saf','saf-write','覆盖文档内容','Overwrite document contents',
     'printf %s "hello" | termux-saf-write "$FILE_URI"', '从 stdin 读取并覆盖原内容，不是追加写；文件需先存在。', 'Reads stdin and replaces existing contents, not an append. The document must already exist.'),
    ('saf','saf-stat','查询文档属性','Inspect document metadata',
     'termux-saf-stat "$FILE_URI"', '检查文档名称、类型等 provider 返回的元数据。', 'Inspect document name, type, and other provider-reported metadata.'),
    ('saf','saf-rm','删除文档','Delete a document',
     'termux-saf-rm "$FILE_URI"', '会删除该 URI 对应的文档；执行前用 saf-stat 确认目标。', 'Deletes the document at that URI; confirm the target with saf-stat first.'),

    ('automation','job-scheduler','安排后台脚本任务','Schedule background scripts',
     'termux-job-scheduler --script "$HOME/bin/check.sh" --job-id 7 --period-ms 900000 --network any', '脚本必须存在且可执行；--pending 查看；--cancel --job-id 7 取消。不是精确定时器。', 'Script must exist and be executable. --pending lists jobs; --cancel --job-id 7 cancels. Timing is approximate.'),
    ('automation','api-start','启动 API 保活服务','Start the API keep-alive service',
     'termux-api-start', '启动插件的 KeepAliveService；不是安装、授权或开机启动配置。', 'Starts the plugin’s KeepAliveService; it does not install, grant permissions, or configure boot startup.'),
    ('automation','api-stop','停止 API 保活服务','Stop the API keep-alive service',
     'termux-api-stop', '停止对应 KeepAliveService；不是删除插件或卸载命令包。', 'Stops KeepAliveService; it does not uninstall the plugin or CLI package.'),
    ('automation','keystore','管理 Android Keystore 密钥','Manage Android Keystore keys',
     'termux-keystore list -d', '支持 generate / sign / verify / delete；RSA 或 EC。私钥保存在 Keystore；硬件保护能力取决于设备。', 'Supports generate/sign/verify/delete, with RSA or EC. Private keys remain in Keystore; hardware protection is device-dependent.'),
]

INSTALL = '''pkg update
pkg install termux-api jq

# Inspect the installed CLI package and its commands.
dpkg-query -W termux-api
dpkg -L termux-api | sed -n '\\|/bin/termux-|p'

termux-battery-status
termux-toast -s "Termux:API ready"'''
RECIPES = [
    ('battery', '电量通知', 'Battery notification',
     '''battery=$(termux-battery-status) || exit 1
percent=$(printf '%s' "$battery" | jq -er '.percentage | select(type == "number")') || exit 1
termux-notification --id 100 --title "电量" --content "${percent}%"''',
     '先检查返回值和 JSON 字段再拼接通知，避免把授权错误当成电量。',
     'Check the result and JSON field before building a notification, so a permission error is not treated as a battery value.'),
    ('saf', 'SAF 文件读写', 'SAF file workflow',
     '''DIR_URI=$(termux-saf-managedir) || exit 1
case "$DIR_URI" in content://*) ;; *) exit 1 ;; esac
FILE_URI=$(termux-saf-create -t text/plain "$DIR_URI" note.txt) || exit 1
case "$FILE_URI" in content://*) ;; *) exit 1 ;; esac
printf '%s\\n' "hello from Termux" | termux-saf-write "$FILE_URI"
termux-saf-stat "$FILE_URI"
termux-saf-read "$FILE_URI"''',
     '目录授权返回 URI 后，再创建文件并写入。content:// URI 交给 SAF 命令，不能直接交给 cat、cp 或普通文件路径接口。',
     'Authorize a tree, create a document, then write it. Pass content:// URIs to SAF commands rather than cat, cp, or ordinary filesystem APIs.'),
    ('job', '周期任务', 'Periodic job',
     '''mkdir -p "$HOME/bin"
cat > "$HOME/bin/check-battery.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
termux-battery-status | jq -c . >> "$HOME/battery-history.jsonl"
SH
chmod +x "$HOME/bin/check-battery.sh"
termux-job-scheduler --script "$HOME/bin/check-battery.sh" --job-id 7 --period-ms 900000
termux-job-scheduler --pending
# To remove this job later:
# termux-job-scheduler --cancel --job-id 7''',
     'Android 7+ 的周期下限为 15 分钟；Doze、网络、电量和后台政策会影响实际执行时间。--persisted true 可请求重启后保留任务，仍受系统条件约束。',
     'Android 7+ imposes a 15-minute minimum period. Doze, network, battery, and background rules affect execution time. --persisted true requests survival across reboot, subject to system conditions.'),
]


def codeblock(text, lang, copy=False):
    button = f'<button type="button" class="termux-copy">{"Copy" if lang=="en" else "复制"}</button>' if copy else ''
    return f'<div class="termux-code">{button}<pre><code>{escape(text)}</code></pre></div>'


def command_groups(lang):
    en = lang == 'en'
    output = []
    for key, zh, english in GROUPS:
        title = english if en else zh
        rows = []
        for row in COMMANDS:
            group, suffix, purpose_zh, purpose_en, example, note_zh, note_en = row
            if group != key:
                continue
            name = 'termux-'+suffix
            note = note_en if en else note_zh
            purpose = purpose_en if en else purpose_zh
            source = f'{SOURCE}{name}.in'
            rows.append(f'<tr class="command-row" data-command="{name}"><td><a class="command-name" href="{source}" target="_blank" rel="noopener"><code>{name}</code></a><span class="command-purpose">{escape(purpose)}</span></td><td>{codeblock(example,lang,True)}</td><td class="command-note">{escape(note)}</td></tr>')
        output.append(f'<section class="command-group" data-category="{key}"><h3 id="{lang}-termux-{key}">{title}</h3><table><thead><tr><th>{"Command / purpose" if en else "命令 / 用途"}</th><th>{"Example" if en else "示例"}</th><th>{"Options / requirements" if en else "参数 / 条件"}</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>')
    return ''.join(output)


def body(lang):
    en = lang == 'en'
    options = ''.join(f'<option value="{key}">{english if en else zh}</option>' for key,zh,english in GROUPS)
    controls = f'''<div class="termux-toolbar"><label>{'Search' if en else '搜索'}<input type="search" data-termux-search placeholder="{'command, task, flag…' if en else '命令、用途、参数…'}"></label><label>{'Category' if en else '分类'}<select data-termux-category><option value="all">{'All categories' if en else '全部分类'}</option>{options}</select></label><button type="button" data-termux-reset>{'Reset' if en else '重置'}</button><button type="button" data-termux-print>{'Print / PDF' if en else '打印 / PDF'}</button></div><p class="termux-results" role="status" aria-live="polite">{'57 commands' if en else '共 57 个命令入口'}</p><p class="termux-empty" hidden>{'No matching commands. Clear the search or choose another category.' if en else '没有匹配的命令。请清空搜索或调整分类。'}</p>'''
    if en:
        intro = '''<h1>Termux:API command cheatsheet</h1><p class="lead">Termux:API exposes Android capabilities to shell commands: battery status, clipboard access, notifications, camera and audio, location, and authorized document storage. This sheet covers all 57 command entry points shipped in termux-api 0.60.0, including one retired entry, with examples and links to the corresponding scripts.</p>
<h2 id="en-setup">1. Setup</h2><h3 id="en-install">App and package</h3>
<p>For the main Termux distribution, install the <a href="https://f-droid.org/en/packages/com.termux.api/">Termux:API Android plugin</a> alongside Termux, then install the termux-api CLI package inside the terminal. Termux and its plugin must have compatible signatures, so use the same installation source. Installing the package alone does not install the Android app. <a href="https://github.com/termux/termux-api/blob/6c8eaa223bcc387e6b28146d340acb20712aa3e7/README.md">Official installation notes</a>.</p>'''
        intro += codeblock(INSTALL,lang,True)
        intro += '''<p>The scripts send requests to Termux:API, which invokes Android services and returns results. Many commands produce JSON, while clipboard and document reads can produce plain text or raw bytes. Inspect the output before piping it into jq. Package and Android app versions are separate.</p>
<h3 id="en-compat">Permissions and variants</h3>
<p>The <a href="https://github.com/termux-play-store">Google Play branch</a> integrates some API functionality into its main app and has a different support list. This reference uses the main CLI package’s <a href="https://github.com/termux/termux-api-package/tree/9e7f1531e1aa4a9c1e261a2dbde4de93653c366e">v0.60.0 source</a>. Available commands depend on the installed package, Android app, and device; check the local command list and help.</p>
<p>Contacts, SMS, calls, camera, microphone, and location require their corresponding Android access. Notification listening and modifying system settings can require separate settings-page grants. A shell command retains the app’s permission boundaries; keep the phone UI available when a command opens a picker or permission prompt.</p>
<h2 id="en-commands">2. Command index</h2><p>Command names link to the pinned source. Copy buttons copy text only. Set PHONE_NUMBER, SENSOR_NAME, DIR_URI, or FILE_URI as described before using examples that reference them.</p>'''
    else:
        intro = '''<h1>Termux:API 命令速查</h1><p class="lead">Termux:API 将 Android 的电量、剪贴板、通知、相机、音频、定位与文档访问能力接入 Shell。本文收录 termux-api 0.60.0 提供的全部 57 个命令入口，其中包括一个已废弃入口，按用途整理示例、常用参数和执行条件，命令名可直接打开对应源码。</p>
<h2 id="zh-setup">1. 安装与检查</h2><h3 id="zh-install">插件与命令包</h3>
<p>主线 Termux 需要两个部分：手机上安装 <a href="https://f-droid.org/en/packages/com.termux.api/">Termux:API Android 插件</a>，终端里安装 termux-api 命令包。Termux 与插件需要兼容的签名，应使用同一安装来源；只执行 pkg install 不会安装 Android 插件。参见<a href="https://github.com/termux/termux-api/blob/6c8eaa223bcc387e6b28146d340acb20712aa3e7/README.md">官方安装说明</a>。</p>'''
        intro += codeblock(INSTALL,lang,True)
        intro += '''<p>命令脚本把请求交给 Termux:API，由插件调用 Android 服务并返回结果。许多查询返回 JSON，剪贴板和文档读取则可能返回纯文本或原始字节；先看实际输出，再决定是否接 jq。命令包版本与 Android 插件版本是两套版本号。</p>
<h3 id="zh-compat">权限与版本</h3>
<p><a href="https://github.com/termux-play-store">Google Play 分支</a>已把部分 API 能力内建到主应用，支持范围与主线不同。本表以主线命令包的 <a href="https://github.com/termux/termux-api-package/tree/9e7f1531e1aa4a9c1e261a2dbde4de93653c366e">v0.60.0 源码</a>为基准；实际可用命令取决于已安装的命令包、Android 插件和设备，以 dpkg 输出及本地帮助为准。</p>
<p>联系人、短信、电话、相机、录音和定位分别受 Android 权限控制。“通知访问”和“修改系统设置”还可能需要在系统设置里单独授权。Shell 调用仍使用应用的权限边界；需要选择文件或确认权限时，应能操作手机上的系统界面。</p>
<h2 id="zh-commands">2. 命令索引</h2><p>点击命令名查看固定版本源码；复制按钮只复制文本。含 PHONE_NUMBER、SENSOR_NAME、DIR_URI、FILE_URI 的示例，需要先按说明设置变量。</p>'''
    recipes = []
    for key,zh,english,script,note_zh,note_en in RECIPES:
        recipes.append(f'<h3 id="{lang}-recipe-{key}">{english if en else zh}</h3>{codeblock(script,lang,True)}<p>{escape(note_en if en else note_zh)}</p>')
    if en:
        ending = '''<h2 id="en-troubleshooting">4. Troubleshooting</h2>
<table class="termux-troubleshooting"><thead><tr><th>Symptom</th><th>Check</th></tr></thead><tbody>
<tr><td>Command not found</td><td>Check pkg install termux-api and dpkg -L termux-api. The APK alone does not provide shell scripts.</td></tr>
<tr><td>Command hangs or returns a permission error</td><td>Check plugin installation/signature, visible permission dialogs, and the relevant Android permission. Service keep-alive does not grant access.</td></tr>
<tr><td>No clipboard text from a background session</td><td>Check Android foreground-access restrictions and test on the phone. SSH access does not bypass Android permissions.</td></tr>
<tr><td>SAF URI fails with normal file tools</td><td>Use termux-saf-read/write; a content:// URI is not a filesystem pathname.</td></tr>
<tr><td>Scheduled job runs late</td><td>JobScheduler is approximate and subject to constraints and Doze; it is not a precise cron clock.</td></tr>
<tr><td>Sensor/location output never finishes</td><td>Use sensor -n for a sample limit, sensor -c for cleanup, and location -r once/last for single requests. updates behavior depends on the plugin version.</td></tr>
</tbody></table>
<p>Related commands such as termux-info, termux-setup-storage, termux-open, and termux-wake-lock belong to other Termux tools and are not counted in these 57 entries. The libexec termux-api helper is an implementation detail, not an additional everyday user command.</p>
<p>Reference date: 2026-10-30. Command syntax follows the official scripts linked in the index. Additional references: <a href="https://developer.android.com/about/versions/10/privacy/changes#clipboard-data">Android clipboard restrictions</a>, <a href="https://developer.android.com/reference/android/app/job/JobInfo.Builder#setPeriodic(long)">JobScheduler timing</a>, and <a href="https://github.com/termux/termux-api/blob/6c8eaa223bcc387e6b28146d340acb20712aa3e7/app/src/main/java/com/termux/api/apis/NotificationListAPI.java">notification-listener implementation</a>.</p>'''
    else:
        ending = '''<h2 id="zh-troubleshooting">4. 常见问题</h2>
<table class="termux-troubleshooting"><thead><tr><th>现象</th><th>检查方向</th></tr></thead><tbody>
<tr><td>command not found</td><td>检查 pkg install termux-api 和 dpkg -L termux-api；只装 APK 不会提供 Shell 命令。</td></tr>
<tr><td>命令一直等待或报权限错误</td><td>检查插件安装、签名、手机上的授权弹窗及对应权限。启动保活服务不会自动授予权限。</td></tr>
<tr><td>后台会话读不到剪贴板</td><td>检查 Android 前台访问限制，先在手机上测试；通过 SSH 调用也不会绕过系统权限。</td></tr>
<tr><td>普通文件工具打不开 SAF URI</td><td>使用 termux-saf-read/write；content:// URI 不是文件系统路径。</td></tr>
<tr><td>周期任务没有准点执行</td><td>JobScheduler 受约束条件和 Doze 影响，不是精确到时刻的 cron。</td></tr>
<tr><td>传感器或定位输出不结束</td><td>sensor 用 -n 限定次数、-c 清理；单次定位用 -r once/last。updates 的行为还取决于插件版本。</td></tr>
</tbody></table>
<p>termux-info、termux-setup-storage、termux-open、termux-wake-lock 属于其他 Termux 工具，不计入本表 57 个入口。libexec 中的 termux-api helper 是底层实现入口，也不作为额外的日常命令列出。</p>
<p>资料核对日期：2026-10-30。命令语法依据索引中链接的官方脚本。补充来源：<a href="https://developer.android.com/about/versions/10/privacy/changes#clipboard-data">Android 剪贴板限制</a>、<a href="https://developer.android.com/reference/android/app/job/JobInfo.Builder#setPeriodic(long)">JobScheduler 调度语义</a>、<a href="https://github.com/termux/termux-api/blob/6c8eaa223bcc387e6b28146d340acb20712aa3e7/app/src/main/java/com/termux/api/apis/NotificationListAPI.java">通知监听实现</a>。</p>'''
    return f'<div class="lang-{lang}"><div class="termux-sheet" data-language="{lang}">{intro}{controls}{command_groups(lang)}<h2 id="{lang}-recipes">{"3. Recipes" if en else "3. 组合用法"}</h2>{"".join(recipes)}{ending}</div></div>'


def main():
    names = ['termux-'+r[1] for r in COMMANDS]
    assert len(names)==57 and len(set(names))==57
    metadata = {
        'title':'Termux:API 命令速查','title_en':'Termux:API Command Cheatsheet',
        'slug':'cheatsheet-termux-api','date':'2026-10-30',
        'tags':'Termux, Android, CLI, Cheatsheet','tags_en':'Termux, Android, CLI, Cheatsheet',
        'reading':'速查表','reading_en':'Reference sheet',
        'summary':'按用途整理 Termux:API 的 57 个命令入口，覆盖通知、剪贴板、定位、音频、SAF 与任务调度，支持搜索、复制和打印。',
        'summary_en':'A searchable reference for 57 Termux:API commands, covering notifications, clipboard, location, audio, SAF, and jobs, with copy and print controls.',
        'series':'cheatsheets','series_title':'Cheatsheets','series_title_en':'Cheatsheets','series_order':'9',
    }
    meta='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in metadata.items())
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Termux:API 命令速查</title>
{meta}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/cheatsheets/termux-api.css">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/cheatsheets/termux-api.js" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">
{body('zh')}{body('en')}
</main></div></body></html>\n'''
    path=ROOT/'posts/cheatsheet-termux-api.html';path.write_text(page);print('Wrote',path)


if __name__=='__main__':
    main()
