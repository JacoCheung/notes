/** Resource limits shared with the caller when choosing export resolution and FPS. */
export const GIF_EXPORT_LIMITS = Object.freeze({
  maxDimension: 2048,
  maxPixelsPerFrame: 2_100_000,
  maxFrames: 600,
  maxTotalPixels: 180_000_000,
  maxDurationMs: 120_000,
  maxOutputBytes: 64 * 1024 * 1024,
});

const abortError = () => new DOMException('GIF export cancelled.', 'AbortError');

/**
 * Encode an animation in a dedicated module Worker, one RGBA frame at a time.
 *
 * renderFrame(index) must return (or resolve to) an opaque RGBA8 ImageData with
 * the requested dimensions. Paint the canvas background before taking its image.
 * Its data buffer is transferred to the worker: do not reuse that ImageData.
 * Only one frame is requested at a time; compressed output accumulates in the
 * worker. Wrap the result with new Blob([bytes], { type: 'image/gif' }).
 *
 * delayMs is the desired duration of each frame. GIF stores 10 ms units; the
 * worker rounds cumulative frame times to preserve the overall duration.
 * onProgress receives { completed, total, ratio }, starting at zero.
 * Aborting terminates the worker and rejects with an AbortError, even while a
 * renderFrame promise is pending. The caller owns cancellation of its renderer.
 */
export async function encodeGifFrames({
  width, height, frameCount, delayMs, renderFrame, signal, onProgress,
}) {
  const limits = GIF_EXPORT_LIMITS;
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 ||
      width > limits.maxDimension || height > limits.maxDimension ||
      width * height > limits.maxPixelsPerFrame) {
    throw new RangeError('GIF dimensions exceed the export limit.');
  }
  if (!Number.isInteger(frameCount) || frameCount < 1 || frameCount > limits.maxFrames ||
      width * height * frameCount > limits.maxTotalPixels) {
    throw new RangeError('GIF frame count exceeds the export limit.');
  }
  if (!Number.isFinite(delayMs) || delayMs < 20 || delayMs > 655350 ||
      frameCount * delayMs > limits.maxDurationMs) {
    throw new RangeError('GIF frame delay must be at least 20 ms and fit the duration limit.');
  }
  if (typeof renderFrame !== 'function' ||
      (onProgress !== undefined && typeof onProgress !== 'function')) {
    throw new TypeError('GIF export requires a frame renderer and an optional progress callback.');
  }
  if (signal && (typeof signal.addEventListener !== 'function' ||
                 typeof signal.removeEventListener !== 'function')) {
    throw new TypeError('signal must be an AbortSignal.');
  }
  if (signal?.aborted) throw abortError();
  if (typeof Worker === 'undefined') throw new Error('This browser does not support Web Workers.');

  const worker = new Worker(new URL('./gif-worker.js', import.meta.url), { type: 'module' });
  return new Promise((resolve, reject) => {
    let settled = false;
    let pending = null;
    let nextId = 0;
    const cleanup = () => {
      worker.terminate();
      signal?.removeEventListener('abort', onAbort);
      worker.onmessage = worker.onerror = worker.onmessageerror = null;
    };
    const fail = error => {
      if (settled) return;
      settled = true;
      const request = pending;
      pending = null;
      cleanup();
      request?.reject(error);
      reject(error);
    };
    const onAbort = () => fail(abortError());
    const request = (message, transfers = []) => new Promise((accept, decline) => {
      if (settled) return decline(abortError());
      const id = ++nextId;
      pending = { id, resolve: accept, reject: decline };
      try { worker.postMessage({ ...message, id }, transfers); }
      catch (error) { fail(error); }
    });
    worker.onmessage = ({ data }) => {
      if (settled) return;
      if (!pending || data?.id !== pending.id) {
        fail(new Error('Unexpected GIF worker response.'));
        return;
      }
      if (data.error) {
        fail(new Error(data.error));
        return;
      }
      const response = pending;
      pending = null;
      response.resolve(data);
    };
    worker.onerror = event => {
      event.preventDefault();
      fail(new Error(event.message || 'Unable to load the GIF encoder worker.'));
    };
    worker.onmessageerror = () => fail(new Error('Unable to read the GIF worker response.'));
    signal?.addEventListener('abort', onAbort, { once: true });

    const run = async () => {
      await request({ type: 'init', width, height, frameCount, delayMs,
        maxOutputBytes: limits.maxOutputBytes });
      onProgress?.({ completed: 0, total: frameCount, ratio: 0 });
      for (let index = 0; index < frameCount; index++) {
        if (settled) return;
        const frame = await renderFrame(index);
        if (settled) return;
        if (!(frame instanceof ImageData) || !(frame.data instanceof Uint8ClampedArray) ||
            frame.width !== width || frame.height !== height ||
            frame.data.byteLength !== width * height * 4) {
          throw new TypeError('renderFrame must return RGBA8 ImageData with the export dimensions.');
        }
        const pixels = frame.data;
        const buffer = pixels.buffer instanceof ArrayBuffer && pixels.byteOffset === 0 &&
          pixels.byteLength === pixels.buffer.byteLength ? pixels.buffer : pixels.slice().buffer;
        await request({ type: 'frame', index, buffer }, [buffer]);
        if (settled) return;
        onProgress?.({ completed: index + 1, total: frameCount, ratio: (index + 1) / frameCount });
      }
      const { bytes } = await request({ type: 'finish' });
      if (settled) return;
      settled = true;
      cleanup();
      resolve(bytes);
    };
    if (signal?.aborted) onAbort();
    else run().catch(fail);
  });
}
