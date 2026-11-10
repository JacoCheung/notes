/* Shared step model for the page player and exported GIFs. */
(function (root, factory) {
  const model = factory();
  if (typeof module === 'object' && module.exports) module.exports = model;
  else root.GatherScatterAnimation = model;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const copy = a => a.map(row => row.slice());
  const transpose = a => a[0].map((_, j) => a.map(row => row[j]));
  const fill = (a, value) => a.map(row => row.map(() => value));
  function create(config) {
    const {op, pass, indices} = config, dim = Number(config.dim);
    if (!['gather', 'scatter', 'scatter_add'].includes(op) ||
        !['forward', 'backward'].includes(pass) || ![0, 1].includes(dim) ||
        !['unique', 'repeated'].includes(indices)) throw new Error('Invalid animation configuration');
    const orient = a => dim === 1 ? a : transpose(a);
    const index = orient(indices === 'repeated' ? [[2,0,2],[1,3,0]] : [[2,0,3],[1,3,0]]);
    const x = orient([[10,20,30,40],[50,60,70,80]]);
    const base = orient([[1,2,3,4],[5,6,7,8]]);
    const src = orient([[10,20,30],[40,50,60]]);
    const g = op === 'gather' ? orient([[1,2,3],[4,5,6]]) : copy(base);
    const backward = pass === 'backward';
    const inputKey = backward ? 'g' : op === 'gather' ? 'x' : 'src';
    const outputKey = backward ? op === 'gather' ? 'dx' : 'dsrc' : 'out';
    const input = backward ? g : op === 'gather' ? x : src;
    const initial = backward ? op === 'gather' ? fill(x, 0) : fill(src, null)
      : op === 'gather' ? fill(index, null) : copy(base);
    const steps = [], counts = fill(base, 0);
    index.forEach((row, i) => row.forEach((k, j) => {
      const mapped = dim === 0 ? [k, j] : [i, k];
      const readMapped = backward ? op !== 'gather' : op === 'gather';
      const from = readMapped ? mapped : [i, j];
      const to = readMapped ? [i, j] : mapped;
      counts[mapped[0]][mapped[1]]++;
      steps.push({index: [i, j], k, mapped, from, to, value: input[from[0]][from[1]]});
    }));
    const collision = op === 'scatter' && counts.some(row => row.some(n => n > 1));
    function snapshot(cursor) {
      cursor = Math.max(0, Math.min(steps.length * 3, Math.trunc(cursor)));
      const out = copy(initial), dbase = backward && op !== 'gather' ? copy(g) : null;
      const completed = Math.floor(cursor / 3);
      for (const step of steps.slice(0, completed)) {
        const [i, j] = step.to;
        if ((backward && op === 'gather') || (!backward && op === 'scatter_add')) out[i][j] += step.value;
        else if (!backward && op === 'scatter' && counts[i][j] > 1) out[i][j] = '?';
        else out[i][j] = step.value;
        if (dbase && op === 'scatter') dbase[step.mapped[0]][step.mapped[1]] = 0;
      }
      const activeIndex = cursor ? Math.floor((cursor - 1) / 3) : -1;
      const active = activeIndex < 0 ? null : steps[activeIndex];
      const matrices = [{key:'index',values:copy(index)}, {key:inputKey,values:copy(input)}, {key:outputKey,values:out}];
      if (dbase) matrices.push({key:'dbase',values:dbase});
      return {cursor, completed, activeIndex, active, phase:cursor ? (cursor-1)%3 : -1,
        matrices, collision, counts, inputKey, outputKey, total:steps.length*3};
    }
    return {config:{op,pass,dim,indices},steps,inputKey,outputKey,initial,counts,collision,total:steps.length*3,snapshot};
  }
  return {create};
});
