// Sample the supplied SVG's SMIL tracks deterministically for playback and export.
export function createTimeline(source) {
  const document = new DOMParser().parseFromString(source, 'image/svg+xml');
  if (document.querySelector('parsererror')) throw new Error('Invalid SVG document');
  const svg = document.documentElement;
  const tracks = [];
  for (const animation of [...svg.querySelectorAll('animateTransform, animate')]) {
    const target = animation.parentElement;
    const duration = Number.parseFloat(animation.getAttribute('dur'));
    const kind = animation.localName === 'animateTransform' ? 'translate' : 'opacity';
    if (!duration || (kind === 'translate' && animation.getAttribute('type') !== 'translate') ||
        (kind === 'opacity' && animation.getAttribute('attributeName') !== 'opacity')) {
      throw new Error('Unsupported animation track');
    }
    const values = animation.getAttribute('values').split(';').map(value =>
      kind === 'translate' ? value.trim().split(/[ ,]+/).map(Number) : [Number(value)]);
    const keyTimes = animation.getAttribute('keyTimes');
    const times = keyTimes ? keyTimes.split(';').map(value => Math.round(Number(value) * duration * 1000) / 1000)
      : values.map((_, i) => i * duration / (values.length - 1));
    const id = String(tracks.length);
    target.setAttribute('data-timeline-track', id);
    const discrete = animation.getAttribute('calcMode') === 'discrete';
    // Linear tracks without keyTimes are evenly spaced and can be indexed directly.
    tracks.push({ id, kind, duration, values, times, discrete, keyed: Boolean(keyTimes) && !discrete, target });
    animation.remove();
  }
  // A figure declares its track count, so a stale or truncated file fails here.
  if (!tracks.length || tracks.length !== Number(svg.getAttribute('data-tracks'))) throw new Error('Unexpected SVG animation data');
  const duration = Math.max(...tracks.map(track => track.duration));
  const phaseTimes = tracks.find(track => track.kind === 'opacity').times.slice(0, -1);
  const viewBox = svg.viewBox.baseVal;
  const width = viewBox.width, height = viewBox.height;

  function sample(track, time) {
    const t = Math.max(0, Math.min(time, track.duration - 0.000001));
    let i = 0;
    if (track.discrete || track.keyed) {
      while (i + 1 < track.times.length && t >= track.times[i + 1]) i++;
      if (track.discrete) return track.values[i];
      const next = Math.min(i + 1, track.values.length - 1);
      const span = track.times[next] - track.times[i];
      const part = span > 0 ? (t - track.times[i]) / span : 0;
      return track.values[i].map((value, j) => value + part * (track.values[next][j] - value));
    }
    const position = t / track.duration * (track.values.length - 1);
    i = Math.min(Math.floor(position), track.values.length - 2);
    const fraction = position - i;
    return track.values[i].map((value, j) => value + fraction * (track.values[i + 1][j] - value));
  }

  function render(time, targetSvg = svg) {
    const targets = targetSvg === svg ? null : new Map([...targetSvg.querySelectorAll('[data-timeline-track]')]
      .map(node => [node.getAttribute('data-timeline-track'), node]));
    for (const track of tracks) {
      const target = targets ? targets.get(track.id) : track.target;
      const values = sample(track, time);
      target.setAttribute(track.kind === 'translate' ? 'transform' : 'opacity',
        track.kind === 'translate' ? `translate(${values[0].toFixed(4)} ${values[1].toFixed(4)})` : String(values[0]));
    }
    // The opacity tracks mark the step in progress. At an exact checkpoint the
    // layout shown there is current instead, so its step marker yields.
    const checkpoint = phaseTimes.findIndex(value => Math.abs(value - time) < 0.0005);
    for (const mark of targetSvg.querySelectorAll('[data-mark]')) {
      const [kind, index] = mark.getAttribute('data-mark').split(':');
      const here = Number(index) === checkpoint;
      if (!mark.hasAttribute('data-timeline-track')) mark.setAttribute('opacity', here ? '1' : '0');
      else if (here && kind === 'step') mark.setAttribute('opacity', '0');
    }
  }

  function snapshot(time) {
    const copy = svg.cloneNode(true);
    render(time, copy);
    return copy;
  }

  function phase(time) {
    const t = Math.min(time, duration - 0.000001);
    let index = 0;
    while (index + 1 < phaseTimes.length && t >= phaseTimes[index + 1]) index++;
    return index;
  }
  render(0);
  return { svg, duration, width, height, phaseTimes, render, snapshot, phase };
}

export async function rasterizeFrame(timeline, time, width, signal) {
  if (signal?.aborted) throw new DOMException('Export cancelled', 'AbortError');
  const height = Math.round(width * timeline.height / timeline.width);
  const svg = timeline.snapshot(time);
  svg.setAttribute('width', String(width));
  svg.setAttribute('height', String(height));
  const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)], { type: 'image/svg+xml;charset=utf-8' }));
  try {
    const img = new Image();
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = () => reject(new Error('Unable to render SVG frame'));
      img.src = url;
    });
    if (signal?.aborted) throw new DOMException('Export cancelled', 'AbortError');
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, width, height);
    context.drawImage(img, 0, 0, width, height);
    return canvas;
  } finally {
    URL.revokeObjectURL(url);
  }
}
