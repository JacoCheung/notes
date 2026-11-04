#!/usr/bin/env python3
"""Build the ADB reference using the compact Termux sheet's CSS and interactions."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AOSP = 'https://android.googlesource.com/platform/'
SOURCES = {
    'adb': AOSP + 'packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md',
    'guide': 'https://developer.android.com/tools/adb',
    'logcat': 'https://developer.android.com/tools/logcat',
    'dumpsys': 'https://developer.android.com/tools/dumpsys',
    'brew': 'https://formulae.brew.sh/cask/android-platform-tools',
    'termux': 'https://github.com/termux/termux-packages/blob/master/packages/android-tools/build.sh',
    'pm': AOSP + 'frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/PackageManagerShellCommand.java',
    'input': AOSP + 'frameworks/base/+/refs/heads/main/services/core/java/com/android/server/input/InputShellCommand.java',
    'wm': AOSP + 'frameworks/base/+/refs/heads/main/services/core/java/com/android/server/wm/WindowManagerShellCommand.java',
    'settings': AOSP + 'frameworks/base/+/refs/heads/main/packages/SettingsProvider/src/com/android/providers/settings/SettingsService.java',
    'runas': AOSP + 'system/core/+/refs/heads/main/run-as/run-as.cpp',
    'toybox': AOSP + 'external/toybox/+/refs/heads/main/toys/',
    'getprop': AOSP + 'system/core/+/refs/heads/main/toolbox/getprop.cpp',
}
GROUPS = [
    ('basics', '安装与设备选择', 'Setup and selection'),
    ('wireless', '无线连接', 'Wireless debugging'),
    ('files', '文件与存储', 'Files and storage'),
    ('packages', '应用安装', 'App installation'),
    ('activity', '应用运行', 'App execution'),
    ('logs', 'Logcat 日志', 'Logcat'),
    ('inspect', '系统诊断', 'Diagnostics'),
    ('screen', '屏幕与输入', 'Screen and input'),
    ('ports', '端口与网络', 'Ports and networking'),
    ('settings', '权限与设置', 'Permissions and settings'),
    ('lifecycle', '服务与重启', 'Server and reboot'),
    ('debug', '开发调试', 'Development tools'),
]

# Category, stable ID, purpose zh/en, copyable example, note zh/en, source key.
COMMANDS = [
    ('basics', 'install-mac', 'macOS 安装', 'Install on macOS',
     'brew install --cask android-platform-tools',
     '需先安装 Homebrew', 'Requires Homebrew', 'brew'),
    ('basics', 'install-termux', 'Termux 安装', 'Install in Termux',
     'pkg install android-tools',
     '安装 ADB 客户端；不等于已取得手机调试授权', 'Installs the ADB client; device authorization is separate', 'termux'),
    ('basics', 'help', '版本与帮助', 'Version and help',
     'adb version\nadb help', '', '', 'adb'),
    ('basics', 'devices', '列出连接设备', 'List connected devices',
     'adb devices -l',
     'USB 需开启调试；unauthorized 时解锁手机确认授权', 'Enable USB debugging; unlock and authorize if unauthorized', 'guide'),
    ('basics', 'serial', '指定设备', 'Select a device',
     'adb -s SERIAL shell',
     '用 devices 返回的序列号替换 SERIAL；-s 位于子命令前', 'Replace SERIAL with a listed serial; -s precedes the subcommand', 'adb'),
    ('basics', 'transport', '按连接类型选择', 'Select by transport',
     'adb -d get-state\nadb -e get-state',
     '-d USB；-e TCP/IP；同类型有多台时改用 -s', '-d USB; -e TCP/IP; use -s when several match', 'adb'),

    ('wireless', 'pair', '无线配对', 'Pair wirelessly',
     'adb pair 192.168.1.20:37001',
     'Android 11+ 手机；使用配对弹窗端口，按提示输入配对码', 'Android 11+ phones; use the pairing-dialog port and enter its code', 'guide'),
    ('wireless', 'connect', '连接无线设备', 'Connect wirelessly',
     'adb connect 192.168.1.20:38001',
     '使用无线调试主页的连接端口，与配对端口不同', 'Use the connection port on the Wireless debugging screen, not the pairing port', 'guide'),
    ('wireless', 'mdns', '发现无线调试服务', 'Discover wireless services',
     'adb mdns check\nadb mdns services',
     '通常要求同一网络；服务可见性取决于 mDNS', 'Usually the same network; discovery depends on mDNS', 'adb'),
    ('wireless', 'disconnect', '断开指定无线设备', 'Disconnect a wireless device',
     'adb disconnect 192.168.1.20:38001',
     '不带地址会断开所有 TCP/IP 设备', 'Omitting the address disconnects all TCP/IP devices', 'adb'),
    ('wireless', 'tcpip', '传统 TCP 调试', 'Legacy TCP debugging',
     'adb tcpip 5555\nadb connect 192.168.1.20:5555',
     '通常先经 USB 授权；仅可信网络，不是 TLS 无线配对模式', 'Usually authorize over USB first; trusted network only, not TLS pairing', 'guide'),
    ('wireless', 'usb', '恢复 USB 监听', 'Return to USB listening',
     'adb usb',
     '重启目标 adbd 的监听；传统 TCP 调试完成后使用', 'Restarts target adbd listening; use after legacy TCP debugging', 'adb'),

    ('files', 'push', '上传文件', 'Upload a file',
     'adb push ./note.txt /sdcard/Download/',
     '本机 → 设备；目录也可传输', 'Host → device; directories are also supported', 'adb'),
    ('files', 'pull', '下载文件', 'Download a file',
     'adb pull /sdcard/Download/note.txt ./note.txt',
     '设备 → 本机；-a 保留时间与权限模式', 'Device → host; -a preserves timestamps and mode', 'adb'),
    ('files', 'push-sync', '增量上传', 'Upload newer files',
     'adb push --sync ./assets /sdcard/Download/',
     '按修改时间跳过未更新文件；不清理远端多余文件', 'Skips files by modification time; does not delete extra remote files', 'adb'),
    ('files', 'list-files', '列目录', 'List files',
     'adb shell ls -lah /sdcard/Download',
     '文件访问仍受设备权限限制', 'Device filesystem permissions still apply', 'toybox'),
    ('files', 'mkdir', '创建目录', 'Create a directory',
     'adb shell mkdir -p /sdcard/Download/adb-demo', '', '', 'toybox'),
    ('files', 'storage', '存储占用', 'Storage usage',
     'adb shell df -h /sdcard\nadb shell du -sh /sdcard/Download', '', '', 'toybox'),
    ('files', 'remove-file', '删除指定文件', 'Delete a specific file',
     'adb shell rm /sdcard/Download/adb-demo/note.txt',
     '直接删除；执行前确认设备路径', 'Deletes the file; verify the device path first', 'toybox'),

    ('packages', 'install', '安装 APK', 'Install an APK',
     'adb install ./app.apk',
     '-t 允许测试 APK；-g 授予运行时权限', '-t allows test APKs; -g grants runtime permissions', 'adb'),
    ('packages', 'update', '覆盖安装', 'Replace an installed app',
     'adb install -r ./app.apk',
     '保留应用数据；签名须兼容，不能任意降级', 'Preserves data; signatures must match, downgrade rules still apply', 'adb'),
    ('packages', 'split-apk', '安装 split APK', 'Install split APKs',
     'adb install-multiple base.apk split_config.arm64_v8a.apk',
     '同一应用；需包含与设备匹配的全部必需 splits', 'One app; include every required split matching the device', 'adb'),
    ('packages', 'uninstall', '卸载应用', 'Uninstall an app',
     'adb uninstall com.example.app',
     '默认删除数据；-k 保留数据与缓存', 'Deletes data by default; -k keeps data and cache', 'adb'),
    ('packages', 'clear', '清空应用数据', 'Clear app data',
     'adb shell pm clear com.example.app',
     '保留 APK；删除应用数据与登录状态', 'Keeps the APK; removes app data and sign-in state', 'pm'),
    ('packages', 'list-packages', '列出已安装应用', 'List installed apps',
     'adb shell pm list packages -3',
     '-3 第三方；-s 系统应用；-f 显示 APK 路径', '-3 third-party; -s system; -f includes APK paths', 'pm'),
    ('packages', 'apk-path', '查询 APK 路径', 'Locate installed APKs',
     'adb shell pm path com.example.app',
     'split 安装会返回多个路径；下载需逐个 pull', 'Split installs return multiple paths; pull each one if needed', 'pm'),

    ('activity', 'shell', '进入设备 Shell', 'Open a device shell',
     'adb shell',
     'exit 退出；设备上的 shell 用户，不等于 root', 'exit leaves the shell; the shell user is not root', 'adb'),
    ('activity', 'launch', '启动 Activity', 'Launch an Activity',
     'adb shell am start -W -n com.example.app/.MainActivity',
     '-W 等待启动结果；替换为实际组件名', '-W waits for launch results; use the actual component name', 'guide'),
    ('activity', 'open-url', '打开 URL', 'Open a URL',
     'adb shell am start -a android.intent.action.VIEW -d https://example.com/',
     '由设备上的匹配应用处理', 'Handled by a matching app on the device', 'guide'),
    ('activity', 'force-stop', '停止指定应用', 'Force-stop an app',
     'adb shell am force-stop com.example.app',
     '停止该包相关进程，不卸载、不清数据', 'Stops the package without uninstalling or clearing its data', 'guide'),
    ('activity', 'broadcast', '发送应用广播', 'Send an app broadcast',
     'adb shell am broadcast -a com.example.app.PING -p com.example.app',
     '受组件导出与广播权限限制', 'Receiver export and broadcast permissions apply', 'guide'),
    ('activity', 'instrument', '运行 instrumentation 测试', 'Run instrumentation tests',
     'adb shell am instrument -w com.example.app.test/androidx.test.runner.AndroidJUnitRunner',
     '需已安装测试 APK；替换测试包与 runner', 'Install the test APK first; use its package and runner', 'guide'),

    ('logs', 'logcat', '实时日志', 'Stream logs',
     'adb logcat -v threadtime',
     'Ctrl+C 停止；包含时间、PID 与 TID', 'Ctrl+C stops; includes timestamps, PID, and TID', 'logcat'),
    ('logs', 'log-tags', '按 tag 与级别筛选', 'Filter tags and priorities',
     "adb logcat MyApp:D '*:S'",
     'MyApp ≥ Debug；其他静默；星号需引号', 'MyApp at Debug or higher; silence others; quote the wildcard', 'logcat'),
    ('logs', 'log-pid', '按进程筛选', 'Filter a process',
     'adb logcat --pid=12345',
     '12345 换成 pidof 返回的 PID；重启应用后需更新', 'Use the PID returned by pidof; refresh after app restart', 'logcat'),
    ('logs', 'log-save', '导出当前日志', 'Save current logs',
     'adb logcat -d -v threadtime > logcat.txt',
     '-d 导出后退出；文件保存在本机', '-d dumps and exits; the file is saved on the host', 'logcat'),
    ('logs', 'log-crash', '查看崩溃缓冲区', 'Read the crash buffer',
     'adb logcat -b crash -d',
     '-b all 选择所有可访问缓冲区', '-b all selects all accessible buffers', 'logcat'),
    ('logs', 'log-clear', '清空日志缓冲区', 'Clear log buffers',
     'adb logcat -c',
     '清除选中缓冲区；先导出需要保留的日志', 'Clears selected buffers; export needed logs first', 'logcat'),

    ('inspect', 'bugreport', '导出诊断报告', 'Export a diagnostic report',
     'adb bugreport ./bugreport.zip',
     '输出在本机；报告可能含设备与应用信息', 'Saved on the host; may contain device and app information', 'adb'),
    ('inspect', 'services', '列出可诊断服务', 'List diagnostic services',
     'adb shell dumpsys -l',
     '指定服务可缩小输出范围', 'Specify a service to narrow the output', 'dumpsys'),
    ('inspect', 'battery', '电池与充电状态', 'Battery and charging state',
     'adb shell dumpsys battery', '', '', 'dumpsys'),
    ('inspect', 'memory', '应用内存', 'App memory usage',
     'adb shell dumpsys meminfo com.example.app',
     'PSS、堆与其他内存分类', 'PSS, heap, and other memory categories', 'dumpsys'),
    ('inspect', 'frames', '界面渲染统计', 'UI rendering statistics',
     'adb shell dumpsys gfxinfo com.example.app framestats',
     '受渲染路径与系统版本影响', 'Availability depends on rendering path and OS version', 'dumpsys'),
    ('inspect', 'processes', '查询应用 PID', 'Find an app PID',
     'adb shell pidof com.example.app',
     '应用需正在运行；子进程可能使用其他进程名', 'The app must be running; child processes may have different names', 'toybox'),
    ('inspect', 'top', 'CPU 与进程负载', 'CPU and process load',
     'adb shell top -b -n 1',
     '单次输出；可用选项以设备 top --help 为准', 'One snapshot; check device top --help for supported options', 'toybox'),

    ('screen', 'screenshot', '截图到本机', 'Capture a screenshot to the host',
     'adb exec-out screencap -p > screen.png',
     'PNG 二进制输出；此重定向示例适用于 Bash / Zsh', 'Binary PNG output; this redirection is for Bash / Zsh', 'guide'),
    ('screen', 'record', '录屏并下载', 'Record and download video',
     'adb shell screenrecord --time-limit 15 /sdcard/demo.mp4\nadb pull /sdcard/demo.mp4 .',
     '15 秒；受保护画面可能无法录制', '15 seconds; protected content may not be captured', 'guide'),
    ('screen', 'key', '发送按键', 'Send a key event',
     'adb shell input keyevent KEYCODE_HOME',
     '常用：KEYCODE_BACK / KEYCODE_ENTER / KEYCODE_POWER', 'Also: KEYCODE_BACK / KEYCODE_ENTER / KEYCODE_POWER', 'input'),
    ('screen', 'tap', '点击屏幕', 'Tap the screen',
     'adb shell input tap 300 500',
     '坐标单位为像素；按当前分辨率调整', 'Pixel coordinates; adjust for the current resolution', 'input'),
    ('screen', 'swipe', '滑动手势', 'Swipe gesture',
     'adb shell input swipe 300 1000 300 300 400',
     '起点 x/y → 终点 x/y；最后一项为毫秒', 'Start x/y → end x/y; final argument is milliseconds', 'input'),
    ('screen', 'text', '输入文本', 'Enter text',
     'adb shell input text hello%sworld',
     '%s 表示空格；适合 ASCII，不保证任意 Unicode', '%s represents a space; suitable for ASCII, not arbitrary Unicode', 'input'),
    ('screen', 'display', '查询分辨率与密度', 'Inspect display size and density',
     'adb shell wm size\nadb shell wm density',
     '查看物理值与 override；size reset / density reset 清除覆盖', 'Shows physical and override values; size reset / density reset clear overrides', 'wm'),

    ('ports', 'forward', '本机端口 → 设备', 'Host port → device',
     'adb forward tcp:8081 tcp:8080',
     '访问本机 8081 → 设备 8080；本机指 ADB server 所在主机', 'Host 8081 → device 8080; host means the ADB server machine', 'adb'),
    ('ports', 'reverse', '设备端口 → 本机', 'Device port → host',
     'adb reverse tcp:8080 tcp:8000',
     '设备访问 localhost:8080 → ADB server 主机的 8000', 'Device localhost:8080 → port 8000 on the ADB server host', 'adb'),
    ('ports', 'list-forwards', '列出端口映射', 'List port mappings',
     'adb forward --list\nadb reverse --list', '', '', 'adb'),
    ('ports', 'remove-forward', '移除正向映射', 'Remove a forward mapping',
     'adb forward --remove tcp:8081',
     '参数是本机监听端口', 'Use the host listening port', 'adb'),
    ('ports', 'remove-reverse', '移除反向映射', 'Remove a reverse mapping',
     'adb reverse --remove tcp:8080',
     '参数是设备监听端口', 'Use the device listening port', 'adb'),
    ('ports', 'network', '查看地址与路由', 'Inspect addresses and routes',
     'adb shell ip addr show wlan0\nadb shell ip route',
     '接口名按设备调整；可见信息受系统权限限制', 'Adjust the interface name; system permissions restrict visibility', 'toybox'),

    ('settings', 'properties', '系统版本与 API level', 'OS version and API level',
     'adb shell getprop ro.build.version.release\nadb shell getprop ro.build.version.sdk',
     'getprop 不带键名可列出可见属性', 'getprop without a key lists visible properties', 'getprop'),
    ('settings', 'setting-read', '读取系统设置', 'Read a system setting',
     'adb shell settings get system screen_off_timeout',
     '毫秒；另有 secure / global 命名空间', 'Milliseconds; secure / global are other namespaces', 'settings'),
    ('settings', 'setting-write', '修改熄屏超时', 'Change screen timeout',
     'adb shell settings put system screen_off_timeout 600000',
     '10 分钟；先记录原值，恢复时写回原值', '10 minutes; record and restore the original value', 'settings'),
    ('settings', 'grant', '授予运行时权限', 'Grant a runtime permission',
     'adb shell pm grant com.example.app android.permission.CAMERA',
     '应用须已声明该可变更权限；不适用于任意特殊权限', 'The app must declare an eligible permission; not for arbitrary special access', 'pm'),
    ('settings', 'revoke', '撤销运行时权限', 'Revoke a runtime permission',
     'adb shell pm revoke com.example.app android.permission.CAMERA',
     '系统固定等权限不能任意撤销', 'System-fixed and other restricted permissions cannot be freely revoked', 'pm'),
    ('settings', 'disable', '对用户停用应用', 'Disable an app for a user',
     'adb shell pm disable-user --user 0 com.example.app',
     '用户 0；执行前确认目标，部分系统包禁止停用', 'User 0; verify the package, some system apps cannot be disabled', 'pm'),
    ('settings', 'enable', '恢复启用应用', 'Re-enable an app',
     'adb shell pm enable --user 0 com.example.app',
     '与 disable-user 使用同一用户和包名', 'Use the same user and package as disable-user', 'pm'),

    ('lifecycle', 'start-server', '启动本机 ADB server', 'Start the host ADB server',
     'adb start-server',
     '通常会自动启动；默认本机端口 5037', 'Usually starts automatically; default host port 5037', 'adb'),
    ('lifecycle', 'kill-server', '停止本机 ADB server', 'Stop the host ADB server',
     'adb kill-server',
     '会中断使用该 server 的设备连接与调试会话', 'Interrupts device connections and debug sessions using this server', 'adb'),
    ('lifecycle', 'reconnect', '重连异常设备', 'Reconnect unavailable devices',
     'adb reconnect offline',
     '重置 offline / unauthorized 连接；仍需手机授权', 'Resets offline / unauthorized connections; authorization is still required', 'adb'),
    ('lifecycle', 'wait', '等待设备连接', 'Wait for a device connection',
     'adb wait-for-device',
     '仅表示 adbd 已连接，不代表 Android 开机完成', 'Waits for adbd, not for Android to finish booting', 'adb'),
    ('lifecycle', 'boot-state', '检查开机完成状态', 'Check boot completion',
     'adb shell getprop sys.boot_completed',
     '通常为 1 时已完成开机；此命令不主动等待', 'Usually 1 after boot completes; this command does not wait', 'getprop'),
    ('lifecycle', 'reboot', '重启设备', 'Reboot the device',
     'adb reboot',
     '立即重启；当前设备会话会断开', 'Reboots immediately; current device sessions disconnect', 'adb'),
    ('lifecycle', 'recovery', '重启到 Recovery', 'Reboot to recovery',
     'adb reboot recovery',
     '恢复模式；支持情况因设备而异', 'Recovery mode; support varies by device', 'adb'),
    ('lifecycle', 'bootloader', '重启到 Bootloader', 'Reboot to bootloader',
     'adb reboot bootloader',
     '之后常需使用 fastboot；fastboot 是另一套工具', 'Usually use fastboot afterward; it is a separate tool', 'adb'),

    ('debug', 'run-as', '访问可调试应用目录', 'Access a debuggable app directory',
     'adb shell run-as com.example.app ls files',
     '仅限允许 run-as 的 debuggable 应用，不是任意应用 root 访问', 'Requires an eligible debuggable app; not root access to arbitrary apps', 'runas'),
    ('debug', 'jdwp', '列出 Java 调试进程', 'List Java debug processes',
     'adb jdwp',
     '输出提供 JDWP transport 的进程 PID', 'Lists PIDs exposing JDWP transport', 'adb'),
    ('debug', 'jdwp-forward', '转发 JDWP 调试端口', 'Forward a JDWP debug port',
     'adb forward tcp:8700 jdwp:12345',
     '12345 换成 adb jdwp 返回的 PID；本机调试器连接 8700', 'Use a PID from adb jdwp; attach the host debugger to 8700', 'adb'),
    ('debug', 'root', '以 root 重启 adbd', 'Restart adbd as root',
     'adb root',
     '仅支持允许 root 的开发镜像；普通零售 user 构建通常拒绝', 'Requires a root-capable development image; retail user builds usually reject it', 'adb'),
    ('debug', 'unroot', '恢复非 root adbd', 'Return adbd to non-root mode',
     'adb unroot',
     '会重启 adbd 并短暂断开连接', 'Restarts adbd and briefly disconnects', 'adb'),
    ('debug', 'features', '查询双方支持的特性', 'Inspect supported features',
     'adb features\nadb host-features',
     'features 为主机与设备共同支持；host-features 只查主机', 'features is the common set; host-features checks only the host', 'adb'),
]


def codeblock(text, lang, source=''):
    lines = text.split('\n')
    first = escape(lines[0])
    if source:
        first = f'<a class="command-name" href="{source}" target="_blank" rel="noopener" title="{"Reference" if lang == "en" else "参考文档"}">{first}</a>'
    code = '\n'.join([first] + [escape(line) for line in lines[1:]])
    return f'<div class="termux-code"><pre><code>{code}</code></pre><button type="button" class="termux-copy">{"Copy" if lang == "en" else "复制"}</button></div>'


def command_groups(lang):
    en = lang == 'en'
    output = []
    for key, zh, english in GROUPS:
        rows = []
        for group, ident, purpose_zh, purpose_en, example, note_zh, note_en, source in COMMANDS:
            if group != key:
                continue
            note = note_en if en else note_zh
            note_html = f'<p class="command-note">{escape(note)}</p>' if note else ''
            rows.append(f'<div class="command-row" data-command="{ident}"><div class="command-purpose">{escape(purpose_en if en else purpose_zh)}</div>{codeblock(example,lang,SOURCES[source])}{note_html}</div>')
        output.append(f'<section class="command-group" data-category="{key}" aria-labelledby="{lang}-adb-{key}"><header class="command-group-heading"><h2 id="{lang}-adb-{key}">{english if en else zh}</h2><span>{len(rows):02d}</span></header>{"".join(rows)}</section>')
    return '<div class="termux-grid">' + ''.join(output) + '</div>'


def body(lang):
    en = lang == 'en'
    count = len(COMMANDS)
    options = ''.join(f'<option value="{key}">{english if en else zh}</option>' for key,zh,english in GROUPS)
    title = 'ADB Command Cheatsheet' if en else 'ADB 命令速查'
    lead = f'{count} examples · {len(GROUPS)} categories · ADB + Android shell' if en else f'{count} 组常用指令 · {len(GROUPS)} 类用途 · ADB + Android Shell'
    setup = ('Run adb on your computer or in Termux; commands after shell run on the target device.' if en else 'adb 在电脑或 Termux 执行；shell 后的命令在目标设备上运行。')
    controls = f'''<div class="termux-toolbar"><label class="termux-search"><span class="termux-sr-only">{'Search commands' if en else '搜索命令'}</span><input type="search" data-termux-search placeholder="{'Search command, task, flag…' if en else '搜索命令、用途、参数…'}"></label><label><span class="termux-sr-only">{'Category' if en else '分类'}</span><select data-termux-category><option value="all">{'All categories' if en else '全部分类'}</option>{options}</select></label><button type="button" data-termux-reset>{'Reset' if en else '重置'}</button><button type="button" data-termux-print>{'Print / PDF' if en else '打印 / PDF'}</button><span class="termux-results" role="status" aria-live="polite">{count} / {count}</span></div><p class="termux-empty" hidden>{'No matching commands.' if en else '没有匹配的命令。'}</p>'''
    footer = ('''<span>Examples use Bash/Zsh. Replace sample IPs, ports, serials, packages, and paths.</span><span>Availability depends on Platform-Tools, Android, and device permissions.</span>''' if en else '''<span>示例采用 Bash/Zsh；IP、端口、序列号、包名和路径按实际替换。</span><span>命令支持取决于 Platform-Tools、Android 版本与设备权限。</span>''')
    links = f'''<a href="https://developer.android.com/tools/releases/platform-tools">Platform-Tools</a><a href="{SOURCES['guide']}">{'ADB guide' if en else 'ADB 官方说明'}</a><a href="{SOURCES['adb']}">{'Command reference' if en else '命令手册'}</a>'''
    return f'''<div class="lang-{lang}"><div class="termux-sheet adb-sheet" data-language="{lang}"><h1>{title}</h1><p class="lead">{lead}</p><div class="termux-setup"><span>{setup}</span></div>{controls}{command_groups(lang)}<footer class="termux-footer">{footer}<span>{links}</span></footer></div></div>'''


def main():
    names = [r[1] for r in COMMANDS]
    assert len(names) == len(set(names))
    assert {r[0] for r in COMMANDS} == {r[0] for r in GROUPS}
    count = len(COMMANDS)
    metadata = {
        'title':'ADB 命令速查','title_en':'ADB Command Cheatsheet',
        'slug':'cheatsheet-adb','date':'2026-11-03',
        'tags':'ADB, Android, CLI, Cheatsheet','tags_en':'ADB, Android, CLI, Cheatsheet',
        'reading':'速查表','reading_en':'Reference sheet',
        'summary':f'{count} 组 ADB 常用指令，覆盖无线连接、文件、应用、日志、截图录屏与端口转发，支持搜索、复制和打印。',
        'summary_en':f'{count} ADB examples covering wireless connections, files, apps, logs, screen capture, and port forwarding, with search, copy, and print controls.',
        'series':'cheatsheets','series_title':'Cheatsheets','series_title_en':'Cheatsheets','series_order':'10',
    }
    meta = '\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in metadata.items())
    page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ADB 命令速查</title>
{meta}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/cheatsheets/termux-api.css?v=compact-2">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/cheatsheets/termux-api.js?v=compact-2" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">
{body('zh')}{body('en')}
</main></div></body></html>\n'''
    path = ROOT/'posts/cheatsheet-adb.html'
    path.write_text(page)
    print(f'Wrote {path}: {count} entries / {len(GROUPS)} categories')


if __name__ == '__main__':
    main()
