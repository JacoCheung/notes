// The tool owns its content height; the article owns its reading layout.
(() => {
  const root = document.documentElement;
  const preferred = matchMedia('(prefers-color-scheme: dark)');
  function setTheme() {
    if (window.parent !== window) return;
    let theme;
    try { theme = localStorage.getItem('theme'); } catch (_) {}
    root.dataset.theme = theme === 'light' || theme === 'dark'
      ? theme : preferred.matches ? 'dark' : 'light';
  }
  setTheme();
  preferred.addEventListener('change', setTheme);
  window.addEventListener('storage', setTheme);
  if (window.parent !== window) {
    root.classList.add('embedded');
    const content = document.querySelector('.root, .app');
    let previous = 0;
    const report = () => {
      const style = getComputedStyle(document.body);
      const height = Math.ceil(content.getBoundingClientRect().height
        + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom));
      if (height !== previous) {
        previous = height;
        window.parent.postMessage({type: 'notes-tool-height', height}, location.origin);
      }
    };
    new ResizeObserver(report).observe(content);
    report();
  }
})();
