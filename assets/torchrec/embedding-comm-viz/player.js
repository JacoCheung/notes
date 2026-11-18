import { createTimeline, rasterizeFrame } from './svg-timeline.js?v=6';
import { encodeGifFrames, GIF_EXPORT_LIMITS } from './gif-export.js';

const texts = {
  zh: {
    previous: '上一阶段', play: '播放', pause: '暂停', next: '下一阶段', stop: '停止并回到起点',
    speed: '播放速度', reverse: '倒放', loop: '循环播放', zoom: '原图尺寸',
    fullscreen: '全屏', exitFullscreen: '退出全屏', timeline: '动画进度',
    export: '导出', frame: '当前帧', original: '原图', cancel: '取消导出',
    loading: '正在加载动画…', ready: '动画已就绪。',
    loadFailed: '动画加载失败，请刷新页面重试。', exportFailed: '导出失败，请稍后重试或选择较小的 GIF 宽度。',
    pngBusy: '正在生成截图…', pngDone: '当前帧已导出为 PNG。', cancelled: 'GIF 导出已取消。',
    gifDone: '整段 GIF 已导出。', fullFailed: '浏览器未能进入全屏，可切换到原图尺寸查看。',
    controls: '动画播放控制', viewport: '原图尺寸下可横向滚动',
    state: name => `跳到 ${name} 布局`, step: name => `播放步骤 ${name}`,
    exporting: (n, total) => `正在导出 GIF：${n} / ${total} 帧`,
  },
  en: {
    previous: 'Previous stage', play: 'Play', pause: 'Pause', next: 'Next stage', stop: 'Stop and return to start',
    speed: 'Playback speed', reverse: 'Reverse', loop: 'Loop', zoom: 'Original size',
    fullscreen: 'Fullscreen', exitFullscreen: 'Exit fullscreen', timeline: 'Animation progress',
    export: 'Export', frame: 'current frame', original: 'original', cancel: 'Cancel export',
    loading: 'Loading animation…', ready: 'Ready.',
    loadFailed: 'The animation could not load. Refresh the page to retry.', exportFailed: 'Export failed. Retry or choose the smaller GIF width.',
    pngBusy: 'Rendering screenshot…', pngDone: 'Current frame exported as PNG.', cancelled: 'GIF export cancelled.',
    gifDone: 'Full GIF exported.', fullFailed: 'Fullscreen is unavailable. Switch to the original size to inspect the diagram.',
    controls: 'Animation controls', viewport: 'scroll horizontally at original size',
    state: name => `Jump to the ${name} layout`, step: name => `Play step ${name}`,
    exporting: (n, total) => `Exporting GIF: ${n} / ${total} frames`,
  },
};
// Messages that need no visible notice: the viewport already shows loading states.
const quiet = new Set(['loading', 'ready', 'loadFailed']);
const transient = new Set(['pngDone', 'gifDone', 'cancelled']);
const lang = () => document.documentElement.lang.startsWith('zh') ? 'zh' : 'en';
const t = () => texts[lang()];

// One player per figure. The markup names its SVG (data-src), its download
// name (data-name) and, per language, its title and the names of its stages.
async function setup(root) {
const $ = name => root.querySelector(`[data-${name}]`);
const own = name => root.dataset[name + (lang() === 'zh' ? 'Zh' : 'En')];
const phases = () => own('phases').split('|');
let timeline;
let time = 0;
let playing = false;
let rate = 1;
let direction = 1;
let stopAt = null;
let lastTick = null;
let frameRequest = 0;
let exportController = null;
let pngBusy = false;
let progress = null;
let statusKey = 'loading';
let noticeTimer = 0;
let stations = [];
const pressed = name => $(name).getAttribute('aria-pressed') === 'true';

function label(element, text) {
  element.setAttribute('aria-label', text);
  element.title = text;
}
function toggle(name) {
  const next = !pressed(name);
  $(name).setAttribute('aria-pressed', String(next));
  return next;
}
function status(key) {
  statusKey = key;
  clearTimeout(noticeTimer);
  $('export-status').textContent = t()[key];
  $('notice').hidden = quiet.has(key);
  if (transient.has(key)) noticeTimer = setTimeout(() => status('ready'), 4000);
}
function setMenu(open) {
  $('menu-list').hidden = !open;
  $('export').setAttribute('aria-expanded', String(open));
}
function syncControls() {
  const duration = timeline?.duration || Number($('scrubber').max);
  const clock = `${time.toFixed(2)} / ${duration.toFixed(2)} s`;
  label($('play'), t()[playing ? 'pause' : 'play']);
  $('play').setAttribute('aria-pressed', String(playing));
  $('time').textContent = clock;
  $('scrubber').value = time;
  $('scrubber').setAttribute('aria-valuetext', clock);
  $('scrubber').style.setProperty('--fill', `${time / duration * 100}%`);
  root.dataset.time = String(time);
  root.dataset.playing = String(playing);
  if (timeline) {
    const phase = phases()[timeline.phase(time)];
    if ($('stage').textContent !== phase) $('stage').textContent = phase;
  }
}
function localize() {
  root.querySelectorAll('[data-i18n]').forEach(element => { element.textContent = t()[element.dataset.i18n]; });
  root.querySelectorAll('[data-label]').forEach(element => label(element, t()[element.dataset.label]));
  for (const { node, kind, name, tip } of stations) {
    node.setAttribute('aria-label', t()[kind](name));
    tip.textContent = t()[kind](name);
  }
  $('controls').setAttribute('aria-label', t().controls);
  $('viewport').setAttribute('aria-label', `${own('title')}; ${t().viewport}`);
  label($('fullscreen'), document.fullscreenElement === root ? t().exitFullscreen : t().fullscreen);
  $('loading').textContent = t()[statusKey === 'loadFailed' ? 'loadFailed' : 'loading'];
  $('export-status').textContent = progress ? t().exporting(progress.completed, progress.total) : t()[statusKey];
  syncControls();
}
function pause() {
  playing = false;
  stopAt = null;
  lastTick = null;
  cancelAnimationFrame(frameRequest);
  frameRequest = 0;
  syncControls();
}
function seek(value) {
  time = Math.max(0, Math.min(timeline.duration, value));
  timeline.render(time);
  syncControls();
}
function tick(now) {
  if (!playing) return;
  const elapsed = lastTick === null ? 0 : (now - lastTick) / 1000;
  lastTick = now;
  let nextTime = time + elapsed * rate * direction;
  if (stopAt !== null && (direction > 0 ? nextTime >= stopAt : nextTime <= stopAt)) {
    seek(stopAt);
    pause();
    return;
  }
  if (nextTime > timeline.duration || nextTime < 0) {
    if (pressed('loop')) nextTime = ((nextTime % timeline.duration) + timeline.duration) % timeline.duration;
    else { seek(nextTime); pause(); return; }
  }
  seek(nextTime);
  frameRequest = requestAnimationFrame(tick);
}
function play() {
  if (playing || !timeline) return;
  if (direction > 0 && time >= timeline.duration) seek(0);
  if (direction < 0 && time <= 0) seek(timeline.duration);
  playing = true;
  lastTick = null;
  syncControls();
  frameRequest = requestAnimationFrame(tick);
}
// Play one step and stop on the layout it produces (or, reversed, the one it started from).
function playSpan(from, to) {
  pause();
  seek(direction > 0 ? from : to);
  stopAt = direction > 0 ? to : from;
  play();
}
function step(forward) {
  pause();
  const points = [...timeline.phaseTimes, timeline.duration];
  const target = forward ? points.find(value => value > time + 0.001) : points.findLast(value => value < time - 0.001);
  seek(target ?? (forward ? timeline.duration : 0));
}
// The titles in the figure are the stage navigation: a layout title jumps to
// that layout, a step title plays the step.
function bindStations() {
  $('ticks').replaceChildren(...timeline.phaseTimes.slice(1).map(at => {
    const mark = document.createElement('i');
    mark.style.setProperty('--at', String(at / timeline.duration));
    return mark;
  }));
  stations = [...timeline.svg.querySelectorAll('[data-nav]')].map(node => {
    const [kind, index] = node.getAttribute('data-nav').split(':');
    const at = timeline.phaseTimes[Number(index)];
    const until = timeline.phaseTimes[Number(index) + 1];
    const go = kind === 'state' ? () => { pause(); seek(at); } : () => playSpan(at, until);
    const tip = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    node.prepend(tip);
    node.setAttribute('role', 'button');
    node.setAttribute('tabindex', '0');
    node.addEventListener('click', go);
    node.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      go();
    });
    return { node, kind, tip, name: node.querySelector('text').textContent };
  });
}
function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function exportPng() {
  if (pngBusy || !timeline) return;
  pngBusy = true;
  $('png').disabled = true;
  const capturedTime = time;
  if (!exportController) status('pngBusy');
  try {
    const canvas = await rasterizeFrame(timeline, capturedTime, timeline.width);
    const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('PNG encoding failed')), 'image/png'));
    download(blob, `${root.dataset.name}-${capturedTime.toFixed(2)}s.png`);
    if (!exportController) status('pngDone');
  } catch (error) {
    console.error(error);
    if (!exportController) status('exportFailed');
  } finally {
    pngBusy = false;
    $('png').disabled = false;
  }
}
async function exportGif(width) {
  if (exportController || !timeline) return;
  const controller = new AbortController();
  exportController = controller;
  const capturedRate = rate, capturedDirection = direction;
  const height = Math.round(width * timeline.height / timeline.width);
  const seconds = timeline.duration / capturedRate;
  const frameCount = Math.min(270, Math.ceil(seconds * 15), Math.floor(GIF_EXPORT_LIMITS.maxTotalPixels / (width * height)));
  const gifButtons = root.querySelectorAll('[data-gif]');
  gifButtons.forEach(button => { button.disabled = true; });
  clearTimeout(noticeTimer);
  progress = { completed: 0, total: frameCount };
  $('export-status').textContent = t().exporting(0, frameCount);
  $('notice').hidden = false;
  $('cancel').hidden = false;
  $('progress').hidden = false;
  $('progress').value = 0;
  root.dataset.exporting = 'true';
  try {
    const bytes = await encodeGifFrames({
      width, height, frameCount, delayMs: seconds * 1000 / frameCount,
      signal: controller.signal,
      renderFrame: async index => {
        const time = capturedDirection > 0 ? index / frameCount * timeline.duration : timeline.duration - index / frameCount * timeline.duration;
        const canvas = await rasterizeFrame(timeline, time, width, controller.signal);
        return canvas.getContext('2d').getImageData(0, 0, width, height);
      },
      onProgress: value => {
        progress = value;
        $('progress').value = value.ratio;
        $('export-status').textContent = t().exporting(value.completed, value.total);
      },
    });
    download(new Blob([bytes], { type: 'image/gif' }), `${root.dataset.name}-${capturedRate}x${capturedDirection < 0 ? '-reverse' : ''}.gif`);
    progress = null;
    status('gifDone');
  } catch (error) {
    progress = null;
    status(error.name === 'AbortError' ? 'cancelled' : 'exportFailed');
    if (error.name !== 'AbortError') console.error(error);
  } finally {
    exportController = null;
    root.dataset.exporting = 'false';
    gifButtons.forEach(button => { button.disabled = false; });
    $('cancel').hidden = true;
    $('progress').hidden = true;
  }
}

$('play').addEventListener('click', () => playing ? pause() : play());
$('stop').addEventListener('click', () => { pause(); seek(0); });
$('previous').addEventListener('click', () => step(false));
$('next').addEventListener('click', () => step(true));
$('scrubber').addEventListener('input', event => {
  const target = Number(event.target.value);
  pause();
  seek(target);
});
$('speed').addEventListener('change', event => { rate = Number(event.target.value); lastTick = null; });
$('reverse').addEventListener('click', () => { direction = toggle('reverse') ? -1 : 1; stopAt = null; lastTick = null; });
$('loop').addEventListener('click', () => toggle('loop'));
// Fitted is the stylesheet's size (column width, capped to one screen); zoomed is the drawing's own width.
$('zoom').addEventListener('click', () => { $('svg-host').style.width = toggle('zoom') ? `${timeline.width}px` : ''; });
$('export').addEventListener('click', () => setMenu($('menu-list').hidden));
$('menu-list').addEventListener('click', () => setMenu(false));
$('png').addEventListener('click', exportPng);
root.querySelectorAll('[data-gif]').forEach(button => button.addEventListener('click', () => exportGif(Number(button.dataset.gif))));
$('cancel').addEventListener('click', () => exportController?.abort());
$('fullscreen').addEventListener('click', async () => {
  try {
    if (document.fullscreenElement === root) await document.exitFullscreen();
    else await root.requestFullscreen();
  } catch { if (!exportController) status('fullFailed'); }
});
document.addEventListener('click', event => { if (!$('menu').contains(event.target)) setMenu(false); });
root.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || $('menu-list').hidden) return;
  setMenu(false);
  $('export').focus();
});
document.addEventListener('fullscreenchange', localize);
document.addEventListener('visibilitychange', () => { lastTick = null; });
new MutationObserver(localize).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
window.addEventListener('pagehide', () => { pause(); exportController?.abort(); });
localize();

try {
  const response = await fetch(new URL(root.dataset.src, import.meta.url));
  if (!response.ok) throw new Error(`SVG HTTP ${response.status}`);
  timeline = createTimeline(await response.text());
  const shadow = $('svg-host').attachShadow({ mode: 'open' });
  const style = document.createElement('style');
  // Interaction-only styling stays out of the SVG so exports match the file.
  style.textContent = ':host{display:block}svg{display:block;width:100%;height:auto}' +
    '[data-nav]{cursor:pointer;outline:none}[data-nav] .nav-hit{transition:fill .12s}' +
    '[data-nav]:hover .nav-hit{fill:rgba(32,42,53,.06)}[data-nav]:active .nav-hit{fill:rgba(32,42,53,.12)}' +
    '[data-nav]:focus-visible .nav-hit{stroke:var(--accent,#2563eb);stroke-width:2.5}';
  shadow.append(style, timeline.svg);
  bindStations();
  $('loading').hidden = true;
  root.querySelectorAll('[data-needs-svg]').forEach(control => { control.disabled = false; });
  $('scrubber').max = timeline.duration;
  root.dataset.ready = 'true';
  seek(0);
  status('ready');
  localize();
} catch (error) {
  console.error(error);
  status('loadFailed');
  $('loading').textContent = t().loadFailed;
}
}

document.querySelectorAll('[data-keyflow-player]').forEach(setup);
