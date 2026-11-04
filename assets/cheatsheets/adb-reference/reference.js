(() => {
  document.querySelectorAll('.man-sheet').forEach(sheet => {
    const en = sheet.dataset.language === 'en';
    const input = sheet.querySelector('[data-man-search]');
    const select = sheet.querySelector('select[data-man-scope]');
    const rows = [...sheet.querySelectorAll('.man-entry')];
    const sections = [...sheet.querySelectorAll('.man-section')];
    const groups = [...sheet.querySelectorAll('.man-group')];
    const count = sheet.querySelector('[data-man-count]');
    const status = sheet.querySelector('[data-man-status]');
    const searchIndex = new Map(rows.map(row => [row, (
      row.closest('.man-section').dataset.manScope + ' ' + row.querySelector('dt code').textContent + ' ' + row.querySelector('dd').textContent
    ).toLocaleLowerCase()]));
    function filter() {
      const terms = input.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      rows.forEach(row => {
        const scope = row.closest('.man-section').dataset.manScope;
        row.hidden = (select.value !== 'all' && select.value !== scope)
          || !terms.every(term => searchIndex.get(row).includes(term));
      });
      groups.forEach(group => { group.hidden = !group.querySelector('.man-entry:not([hidden])'); });
      sections.forEach(section => { section.hidden = !section.querySelector('.man-entry:not([hidden])'); });
      const shown = rows.filter(row => !row.hidden).length;
      count.textContent = `${shown} / ${rows.length}`;
      sheet.querySelector('.man-empty').hidden = shown > 0;
    }
    function reset() { input.value = ''; select.value = 'all'; filter(); }
    input.addEventListener('input', filter);
    select.addEventListener('change', filter);
    sheet.querySelector('[data-man-reset]').addEventListener('click', reset);
    sheet.querySelector('[data-man-print]').addEventListener('click', () => window.print());
    sheet.querySelectorAll('[data-man-copy]').forEach(button => {
      button.addEventListener('click', async () => {
        const text = button.closest('dt').querySelector('code').textContent;
        try {
          if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
          else {
            const area = document.createElement('textarea');
            area.value = text;
            area.style.cssText = 'position:fixed;left:-9999px;top:0';
            document.body.append(area);
            let copied;
            try { area.select(); copied = document.execCommand('copy'); }
            finally { area.remove(); button.focus({ preventScroll: true }); }
            if (!copied) throw new Error('Clipboard unavailable');
          }
          status.textContent = en ? 'Syntax copied.' : '已复制语法。';
          button.textContent = '✓';
          setTimeout(() => { button.textContent = en ? 'Copy' : '复制'; }, 1500);
        } catch {
          status.textContent = en ? 'Select and copy the syntax manually.' : '请手动选中语法复制。';
        }
      });
    });
    function reveal(hash) {
      const target = document.getElementById(decodeURIComponent(hash.slice(1)));
      if (target && sheet.contains(target) && target.closest('[hidden]')) reset();
    }
    document.addEventListener('click', event => {
      const link = event.target.closest('a[href^="#"]');
      if (link) reveal(link.hash);
    }, true);
    window.addEventListener('hashchange', () => reveal(location.hash));
    filter();
  });
})();
