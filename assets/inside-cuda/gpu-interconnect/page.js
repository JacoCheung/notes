'use strict';

document.querySelectorAll('.interconnect-article [data-path-focus]').forEach(select => {
  const readingLink = select.closest('figure').querySelector('[data-path-reading]');
  if (!readingLink) return;
  const update = () => {
    readingLink.href = select.selectedOptions[0].dataset.pathHref;
  };
  select.addEventListener('change', update);
  update();
});
