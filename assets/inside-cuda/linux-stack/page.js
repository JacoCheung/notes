'use strict';

function setupComponentInfo(figure) {
  const catalogElement = figure.querySelector('[data-component-catalog]');
  if (!catalogElement) return () => {};
  const catalog = JSON.parse(catalogElement.textContent);
  const article = figure.closest('.lang-zh, .lang-en');
  const panel = figure.querySelector('.component-popover');
  const closeButton = panel.querySelector('[data-component-close]');
  const nativePopover = typeof panel.showPopover === 'function';
  let active = null;

  const clearSelection = () => {
    active?.classList.remove('is-selected');
    active?.setAttribute('aria-expanded', 'false');
    active = null;
    panel.hidden = true;
  };
  const close = (restoreFocus = false) => {
    const trigger = active;
    if (nativePopover && panel.matches(':popover-open')) panel.hidePopover();
    clearSelection();
    if (restoreFocus) trigger?.focus({preventScroll: true});
  };
  const position = () => {
    if (!active) return;
    const margin = 12;
    const top = Math.max(margin, (document.querySelector('.site-nav')?.getBoundingClientRect().bottom || 0) + margin);
    panel.style.maxHeight = `${Math.max(64, window.innerHeight - top - margin)}px`;
    const anchor = active.getBoundingClientRect();
    const box = panel.getBoundingClientRect();
    let x, y;
    if (anchor.right + margin + box.width <= window.innerWidth - margin) {
      x = anchor.right + margin;
      y = anchor.top;
    } else if (anchor.left - margin - box.width >= margin) {
      x = anchor.left - margin - box.width;
      y = anchor.top;
    } else {
      x = anchor.left + (anchor.width - box.width) / 2;
      y = anchor.bottom + margin;
      if (y + box.height > window.innerHeight - margin) y = anchor.top - box.height - margin;
    }
    panel.style.left = `${Math.max(margin, Math.min(x, window.innerWidth - box.width - margin))}px`;
    panel.style.top = `${Math.max(top, Math.min(y, window.innerHeight - box.height - margin))}px`;
  };
  const open = node => {
    if (active === node) { close(true); return; }
    const info = catalog[node.dataset.component];
    const row = article.querySelector(`[data-component-row="${node.dataset.component}"]`);
    const description = panel.querySelector('[data-component-description]');
    if (row && info.row_description !== undefined) {
      description.replaceChildren(...Array.from(row.cells[info.row_description].childNodes, child => child.cloneNode(true)));
    } else description.textContent = info.description;
    const meta = panel.querySelector('[data-component-meta]');
    meta.hidden = !(row && info.row_details !== undefined);
    if (!meta.hidden) {
      panel.querySelector('[data-component-meta-value]').replaceChildren(
        ...Array.from(row.cells[info.row_details].childNodes, child => child.cloneNode(true)));
    }
    panel.querySelector('[data-component-layer]').textContent = info.layer;
    panel.querySelector('[data-component-title]').textContent = node.dataset.componentTitle;
    panel.querySelector('[data-component-links]').replaceChildren(...info.links.map(ref => {
      const link = document.createElement('a');
      link.href = ref.url;
      link.textContent = ref.label;
      if (new URL(ref.url, document.baseURI).origin !== location.origin) {
        link.target = '_blank';
        link.rel = 'noopener';
      }
      return link;
    }));
    const section = panel.querySelector('[data-component-section]');
    section.href = info.section;
    section.querySelector('span').textContent = info.section_label;
    active?.classList.remove('is-selected');
    active?.setAttribute('aria-expanded', 'false');
    active = node;
    active.classList.add('is-selected');
    active.setAttribute('aria-expanded', 'true');
    panel.hidden = false;
    if (nativePopover && !panel.matches(':popover-open')) panel.showPopover();
    position();
    closeButton.focus({preventScroll: true});
  };
  figure.querySelectorAll('[data-component]').forEach(node => {
    node.addEventListener('click', () => open(node));
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (!event.repeat) open(node);
      }
    });
  });
  closeButton.addEventListener('click', () => close(true));
  panel.addEventListener('toggle', event => {
    // A queued close event must not clear a popup that was reopened meanwhile.
    if (event.newState === 'closed' && !panel.matches(':popover-open')) clearSelection();
  });
  panel.querySelector('[data-component-section]').addEventListener('click', () => close());
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && active) { event.preventDefault(); close(true); }
  });
  document.addEventListener('click', event => {
    if (!active || panel.contains(event.target)) return;
    const node = event.target.closest?.('[data-component]');
    if (!node || !figure.contains(node)) close();
  });
  // Close on article/diagram scrolling, but allow the popup itself to scroll.
  document.addEventListener('scroll', event => {
    if (active && !panel.contains(event.target)) close();
  }, true);
  window.addEventListener('resize', position);
  return close;
}

document.querySelectorAll('.cuda-figure').forEach(figure => {
  const closeInfo = setupComponentInfo(figure);
  if (figure.dataset.layout) {
    const viewport = figure.querySelector('.diagram-viewport');
    const fitWindow = () => {
      if (!figure.clientWidth) { closeInfo(); return; }
      const header = document.querySelector('.site-nav')?.getBoundingClientRect().height || 56;
      const chrome = figure.getBoundingClientRect().height - viewport.getBoundingClientRect().height;
      const available = Math.max(64, window.innerHeight - header - chrome - 32);
      figure.style.setProperty('--diagram-fit-height', `${available}px`);
    };
    // Also runs when switching languages, when the hidden figure becomes visible.
    // Defer writes outside ResizeObserver delivery to avoid a resize feedback
    // warning when the SVG's fitted height changes the figure's own height.
    let fitFrame = 0;
    const scheduleFit = () => {
      cancelAnimationFrame(fitFrame);
      fitFrame = requestAnimationFrame(fitWindow);
    };
    const observer = new ResizeObserver(scheduleFit);
    observer.observe(figure);
    window.addEventListener('resize', scheduleFit);
    fitWindow();
  }
  const size = figure.querySelector('[data-size-toggle]');
  size.addEventListener('click', () => {
    closeInfo();
    const actual = figure.dataset.size !== 'actual';
    figure.dataset.size = actual ? 'actual' : 'fit';
    size.setAttribute('aria-pressed', String(actual));
    size.textContent = actual ? size.dataset.fitLabel : size.dataset.actualLabel;
  });
  const focus = figure.querySelector('[data-path-focus]');
  if (focus) focus.addEventListener('change', () => {
    closeInfo();
    const path = focus.value;
    figure.querySelectorAll('[data-paths]').forEach(element => {
      element.classList.toggle('is-muted', path !== 'all' && !element.dataset.paths.split(' ').includes(path));
    });
  });
});
