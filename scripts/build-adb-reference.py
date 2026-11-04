#!/usr/bin/env python3
"""Build a concise man-style ADB manual. reference.json retains pinned sources."""
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/cheatsheets/adb-reference'
SOURCES = json.loads((ASSETS / 'reference.json').read_text())['sources']

# Group, stable anchor, syntax, concise Chinese / English description.
ENTRIES = [
    ('options', 'transport', '-d | -e',
     '`-d` 选择 USB 设备，`-e` 选择 TCP/IP 设备；同类设备多于一台时报错。',
     '`-d`: USB device. `-e`: TCP/IP device. Fails if more than one device matches.'),
    ('options', 'serial', '-s SERIAL | -t ID',
     '按序列号或 transport ID 选择设备；`-s` 优先于 `ANDROID_SERIAL`。',
     'Select by serial or transport ID. `-s` overrides `ANDROID_SERIAL`.'),
    ('options', 'server-address', '-H HOST  -P PORT  |  -L SOCKET',
     '指定 ADB server 地址，默认 `localhost:5037`。`-L` 与 `-H` / `-P` 互斥。',
     'ADB server address; default `localhost:5037`. `-L` conflicts with `-H` / `-P`.'),
    ('options', 'listen', '-a',
     '让 ADB server 监听所有网络接口，默认只监听本机。',
     'Make the ADB server listen on all network interfaces instead of localhost.'),
    ('options', 'one-device', '--one-device SERIAL|USB',
     '启动 server 时只连接指定的 USB 设备；用于 `start-server` 或 `server nodaemon`。',
     'Limit the server to one USB device; use with `start-server` or `server nodaemon`.'),
    ('options', 'stdout', '--exit-on-write-error',
     '标准输出关闭时退出。', 'Exit when stdout is closed.'),

    ('session', 'devices', 'adb devices [-l]\nadb help | version',
     '列出设备；`-l` 显示详细信息。`help` 查看帮助，`version` 查看客户端版本。',
     'List devices; `-l` adds details. `help` prints help; `version` reports the client version.'),
    ('session', 'server', 'adb start-server | kill-server | server-status',
     '启动、停止或查询主机上的 ADB server。',
     'Start, stop, or inspect the host ADB server.'),
    ('session', 'state', 'adb get-state | get-serialno | get-devpath\nadb wait-for[-usb|-local|-any]-STATE',
     '查询设备信息，或等待 `device`、`recovery`、`rescue`、`sideload`、`bootloader`、`disconnect` 状态。',
     'Query device information, or wait for `device`, `recovery`, `rescue`, `sideload`, `bootloader`, or `disconnect`.'),

    ('network', 'wireless', 'adb pair HOST:PAIR_PORT [CODE]\nadb connect HOST[:PORT]\nadb disconnect [HOST[:PORT]]',
     '配对、连接或断开无线设备。配对端口与连接端口通常不同；`disconnect` 不带地址时断开全部 TCP/IP 设备。',
     'Pair, connect, or disconnect. Pairing and connection ports usually differ. Without an address, disconnect all TCP/IP devices.'),
    ('network', 'mdns', 'adb mdns check | services',
     '检查 mDNS，或列出发现的无线调试服务。',
     'Check mDNS availability or list discovered wireless debugging services.'),
    ('network', 'forward', 'adb forward [--no-rebind] LOCAL REMOTE\nadb forward --list | --remove LOCAL | --remove-all',
     '主机 → 设备转发；常用端点 `tcp:PORT`、`localabstract:NAME`。`--no-rebind` 禁止覆盖已有映射。',
     'Forward host → device. Common endpoints: `tcp:PORT`, `localabstract:NAME`. `--no-rebind` prevents replacing a mapping.'),
    ('network', 'reverse', 'adb reverse [--no-rebind] REMOTE LOCAL\nadb reverse --list | --remove REMOTE | --remove-all',
     '设备 → 主机转发；例如 `adb reverse tcp:8080 tcp:8080`。',
     'Forward device → host; for example, `adb reverse tcp:8080 tcp:8080`.'),
    ('network', 'tcpip', 'adb tcpip PORT\nadb usb\nadb reconnect [device|offline]',
     '切换 adbd 的 TCP / USB 监听，或重新建立连接；`offline` 重连离线及未授权设备。',
     'Switch adbd to TCP / USB listening, or reconnect. `offline` resets offline and unauthorized connections.'),
    ('network', 'attach', 'adb attach | detach',
     '重新接管或释放 USB 设备，供其他进程使用；需要 libusb 后端。',
     'Reattach or release a USB device for another process; requires the libusb backend.'),

    ('files', 'push', 'adb push [--sync] [-n] [-q] [-z ALGORITHM | -Z] LOCAL... REMOTE',
     '上传；`--sync` 比较时间戳，`-n` 试运行，`-q` 隐藏进度。`-z` 压缩算法：`any/none/brotli/lz4/zstd`；`-Z` 禁用压缩。',
     'Upload. `--sync`: compare timestamps; `-n`: dry run; `-q`: quiet. `-z`: `any/none/brotli/lz4/zstd`; `-Z`: no compression.'),
    ('files', 'pull', 'adb pull [-a] [-q] [-z ALGORITHM | -Z] REMOTE... [LOCAL]',
     '下载；`-a` 保留时间戳与权限。压缩选项同 `push`。',
     'Download; `-a` preserves timestamps and mode. Compression options match `push`.'),
    ('files', 'sync', 'adb sync [-l] [-n] [-q] [-z ALGORITHM | -Z] [PARTITION]',
     '将 `ANDROID_PRODUCT_OUT` 下的系统构建同步到设备；`-l` 仅列出变化，默认同步全部支持的分区。',
     'Sync a system build from `ANDROID_PRODUCT_OUT`; `-l` lists changes. Defaults to all supported partitions.'),
    ('files', 'shell', 'adb shell [-e ESCAPE] [-n] [-T | -t | -tt] [-x] [COMMAND...]',
     '远程 Shell。`-e` 转义字符；`-n` 不读 stdin；`-T` 禁用 PTY，`-t` 按终端状态分配，`-tt` 强制分配；`-x` 禁用退出码与 stdout/stderr 分离。',
     'Remote shell. `-e`: escape character; `-n`: no stdin; `-T`: no PTY; `-t`: PTY when on a TTY; `-tt`: force PTY; `-x`: disable exit codes and separate stdout/stderr.'),
    ('files', 'exec', 'adb exec-in COMMAND [ARGS...]\nadb exec-out COMMAND [ARGS...]',
     '无 PTY 的原始流输入 / 输出；截图等二进制输出可用 `exec-out`。',
     'Raw input / output without a PTY. Use `exec-out` for binary output such as screenshots.'),

    ('install', 'install', 'adb install [-r] [-t] [-d] [-g] [--user ID] [--abi ABI] APK',
     '`-r` 覆盖安装；`-t` 允许测试包；`-d` 允许可调试包降级；`-g` 授予运行时权限。',
     '`-r`: replace; `-t`: allow test packages; `-d`: allow debuggable package downgrade; `-g`: grant runtime permissions.'),
    ('install', 'install-mode', 'adb install [--streaming | --no-streaming] [--instant] APK\nadb install [--incremental | --no-incremental] APK',
     '选择流式 / 先上传安装、instant app 或增量安装。增量模式需要设备与 APK 支持。',
     'Choose streamed / pushed installation, an instant app, or incremental installation. Incremental mode requires device and APK support.'),
    ('install', 'splits', 'adb install-multiple [-r] [-t] [-d] [-p] [-g] APK...\nadb install-multi-package [-r] [-t] [-d] [-g] APK...',
     '`install-multiple` 安装同一应用的 split APK，`-p` 为部分安装；`install-multi-package` 原子安装多个应用。',
     '`install-multiple`: one app with split APKs; `-p`: partial install. `install-multi-package`: atomic installation of multiple apps.'),
    ('install', 'uninstall', 'adb uninstall [-k] PACKAGE',
     '卸载应用；`-k` 保留数据与缓存。',
     'Uninstall an app; `-k` preserves data and cache.'),

    ('diagnostics', 'logs', 'adb logcat [OPTIONS] [FILTER...]\nadb bugreport [PATH]',
     '查看日志或导出诊断报告。Logcat：`-d` 导出后退出，`-c` 清空，`-b BUFFER` 选缓冲区，`-v FORMAT` 选格式；完整参数见 `adb logcat --help`。',
     'Read logs or export a bug report. Logcat: `-d` dump and exit; `-c` clear; `-b BUFFER` select buffer; `-v FORMAT` select format. Full options: `adb logcat --help`.'),
    ('diagnostics', 'jdwp', 'adb jdwp\nadb features | host-features',
     '列出 JDWP 进程；查询客户端与设备共同支持的功能，或 server 功能。',
     'List JDWP process IDs; query shared client/device features or server features.'),

    ('device', 'reboot', 'adb reboot [bootloader|recovery|sideload|sideload-auto-reboot]\nadb sideload OTA.zip',
     '重启到指定模式，或在设备的 sideload 模式下安装 OTA。',
     'Reboot into a selected mode, or install an OTA while the device is in sideload mode.'),
    ('device', 'root', 'adb root | unroot\nadb remount [-R]',
     '重启 adbd 以切换 root；重新挂载为可写，`-R` 必要时重启。通常需要 userdebug / eng 系统。',
     'Restart adbd with / without root; remount writable, with `-R` rebooting if needed. Typically requires a userdebug / eng build.'),
    ('device', 'verity', 'adb disable-verity | enable-verity\nadb keygen FILE',
     '切换 userdebug 系统的 dm-verity 检查；`keygen` 在主机生成 ADB 密钥对。',
     'Toggle dm-verity on userdebug builds. `keygen` generates a host ADB key pair.'),

    ('pm', 'packages', 'adb shell pm list packages [OPTIONS] [FILTER]',
     '`-3` 第三方；`-s` 系统包；`-d/-e` 禁用 / 启用；`-f` 路径；`-i` 安装器；`-U` UID；`-u` 含已卸载包；`--user ID` 指定用户。',
     '`-3`: third-party; `-s`: system; `-d/-e`: disabled/enabled; `-f`: path; `-i`: installer; `-U`: UID; `-u`: include uninstalled; `--user ID`: user.'),
    ('pm', 'path', 'adb shell pm path [--user ID] PACKAGE\nadb shell pm dump PACKAGE',
     '查询 APK 路径或包状态；split 安装会返回多个路径。',
     'Print APK paths or package state. Split installations have multiple APK paths.'),
    ('pm', 'existing', 'adb shell pm install-existing [--user ID] PACKAGE',
     '为指定用户安装系统中已存在的应用包。',
     'Install an already present package for the selected user.'),
    ('pm', 'clear', 'adb shell pm clear [--user ID] [--cache-only] PACKAGE\nadb shell pm uninstall [-k] [--user ID] PACKAGE',
     '`clear` 删除应用数据；`--cache-only` 只清缓存。`uninstall --user` 从指定用户卸载。',
     '`clear` removes app data; `--cache-only` clears only cache. `uninstall --user` removes the app for the selected user.'),
    ('pm', 'enable', 'adb shell pm enable [--user ID] PACKAGE_OR_COMPONENT\nadb shell pm disable-user [--user ID] PACKAGE_OR_COMPONENT',
     '启用或按用户禁用应用 / 组件。',
     'Enable or disable an app / component for a user.'),
    ('pm', 'permissions', 'adb shell pm grant [--user ID] PACKAGE PERMISSION\nadb shell pm revoke [--user ID] PACKAGE PERMISSION',
     '授予 / 撤销可变更的权限；不能任意授予签名级权限。',
     'Grant / revoke changeable permissions; does not grant arbitrary signature permissions.'),
    ('pm', 'resolve', 'adb shell pm resolve-activity [--brief] [--user ID] <INTENT>\nadb shell pm query-activities [--components] [--user ID] <INTENT>',
     '解析默认 Activity，或列出所有匹配的 Activity。',
     'Resolve the default activity or list matching activities.'),
    ('pm', 'app-links', 'adb shell pm get-app-links [--user ID] [PACKAGE]\nadb shell pm verify-app-links [--re-verify] [PACKAGE]',
     '查看域名验证状态，或重新请求 App Links 验证。',
     'Inspect domain verification state or request App Links verification again.'),

    ('am', 'start', 'adb shell am start [-W] [-S] [-D] [--user ID] <INTENT>',
     '`start` 即 `start-activity`。`-W` 等待启动结果；`-S` 先停止目标应用；`-D` 启用调试。',
     '`start` aliases `start-activity`. `-W`: wait for launch; `-S`: stop the target first; `-D`: enable debugging.'),
    ('am', 'service', 'adb shell am start-service [--user ID] <INTENT>\nadb shell am start-foreground-service [--user ID] <INTENT>\nadb shell am stop-service [--user ID] <INTENT>',
     '启动普通 / 前台 Service，或停止 Service；仍受系统后台执行规则限制。',
     'Start a normal / foreground service or stop a service. Background execution restrictions still apply.'),
    ('am', 'broadcast', 'adb shell am broadcast [--user ID|all|current]\n    [--receiver-permission PERMISSION] <INTENT>',
     '发送广播；可要求接收方具备指定权限。',
     'Send a broadcast, optionally requiring a permission from receivers.'),
    ('am', 'instrument', 'adb shell am instrument [-w] [-r] [-e KEY VALUE]\n    [--user ID] [--no-window-animation] COMPONENT',
     '运行 instrumentation。`-w` 等待结束；`-r` 输出原始结果；`-e` 传测试参数。',
     'Run instrumentation. `-w`: wait; `-r`: raw results; `-e`: test arguments.'),
    ('am', 'stop', 'adb shell am force-stop [--user ID|all|current] PACKAGE\nadb shell am kill [--user ID|all|current] PACKAGE',
     '`force-stop` 强制停止应用；`kill` 仅终止系统判断可以安全结束的进程。',
     '`force-stop` stops the app; `kill` only terminates processes considered safe to kill.'),
    ('am', 'debug', 'adb shell am set-debug-app [-w] [--persistent] PACKAGE\nadb shell am clear-debug-app',
     '设置 / 清除调试目标；`-w` 等待调试器，`--persistent` 持久保存设置。',
     'Set / clear the debug app. `-w`: wait for a debugger; `--persistent`: retain the setting.'),
    ('am', 'profile', 'adb shell am profile start [--sampling MICROSECONDS] PROCESS FILE\nadb shell am profile stop PROCESS\nadb shell am dumpheap [-n] [-g] PROCESS FILE',
     '采集方法 profile 或堆转储；`-n` 转储 native heap，`-g` 在转储前执行 GC。',
     'Collect a method profile or heap dump. `-n`: native heap; `-g`: run GC first.'),
    ('am', 'users', 'adb shell am get-current-user\nadb shell am switch-user ID\nadb shell am start-user [-w] ID\nadb shell am stop-user [-w] [-f] ID',
     '查询、切换、启动或停止用户；`-w` 等待完成，`-f` 即使父用户不可停止也强制停止目标用户。',
     'Query, switch, start, or stop users. `-w`: wait; `-f`: force the stop even if the parent user cannot be stopped.'),

    ('intent', 'target', '-a ACTION  -d URI  -t MIME  -c CATEGORY\n-n PACKAGE/CLASS  -p PACKAGE',
     '指定 action、数据、类型、类别、组件或包；`-c` 可重复。用于上面的 `<INTENT>`。',
     'Action, data, MIME type, category, component, or package. Repeat `-c` for multiple categories; use in `<INTENT>` above.'),
    ('intent', 'extras', '--es KEY TEXT  --esn KEY  --ez KEY BOOL\n--ei KEY INT  --el KEY LONG  --ef KEY FLOAT  --ed KEY DOUBLE\n--eu KEY URI  --ecn KEY PACKAGE/CLASS',
     '添加字符串、null、布尔、数字、URI 或 ComponentName extra；`-e` 等同 `--es`。',
     'Add string, null, boolean, numeric, URI, or ComponentName extras. `-e` aliases `--es`.'),
    ('intent', 'arrays', '--eia KEY 1,2  --ela KEY 1,2  --efa KEY 1.0,2.0\n--eda KEY 1.0,2.0  --esa KEY a,b',
     '数组 extra；对应 List 形式为 `--eial/--elal/--efal/--edal/--esal`。字符串中的逗号用 `\\,` 转义，并处理好 Shell 引号。',
     'Array extras; List forms: `--eial/--elal/--efal/--edal/--esal`. Escape embedded string commas as `\\,` and quote for the shell.'),
    ('intent', 'flags', '-f FLAGS  --activity-clear-top\n--activity-clear-task  --activity-single-top',
     '`-f` 指定 Intent flags，例如 `-f 0x10000000` 设置 NEW_TASK；其余选项控制 Activity 任务栈。',
     '`-f` sets Intent flags, e.g. `-f 0x10000000` sets NEW_TASK. Other options control activity task behavior.'),
    ('intent', 'uri-permissions', '--grant-read-uri-permission  --grant-write-uri-permission\n--grant-persistable-uri-permission  --grant-prefix-uri-permission',
     '授予接收方 URI 读写、可持久化或前缀权限；实际授权仍受 provider 规则限制。',
     'Grant URI read, write, persistable, or prefix permissions, subject to provider rules.'),

    ('environment', 'serial-env', 'ANDROID_SERIAL',
     '默认设备序列号；命令行 `-s` 可覆盖。',
     'Default device serial; overridden by `-s`.'),
    ('environment', 'server-env', 'ADB_SERVER_SOCKET\nANDROID_ADB_SERVER_ADDRESS  ANDROID_ADB_SERVER_PORT',
     '指定 server socket 或地址 / 端口；没有 `-H/-P/-L` 时才读取 `ADB_SERVER_SOCKET`。',
     'Server socket or host / port. `ADB_SERVER_SOCKET` is read only when `-H/-P/-L` are absent.'),
    ('environment', 'logs-env', 'ADB_TRACE  ANDROID_LOG_TAGS',
     '`ADB_TRACE` 为客户端日志类别，如 `adb,usb,transport` 或 `all`；`ANDROID_LOG_TAGS` 为默认 Logcat 过滤器。',
     '`ADB_TRACE`: client log categories such as `adb,usb,transport` or `all`. `ANDROID_LOG_TAGS`: default Logcat filter.'),
    ('environment', 'usb-env', 'ADB_VENDOR_KEYS  ADB_LIBUSB  ADB_MDNS_AUTO_CONNECT',
     '指定 ADB 密钥路径、USB 后端（`1` 为 libusb，`0` 为内置）和自动连接的 mDNS 服务列表。',
     'ADB key paths, USB backend (`1`: libusb; `0`: built-in), and mDNS services eligible for automatic connection.'),
]

COMMAND_GROUPS = [
    ('session', '设备与服务', 'Devices and server'),
    ('network', '连接与转发', 'Connections and forwarding'),
    ('files', '文件与 Shell', 'Files and shell'),
    ('install', '应用安装', 'App installation'),
    ('diagnostics', '日志与诊断', 'Logs and diagnostics'),
    ('device', '系统控制', 'System control'),
]


def inline(text):
    return re.sub(r'`([^`]+)`', lambda m: '<code>' + m[1] + '</code>', escape(text))


def entries(group, lang):
    en = lang == 'en'
    rows = []
    for category, ident, syntax, zh, english in ENTRIES:
        if category != group:
            continue
        rows.append(f'''<div class="man-entry" id="{lang}-{group}-{ident}"><dt><code>{escape(syntax)}</code><button type="button" data-man-copy aria-label="{'Copy syntax' if en else '复制语法'}: {escape(syntax.splitlines()[0], quote=True)}">{'Copy' if en else '复制'}</button></dt><dd>{inline(english if en else zh)}</dd></div>''')
    return '<dl class="man-entries">' + ''.join(rows) + '</dl>'


def section(key, scope, zh, en_title, content, lang, note=''):
    title = en_title if lang == 'en' else zh
    note_html = f'<p class="man-note">{inline(note)}</p>' if note else ''
    return f'<section class="man-section" data-man-scope="{scope}"><h2 id="{lang}-{key}">{title}</h2>{note_html}{content}</section>'


def body(lang):
    en = lang == 'en'
    title = 'ADB Command Manual' if en else 'ADB 命令手册'
    lead = 'Device connections, files, app management, and debugging; with common pm / am options.' if en else '设备连接、文件传输、应用管理与调试，附 pm / am 常用选项。'
    count = len(ENTRIES)
    search = 'Search commands or options…' if en else '搜索命令或参数…'
    scopes = [('all', '全部', 'All'), ('adb', 'ADB', 'ADB'), ('pm', 'PM', 'PM'), ('am', 'AM', 'AM'), ('intent', 'Intent', 'Intent'), ('environment', '环境变量', 'Environment')]
    options = ''.join(f'<option value="{key}">{english if en else zh}</option>' for key, zh, english in scopes)
    toolbar = f'''<div class="man-toolbar"><label class="man-search"><span class="man-sr-only">{search}</span><input data-man-search type="search" placeholder="{search}"></label><label><span class="man-sr-only">{'Scope' if en else '范围'}</span><select data-man-scope>{options}</select></label><button type="button" data-man-reset>{'Reset' if en else '重置'}</button><button type="button" data-man-print>{'Print / PDF' if en else '打印 / PDF'}</button><output data-man-count aria-live="polite">{count} / {count}</output></div><p class="man-empty" hidden>{'No matches.' if en else '没有匹配的条目。'}</p><p class="man-sr-only" data-man-status role="status"></p>'''
    synopsis = '<pre class="man-synopsis"><code>adb [GLOBAL_OPTIONS] COMMAND [ARGS]\nadb shell pm COMMAND [OPTIONS]\nadb shell am COMMAND [OPTIONS] [&lt;INTENT&gt;]</code></pre>'
    synopsis_note = 'ADB runs on the host; pm and am run on Android. Uppercase words are placeholders; [] means optional, | alternatives, and ... repetition.' if en else 'ADB 在主机执行，pm / am 在 Android 设备执行。大写单词为占位符；[] 表示可选，| 表示择一，... 表示可重复。'
    header = f'<div class="man-intro"><h2 id="{lang}-synopsis">{"SYNOPSIS" if en else "用法 · SYNOPSIS"}</h2>{synopsis}<p class="man-note">{synopsis_note}</p></div>'
    output = [section('options', 'adb', '全局选项 · OPTIONS', 'OPTIONS', entries('options', lang), lang)]
    command_html = ''.join(f'<div class="man-group"><h3 id="{lang}-commands-{key}">{english if en else zh}</h3>{entries(key, lang)}</div>' for key, zh, english in COMMAND_GROUPS)
    output.append(section('commands', 'adb', '主命令 · COMMANDS', 'COMMANDS', command_html, lang))
    for key, zh, english, note_zh, note_en in [
        ('pm', '包管理 · PM', 'PACKAGE MANAGER · PM', '', ''),
        ('am', '运行管理 · AM', 'ACTIVITY MANAGER · AM', '', ''),
        ('intent', 'Intent 参数 · INTENT', 'INTENT', '以下参数可组合传给接受 `<INTENT>` 的命令。', 'Combine these arguments in commands that accept `<INTENT>`.'),
        ('environment', '环境变量 · ENVIRONMENT', 'ENVIRONMENT', '', ''),
    ]:
        output.append(section(key, key, zh, english, entries(key, lang), lang, note_en if en else note_zh))
    links = [('adb.1.md', 'adb(1)'), ('pm.java', 'pm'), ('am.java', 'am'), ('Intent.java', 'Intent'), ('ArtShellCommand.java', 'ART'), ('domain.java', 'App Links')]
    sources = ' · '.join(f'<a href="{escape(SOURCES[file]["url"])}" target="_blank" rel="noopener">{label}</a>' for file, label in links)
    more = 'Full options on your device: `adb help`, `adb shell pm help`, `adb shell am help`. Based on AOSP Android 16; availability depends on Platform-Tools and the device build.' if en else '完整参数以本机 `adb help`、设备 `adb shell pm help` / `adb shell am help` 为准。参考 AOSP Android 16；可用选项取决于 Platform-Tools 和设备系统。'
    footer = f'''<footer class="man-footer"><h2 id="{lang}-see-also">{'SEE ALSO' if en else '参考 · SEE ALSO'}</h2><p>{inline(more)}</p><p>{sources} · <a href="cheatsheet-adb.html">{'Command examples' if en else '命令示例'}</a></p><p class="man-credit">AOSP · <a href="../assets/cheatsheets/adb-reference/NOTICE.txt">NOTICE</a> · <a href="../assets/cheatsheets/adb-reference/LICENSE-2.0.txt">Apache 2.0</a></p></footer>'''
    return f'<div class="lang-{lang}"><article class="man-sheet" data-language="{lang}"><h1>{title}</h1><p class="man-lead">{lead}</p>{toolbar}{header}{"".join(output)}{footer}</article></div>'


def main():
    keys = [(group, ident) for group, ident, *_ in ENTRIES]
    assert len(keys) == len(set(keys))
    metadata = {
        'title': 'ADB 命令手册', 'title_en': 'ADB Command Manual',
        'slug': 'cheatsheet-adb-reference', 'date': '2026-11-03',
        'tags': 'ADB, Android, PM, AM, Cheatsheet', 'tags_en': 'ADB, Android, PM, AM, Cheatsheet',
        'reading': '命令手册', 'reading_en': 'Command manual',
        'summary': 'man page 风格的 ADB 命令手册：全局选项、主命令、pm / am、Intent 与环境变量，支持搜索、复制和打印。',
        'summary_en': 'A concise man-style ADB reference: global options, commands, pm / am, Intent arguments, and environment variables, with search, copy, and print.',
        'series': 'cheatsheets', 'series_title': 'Cheatsheets', 'series_title_en': 'Cheatsheets', 'series_order': '11',
    }
    meta = '\n'.join(f'<meta name="post:{key}" content="{escape(value, quote=True)}">' for key, value in metadata.items())
    html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ADB 命令手册</title>
{meta}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/cheatsheets/adb-reference/reference.css?v=man-2">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/cheatsheets/adb-reference/reference.js?v=man-2" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">{body('zh')}{body('en')}</main></div></body></html>\n'''
    path = ROOT / 'posts/cheatsheet-adb-reference.html'
    path.write_text(html)
    print(f'Wrote {path}: {len(ENTRIES)} entries / {len(html.encode()):,} bytes')


if __name__ == '__main__':
    main()
