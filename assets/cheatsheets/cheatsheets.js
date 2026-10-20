// Enhancements shared by migrated, native HTML reference sheets.
(() => {
  const sheet = document.querySelector('.cheatsheet-sheet');
  if (!sheet) return;
  sheet.querySelectorAll('input[type="search"]').forEach(input => {
    if (!input.hasAttribute('aria-label')) {
      input.setAttribute('aria-label', input.getAttribute('placeholder') || 'Search this cheatsheet');
    }
  });
  sheet.querySelectorAll('[data-sheet-zoom]').forEach(select => {
    select.addEventListener('change', () => {
      const object = select.closest('.viewer').querySelector('object');
      object.style.width = select.value === 'fit'
        ? '100%' : Number(object.dataset.nativeWidth) * Number(select.value) + 'px';
    });
  });
  // Search rebuilds cards. Keep heading nodes stable for the shared TOC's
  // scroll tracking, including headings temporarily removed by a filter.
  const headings = new Map([...sheet.querySelectorAll('h2[id], h3[id]')]
    .map(heading => [heading.id, heading]));
  new MutationObserver(() => {
    sheet.querySelectorAll('h2[id], h3[id]').forEach(heading => {
      const previous = headings.get(heading.id);
      if (previous && previous !== heading) {
        const anchor = previous.querySelector('.headerlink');
        previous.replaceChildren(...heading.childNodes);
        if (anchor && !previous.querySelector('.headerlink')) previous.appendChild(anchor);
        heading.replaceWith(previous);
      } else {
        headings.set(heading.id, heading);
      }
    });
  }).observe(sheet, { childList: true, subtree: true });
  // A search may hide a target. Restore the sheet before following its TOC link.
  document.addEventListener('click', event => {
    const link = event.target.closest('.post-toc a[href^="#"]');
    if (!link) return;
    const id = decodeURIComponent(link.hash.slice(1));
    const target = document.getElementById(id);
    if (target && target.getClientRects().length) return;
    const input = sheet.querySelector('input[type="search"]');
    if (input) {
      input.value = '';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    sheet.querySelectorAll('#filters input[type="checkbox"]').forEach(filter => {
      if (!filter.checked) {
        filter.checked = true;
        filter.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
  });
})();
