(() => {
  'use strict';
  const selector = 'abbr.term-abbr';
  const tooltip = document.createElement('div');
  tooltip.className = 'term-tooltip';
  tooltip.id = 'term-tooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.hidden = true;
  document.body.append(tooltip);
  let active = null;
  let pinned = false;
  let closeTimer = 0;

  const prepare = term => {
    if (term.hasAttribute('title')) {
      term.dataset.expansion = term.getAttribute('title');
      term.removeAttribute('title'); // Avoid a second, delayed native tooltip.
    }
  };
  document.querySelectorAll(selector).forEach(prepare);

  const close = () => {
    clearTimeout(closeTimer);
    active?.removeAttribute('aria-describedby');
    active = null;
    pinned = false;
    tooltip.hidden = true;
  };
  const position = () => {
    const anchor = active.getBoundingClientRect();
    const box = tooltip.getBoundingClientRect();
    const margin = 12;
    let top = anchor.bottom + 10;
    if (top + box.height > innerHeight - margin) top = anchor.top - box.height - 10;
    tooltip.style.top = `${Math.max(margin, top)}px`;
    tooltip.style.left = `${Math.max(margin, Math.min(anchor.left, innerWidth - box.width - margin))}px`;
  };
  const open = term => {
    clearTimeout(closeTimer);
    if (active !== term) {
      close();
      active = term;
    }
    prepare(term); // Component popovers may clone annotated table cells.
    tooltip.textContent = term.dataset.expansion;
    term.setAttribute('aria-describedby', tooltip.id);
    tooltip.hidden = false;
    position();
  };
  const scheduleClose = () => {
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => {
      if (!pinned && document.activeElement !== active && !tooltip.matches(':hover')) close();
    }, 150);
  };
  document.addEventListener('pointerover', event => {
    if (event.pointerType === 'touch') return;
    const term = event.target.closest?.(selector);
    if (term && !term.contains(event.relatedTarget)) open(term);
    if (tooltip.contains(event.target)) clearTimeout(closeTimer);
  });
  document.addEventListener('pointerout', event => {
    const term = event.target.closest?.(selector);
    if (term && term === active && !term.contains(event.relatedTarget)) scheduleClose();
    if (tooltip.contains(event.target) && !tooltip.contains(event.relatedTarget)) scheduleClose();
  });
  document.addEventListener('focusin', event => {
    if (event.target.matches?.(selector)) open(event.target);
  });
  document.addEventListener('focusout', event => {
    if (event.target === active) { pinned = false; scheduleClose(); }
  });
  document.addEventListener('click', event => {
    const term = event.target.closest?.(selector);
    if (term) {
      if (term === active && pinned) close();
      else { open(term); pinned = true; }
    } else if (!tooltip.contains(event.target)) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && active) {
      event.preventDefault();
      close();
    } else if ((event.key === 'Enter' || event.key === ' ') && event.target.matches?.(selector)) {
      event.preventDefault();
      if (!event.repeat) event.target.click();
    }
  });
  document.addEventListener('scroll', event => {
    if (!tooltip.contains(event.target)) close();
  }, true);
  window.addEventListener('resize', close);
  new MutationObserver(close).observe(document.documentElement, {
    attributes: true, attributeFilter: ['lang'],
  });
})();
