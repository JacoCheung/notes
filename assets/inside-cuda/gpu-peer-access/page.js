(() => {
  'use strict';
  document.querySelectorAll('.p2p-figure').forEach(figure => {
    const svg = figure.querySelector('svg');
    figure.querySelectorAll('[data-size]').forEach(button => {
      button.addEventListener('click', () => {
        svg.style.width = button.dataset.size === 'fit' ? '100%' : svg.viewBox.baseVal.width + 'px';
        figure.querySelectorAll('[data-size]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      });
    });
  });
  document.querySelectorAll('.p2p-lab').forEach(lab => {
    const zh = lab.dataset.lang === 'zh';
    const aperture = lab.querySelector('[data-aperture]'), peer = lab.querySelector('[data-peer]');
    const offset = lab.querySelector('[data-offset]');
    const put = (key, value) => {lab.querySelector('[data-' + key + ']').textContent = value;};
    function update() {
      const remote = aperture.value === 'peer', id = Number(peer.value);
      peer.disabled = !remote;
      if (!offset.validity.valid || offset.value === '') {
        put('route', zh ? '页内偏移须为 0–4095 的整数。' : 'Enter an integer page offset from 0 to 4095.');
        return;
      }
      const base = 0x12345000n;
      const pte = ((base >> 12n) << 8n) | (remote ? BigInt(id) << 33n : 0n) | (remote ? 2n : 0n) | 1n;
      put('pte', 'PTE = 0x' + pte.toString(16).padStart(16, '0'));
      put('aperture-value', remote ? '01 · peer' : '00 · local');
      put('peer-value', remote ? id.toString(2).padStart(3, '0') + ' · ID ' + id : (zh ? '000 · PA 的高位' : '000 · upper PA bits'));
      put('pa-value', '0x12345');
      const physical = '0x' + (base + BigInt(offset.value)).toString(16);
      put('route', remote
        ? (zh ? `目标：peer slot ${id} 的物理地址 ${physical}。实际 GPU 与链路由已有 peer 映射确定。` : `Target: physical address ${physical} in peer slot ${id}. The existing peer mapping determines the GPU and link.`)
        : (zh ? `目标：当前 GPU 的物理地址 ${physical}。` : `Target: physical address ${physical} on the current GPU.`));
    }
    [aperture, peer].forEach(e => e.addEventListener('change', update));
    offset.addEventListener('input', update);
    update();
  });
})();
