document.querySelectorAll('.trace-figure').forEach(figure => {
  figure.querySelectorAll('[data-trace-fit]').forEach(button => {
    button.addEventListener('click', () => {
      const svg = figure.querySelector('svg');
      svg.style.width = button.dataset.traceFit === 'actual'
        ? `${svg.viewBox.baseVal.width}px` : '100%';
      figure.querySelectorAll('[data-trace-fit]').forEach(control => {
        control.setAttribute('aria-pressed', String(control === button));
      });
    });
  });
});
