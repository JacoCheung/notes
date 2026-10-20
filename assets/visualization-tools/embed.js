// Keep a single tool instance alive when switching the article language.
// Tool documents are local and can also be opened independently.
(() => {
  const frames = [...document.querySelectorAll('iframe.tool-frame')];
  const preferred = matchMedia('(prefers-color-scheme: dark)');
  function sync(frame) {
    const doc = frame.contentDocument;
    if (!doc?.body) return;
    doc.documentElement.dataset.theme = document.documentElement.dataset.theme
      || (preferred.matches ? 'dark' : 'light');
    doc.documentElement.dataset.articleLang = document.documentElement.lang;
  }
  frames.forEach(frame => frame.addEventListener('load', () => sync(frame)));
  new MutationObserver(() => frames.forEach(sync)).observe(document.documentElement, {
    attributes: true, attributeFilter: ['data-theme', 'lang'],
  });
  preferred.addEventListener('change', () => frames.forEach(sync));
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.data?.type !== 'notes-tool-height') return;
    const frame = frames.find(item => item.contentWindow === event.source);
    const height = Number(event.data.height);
    if (frame && Number.isFinite(height) && height > 0) {
      frame.style.height = Math.ceil(height) + 'px';
    }
  });
  frames.forEach(sync);
})();
