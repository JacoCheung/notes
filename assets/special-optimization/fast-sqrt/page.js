(() => {
  'use strict';
  const cards = [...document.querySelectorAll('[data-fs-explorer]')];
  const buffer = new ArrayBuffer(4);
  const view = new DataView(buffer);
  const f32 = Math.fround;
  const bits = value => { view.setFloat32(0, value, true); return view.getUint32(0, true); };
  const float = value => { view.setUint32(0, value, true); return view.getFloat32(0, true); };
  const hex = value => '0x' + value.toString(16).padStart(8, '0');
  const decimal = value => Number(value.toPrecision(10)).toString();
  const percentage = value => (value >= 0 ? '+' : '') + (value * 100).toFixed(7) + '%';
  const words = {
    zh: { invalid: '请输入可表示为 32 位浮点数的正正规数。', steps: '已计算初值与两次牛顿迭代。' },
    en: { invalid: 'Enter a positive normal binary32 value.', steps: 'Seed and two Newton updates calculated.' },
  };

  function update(raw, origin = null) {
    const x = f32(Number(raw));
    const i = bits(x);
    const exponent = (i >>> 23) & 255;
    const valid = raw.trim() !== '' && x > 0 && exponent > 0 && exponent < 255;
    for (const card of cards) {
      const input = card.querySelector('[data-fs-input]');
      if (input !== origin) input.value = raw;
      input.setAttribute('aria-invalid', String(!valid));
      card.querySelector('[data-fs-results]').hidden = !valid;
      card.querySelector('[data-fs-message]').textContent = words[card.dataset.language][valid ? 'steps' : 'invalid'];
    }
    if (!valid) return;
    const j = (0x5f3759df - (i >>> 1)) >>> 0;
    const reference = Math.sqrt(x);
    let y = float(j);
    const rows = [];
    for (let n = 0; n <= 2; n++) {
      const squareRoot = f32(x * y);
      rows.push([n, decimal(y), percentage(y / (1 / reference) - 1), decimal(squareRoot), percentage(squareRoot / reference - 1)]);
      const xy = f32(x * y);
      const halfY = f32(0.5 * y);
      y = f32(y * f32(1.5 - f32(xy * halfY)));
    }
    for (const card of cards) {
      const write = (name, value) => { card.querySelector(`[data-fs-${name}]`).textContent = value; };
      write('value', decimal(x));
      write('bits', hex(i));
      write('fields', `${exponent} / ${hex(i & 0x7fffff)}`);
      write('shift', hex(i >>> 1));
      write('seed', hex(j));
      const body = card.querySelector('[data-fs-rows]');
      body.replaceChildren(...rows.map(values => {
        const row = document.createElement('tr');
        for (const value of values) {
          const cell = document.createElement('td');
          cell.textContent = value;
          row.append(cell);
        }
        return row;
      }));
    }
  }

  for (const card of cards) {
    card.querySelector('form').addEventListener('submit', event => event.preventDefault());
    card.querySelector('[data-fs-input]').addEventListener('input', event => update(event.target.value, event.target));
    for (const button of card.querySelectorAll('[data-fs-preset]')) {
      button.addEventListener('click', () => update(button.dataset.fsPreset));
    }
  }
  update('25');
})();
