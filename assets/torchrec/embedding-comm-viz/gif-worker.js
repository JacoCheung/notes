import { GIFEncoder, quantize, applyPalette } from './vendor/gifenc-1.0.3.js';

let encoder;
let config;
let completed = 0;

self.onmessage = ({ data }) => {
  const { id, type } = data;
  try {
    if (type === 'init') {
      if (encoder) throw new Error('GIF worker has already been initialized.');
      config = data;
      encoder = GIFEncoder();
      self.postMessage({ id });
      return;
    }
    if (!encoder) throw new Error('GIF worker has not been initialized.');
    const { width, height, frameCount, delayMs, maxOutputBytes } = config;
    if (type === 'frame') {
      if (data.index !== completed || completed >= frameCount ||
          !(data.buffer instanceof ArrayBuffer) || data.buffer.byteLength !== width * height * 4) {
        throw new Error('Invalid GIF frame or frame order.');
      }
      const rgba = new Uint8Array(data.buffer);
      for (let alpha = 3; alpha < rgba.length; alpha += 4) {
        if (rgba[alpha] !== 255) {
          throw new Error('GIF frames must be opaque. Paint the canvas background before rendering.');
        }
      }
      const palette = quantize(rgba, 256, { format: 'rgb565' });
      const index = applyPalette(rgba, palette, 'rgb565');
      // Alternating centisecond delays keep 15 FPS exports close to their target duration.
      const delay = (Math.round((completed + 1) * delayMs / 10) -
                     Math.round(completed * delayMs / 10)) * 10;
      encoder.writeFrame(index, width, height, { palette, delay, repeat: 0, dispose: 1 });
      if (encoder.bytesView().byteLength > maxOutputBytes) {
        throw new Error('GIF output exceeds 64 MiB. Reduce the frame count or resolution.');
      }
      completed++;
      self.postMessage({ id, completed });
      return;
    }
    if (type === 'finish') {
      if (completed !== frameCount) throw new Error('GIF export ended before all frames arrived.');
      encoder.finish();
      const bytes = encoder.bytes();
      self.postMessage({ id, bytes }, [bytes.buffer]);
      encoder = null;
      return;
    }
    throw new Error('Unknown GIF worker request.');
  } catch (error) {
    self.postMessage({ id, error: error.message || String(error) });
  }
};
