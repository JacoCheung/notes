/* Numeric illustration of fixed index maps; no PyTorch runtime is embedded. */
(() => {
  'use strict';
  const transpose = a => a[0].map((_, j) => a.map(row => row[j]));
  const zeros = a => a.map(row => row.map(() => 0));
  const gather = (a, index, dim) => index.map((row, i) => row.map((k, j) => dim === 0 ? a[k][j] : a[i][k]));
  function scatter(base, index, src, dim, add) {
    const out = base.map(row => row.slice()), counts = zeros(base);
    index.forEach((row, i) => row.forEach((k, j) => {
      const r = dim === 0 ? k : i, c = dim === 0 ? j : k;
      counts[r][c]++;
      out[r][c] = add ? out[r][c] + src[i][j] : src[i][j];
    }));
    return {out, counts};
  }
  function matrix(host, name, values, counts) {
    const wrapper = document.createElement('div');
    wrapper.className = 'gs-matrix';
    const title = document.createElement('strong');
    title.textContent = name + ' · [' + values.length + ', ' + values[0].length + ']';
    const cells = document.createElement('div');
    cells.className = 'gs-cells';
    cells.style.gridTemplateColumns = `repeat(${values[0].length}, minmax(0, 1fr))`;
    cells.setAttribute('role', 'table');
    cells.setAttribute('aria-label', name);
    values.forEach((row, i) => {
      const rowNode = document.createElement('div');
      rowNode.setAttribute('role', 'row');
      rowNode.style.display = 'contents';
      row.forEach((v, j) => {
        const cell = document.createElement('span');
        cell.className = 'gs-cell';
        cell.setAttribute('role', 'cell');
        cell.setAttribute('aria-label', `[${i},${j}]: ${v}`);
        cell.textContent = String(v);
        if (counts) {
          cell.dataset.hit = counts[i][j] > 0;
          cell.dataset.collision = counts[i][j] > 1;
        }
        rowNode.append(cell);
      });
      cells.append(rowNode);
    });
    wrapper.append(title, cells);
    host.append(wrapper);
  }
  document.querySelectorAll('.gs-lab').forEach(lab => {
    const zh = lab.dataset.lang === 'zh';
    function render() {
      const op = lab.querySelector('[data-op]').value;
      const backward = lab.querySelector('[data-pass]').value === 'backward';
      const dim = Number(lab.querySelector('[data-dim]').value);
      const repeated = lab.querySelector('[data-indices]').value === 'repeated';
      const orient = a => dim === 1 ? a : transpose(a);
      const x = orient([[10,20,30,40],[50,60,70,80]]);
      const base = orient([[1,2,3,4],[5,6,7,8]]);
      const src = orient([[10,20,30],[40,50,60]]);
      const index = orient(repeated ? [[2,0,2],[1,3,0]] : [[2,0,3],[1,3,0]]);
      const g = op === 'gather' ? orient([[1,2,3],[4,5,6]]) : orient([[1,2,3,4],[5,6,7,8]]);
      const counts = scatter(zeros(base), index, src, dim, true).counts;
      const host = lab.querySelector('.gs-matrices');
      const explanation = lab.querySelector('[data-explanation]');
      const warning = lab.querySelector('[data-warning]');
      host.replaceChildren();
      matrix(host, 'index', index);
      if (backward) {
        matrix(host, 'g = ∂L/∂out', g);
        if (op === 'gather') {
          matrix(host, 'dx', scatter(zeros(x), index, g, dim, true).out, counts);
          explanation.textContent = zh ? '同一输入被读取多次时，dx 汇总所有读取路径的上游梯度；未读取的位置为 0。' : 'dx sums the upstream gradients of all reads of each input. Unread inputs receive zero.';
        } else {
          const db = op === 'scatter_add' ? g : scatter(g, index, zeros(src), dim, false).out;
          matrix(host, 'dbase', db, counts);
          matrix(host, 'dsrc', gather(g, index, dim));
          explanation.textContent = op === 'scatter_add'
            ? (zh ? '加法保留 base 的完整梯度；每个 src 元素从自己的目标位置取得上游梯度。' : 'Addition preserves the complete base gradient. Each source receives its destination gradient.')
            : (zh ? '覆盖位置的 base 梯度为 0；dsrc 展示实现中的 g.gather(dim,index)。' : 'Overwritten base positions receive zero. dsrc shows the implementation’s g.gather(dim,index).');
        }
      } else if (op === 'gather') {
        matrix(host, 'x', x, counts);
        matrix(host, 'out', gather(x, index, dim));
        explanation.textContent = zh ? '输出每个位置读取 index 指定的输入元素；重复读取会产生多份相同的值。' : 'Each output reads the input addressed by index. Repeated reads produce multiple copies.';
      } else {
        matrix(host, 'src', src);
        matrix(host, 'base', base);
        const result = scatter(base, index, src, dim, op === 'scatter_add').out;
        if (op === 'scatter') result.forEach((row, i) => row.forEach((_, j) => { if (counts[i][j] > 1) row[j] = '?'; }));
        matrix(host, 'out', result, counts);
        explanation.textContent = op === 'scatter_add'
          ? (zh ? '每个 src 元素累加到指定目标，结果包含 base 的初始值。' : 'Source elements add into their destinations, including the initial base value.')
          : (zh ? '被写入的位置由 src 覆盖，其他位置保留 base。问号表示接口未指定的竞争写入结果。' : 'Source values overwrite addressed positions; other positions retain base. A question mark denotes an unspecified overwrite winner.');
      }
      const right = dim === 1 ? 'i,index[i,j]' : 'index[i,j],j';
      lab.querySelector('[data-equation]').textContent = backward
        ? (op === 'gather' ? 'dx = zeros_like(x).scatter_add(dim,index,g)' : 'dsrc = g.gather(dim,index)')
        : (op === 'gather' ? `out[i,j] = x[${right}]` : `out[${right}] ${op === 'scatter_add' ? '+=' : '='} src[i,j]`);
      warning.hidden = !(op === 'scatter' && repeated);
      warning.textContent = zh
        ? '重复覆盖：前向没有固定胜出者，实现返回的 dsrc 会把梯度发给所有冲突源位置，不能视为正确的覆盖梯度。切换到 scatter_add 可表达求和。'
        : 'Repeated overwrite: forward has no guaranteed winner. The returned dsrc sends gradients to all competing sources and is not a correct overwrite derivative. Use scatter_add for summation.';
    }
    lab.querySelectorAll('select').forEach(select => select.addEventListener('change', render));
    render();
  });
})();
