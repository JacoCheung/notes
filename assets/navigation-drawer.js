// Reuse the desktop navigation in a modal drawer on narrow screens.
// Moving the original element preserves links, IDs, and disclosure state.
(function () {
  window.NotesNavigationDrawer = function ({ content, kind, onClose, onSelect }) {
    const host = document.querySelector('.site-nav-links');
    if (!content || !host || typeof HTMLDialogElement === 'undefined') return null;

    const narrow = window.matchMedia('(max-width: 1099px)');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'mobile-nav-toggle';
    button.setAttribute('aria-haspopup', 'dialog');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-controls', 'mobile-navigation');
    button.innerHTML = '<svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14" fill="none" stroke="currentColor" stroke-width="1.5"/></svg><span></span>';
    host.prepend(button);

    const dialog = document.createElement('dialog');
    dialog.id = 'mobile-navigation';
    dialog.className = 'mobile-nav-dialog';
    dialog.setAttribute('aria-labelledby', 'mobile-navigation-title');
    dialog.innerHTML = '<div class="mobile-nav-header"><h2 id="mobile-navigation-title"></h2>' +
      '<button class="mobile-nav-close" type="button" autofocus><svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></button></div>' +
      '<div class="mobile-nav-body"></div>';
    document.body.appendChild(dialog);
    content.classList.add('mobile-nav-source');
    const closeButton = dialog.querySelector('.mobile-nav-close');
    let placeholder = null;

    function restore() {
      if (!placeholder) return;
      placeholder.replaceWith(content);
      placeholder = null;
      document.documentElement.classList.remove('mobile-nav-open');
      button.setAttribute('aria-expanded', 'false');
      if (onClose) onClose();
    }

    function close() {
      if (dialog.open) dialog.close();
      restore();
    }

    button.addEventListener('click', () => {
      if (!narrow.matches || dialog.open) return;
      placeholder = document.createComment('navigation position');
      content.before(placeholder);
      dialog.querySelector('.mobile-nav-body').appendChild(content);
      document.documentElement.classList.add('mobile-nav-open');
      button.setAttribute('aria-expanded', 'true');
      dialog.showModal();
      const current = content.querySelector('a.active, .series-filter.active');
      if (current) current.scrollIntoView({ block: 'nearest', behavior: 'instant' });
    });
    closeButton.addEventListener('click', close);
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
    dialog.addEventListener('close', restore);
    let backdropPress = false;
    dialog.addEventListener('pointerdown', event => { backdropPress = event.target === dialog; });
    dialog.addEventListener('click', event => {
      if (backdropPress && event.target === dialog) close();
      backdropPress = false;
    });
    content.addEventListener('click', event => {
      const selection = event.target.closest('a[href], .series-filter');
      if (!dialog.open || !selection || event.defaultPrevented ||
          event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      close();
      if (onSelect) onSelect(selection);
      const href = selection.getAttribute('href');
      if (href?.startsWith('#')) {
        const heading = document.getElementById(decodeURIComponent(href.slice(1)));
        if (heading) requestAnimationFrame(() => {
          const hadTabindex = heading.hasAttribute('tabindex');
          if (!hadTabindex) heading.tabIndex = -1;
          heading.focus({ preventScroll: true });
          if (!hadTabindex) heading.addEventListener('blur', () => heading.removeAttribute('tabindex'), { once: true });
        });
      }
    });
    narrow.addEventListener('change', () => { if (!narrow.matches) close(); });
    window.addEventListener('pagehide', close);

    function setLanguage(language) {
      const english = language === 'en';
      button.querySelector('span').textContent = english ? 'Contents' : '目录';
      const title = kind === 'series'
        ? (english ? 'Blog series' : '博客系列')
        : (english ? 'Article contents' : '文章目录');
      button.setAttribute('aria-label', (english ? 'Open ' : '打开') + title);
      dialog.querySelector('h2').textContent = title;
      closeButton.setAttribute('aria-label', english ? 'Close contents' : '关闭目录');
    }
    setLanguage(document.documentElement.lang.startsWith('en') ? 'en' : 'zh');
    return { close, setLanguage };
  };
})();
