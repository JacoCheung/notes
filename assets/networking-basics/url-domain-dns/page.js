(() => {
  'use strict';
  document.querySelectorAll('[data-network-size]').forEach(button => {
    button.addEventListener('click', () => {
      const figure = button.closest('.network-figure');
      const actual = figure.dataset.size !== 'actual';
      figure.dataset.size = actual ? 'actual' : 'fit';
      button.setAttribute('aria-pressed', String(actual));
      button.textContent = actual ? button.dataset.fitLabel : button.dataset.actualLabel;
      figure.querySelector('svg').style.width = actual ? '1000px' : '100%';
    });
  });
})();
