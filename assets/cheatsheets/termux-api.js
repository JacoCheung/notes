(() => {
  document.querySelectorAll('.termux-sheet').forEach(sheet => {
    const en = sheet.dataset.language === 'en';
    const input = sheet.querySelector('[data-termux-search]');
    const category = sheet.querySelector('[data-termux-category]');
    const groups = [...sheet.querySelectorAll('.command-group')];
    const rows = [...sheet.querySelectorAll('.command-row')];
    const searchable = new Map(rows.map(row => [row, row.textContent.toLocaleLowerCase()]));
    function filter() {
      const terms = input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
      let shown = 0;
      groups.forEach(group => {
        let groupShown = 0;
        group.querySelectorAll('.command-row').forEach(row => {
          const matches = (category.value === 'all' || category.value === group.dataset.category)
            && terms.every(term => searchable.get(row).includes(term));
          row.hidden = !matches;
          if (matches) groupShown++;
        });
        group.hidden = !groupShown;
        shown += groupShown;
      });
      sheet.querySelector('.termux-results').textContent = en
        ? `${shown} / ${rows.length} commands` : `显示 ${shown} / ${rows.length} 个命令入口`;
      sheet.querySelector('.termux-empty').hidden = shown > 0;
    }
    function reset() { input.value = ''; category.value = 'all'; filter(); }
    input.addEventListener('input', filter);
    category.addEventListener('change', filter);
    sheet.querySelector('[data-termux-reset]').addEventListener('click', reset);
    sheet.querySelector('[data-termux-print]').addEventListener('click', () => window.print());
    const status = document.createElement('p');
    status.className = 'termux-copy-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    sheet.querySelector('.termux-toolbar').after(status);
    sheet.querySelectorAll('.termux-copy').forEach(button => {
      const text = button.parentElement.querySelector('code').textContent;
      button.setAttribute('aria-label', `${en ? 'Copy command' : '复制命令'}: ${text.split('\n')[0]}`);
      button.addEventListener('click', async () => {
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
          } else {
            const area = document.createElement('textarea');
            area.value = text;
            area.style.cssText = 'position:fixed;top:0;left:-9999px';
            document.body.append(area);
            let copied;
            try { area.select(); copied = document.execCommand('copy'); }
            finally { area.remove(); button.focus({ preventScroll: true }); }
            if (!copied) throw new Error('Clipboard unavailable');
          }
          button.textContent = en ? 'Copied' : '已复制';
          status.textContent = en ? 'Copied as text; nothing was executed.' : '已复制文本，未执行命令。';
          setTimeout(() => { button.textContent = en ? 'Copy' : '复制'; }, 1600);
        } catch {
          status.textContent = en ? 'Copy unavailable. Select and copy the code manually.' : '复制不可用，请手动选中代码复制。';
        }
      });
    });
    // Restore filtered targets before the shared TOC handles the click.
    document.addEventListener('click', event => {
      const link = event.target.closest('.post-toc a[href^="#"]');
      if (!link) return;
      const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      if (target && sheet.contains(target) && !target.getClientRects().length) reset();
    }, true);
    filter();
  });
})();
