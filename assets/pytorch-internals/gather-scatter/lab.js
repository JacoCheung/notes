/* Pausable rendering of the same step model used for the GIFs. */
(() => {
  'use strict';
  const SVG = 'http://www.w3.org/2000/svg';
  const assets = new URL('.', document.currentScript.src);
  document.querySelectorAll('.gs-lab').forEach((lab, id) => {
    const zh = lab.dataset.lang === 'zh';
    const host = lab.querySelector('.gs-matrices'), stage = lab.querySelector('.gs-stage');
    const play = lab.querySelector('[data-play]'), seek = lab.querySelector('[data-seek]');
    const status = lab.querySelector('[data-status]'), detail = lab.querySelector('[data-explanation]');
    const warning = lab.querySelector('[data-warning]'), motion = matchMedia('(prefers-reduced-motion: reduce)');
    let model, state, cells = new Map(), cursor = 0, elapsed = 0, running = false;
    let frame = 0, lastTime = null, progress = 0, geometry = null;
    const phaseDuration = 800;
    const svg = document.createElementNS(SVG, 'svg');
    svg.classList.add('gs-overlay'); svg.setAttribute('aria-hidden', 'true');
    svg.innerHTML = `<defs><marker id="gs-tip-${id}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="var(--gs-flow)"/></marker></defs><path class="gs-flow-path" marker-end="url(#gs-tip-${id})"/><g class="gs-token"><rect x="-19" y="-14" width="38" height="28" rx="6"/><text text-anchor="middle" y="5"></text></g>`;
    stage.append(svg);
    const path = svg.querySelector('.gs-flow-path'), token = svg.querySelector('.gs-token');
    const key = (name, position) => name + ':' + position.join(',');
    const text = value => value === null ? '·' : String(value);
    function buildMatrices() {
      host.replaceChildren(); cells = new Map();
      state.matrices.forEach(matrix => {
        const box = document.createElement('div'); box.className = 'gs-matrix'; box.dataset.matrix = matrix.key;
        const title = document.createElement('strong');
        title.textContent = matrix.key + ` · [${matrix.values.length}, ${matrix.values[0].length}]`;
        const grid = document.createElement('div'); grid.className = 'gs-cells';
        grid.style.gridTemplateColumns = `24px repeat(${matrix.values[0].length},minmax(0,1fr))`;
        grid.setAttribute('role', 'table'); grid.setAttribute('aria-label', matrix.key);
        const headers = document.createElement('div'); headers.setAttribute('role', 'row'); headers.style.display = 'contents';
        ['', ...matrix.values[0].map((_, j) => j)].forEach(value => {
          const label = document.createElement('span'); label.className = 'gs-coordinate';
          label.setAttribute('role', 'columnheader'); label.textContent = value; headers.append(label);
        });
        grid.append(headers);
        matrix.values.forEach((row, i) => {
          const rowNode = document.createElement('div'); rowNode.setAttribute('role', 'row'); rowNode.style.display = 'contents';
          const label = document.createElement('span'); label.className = 'gs-coordinate';
          label.setAttribute('role', 'rowheader'); label.textContent = i; rowNode.append(label);
          row.forEach((value, j) => {
            const cell = document.createElement('span'); cell.className = 'gs-cell'; cell.setAttribute('role', 'cell');
            cell.textContent = text(value); cell.setAttribute('aria-label', `[${i},${j}]: ${text(value)}`);
            cells.set(key(matrix.key, [i,j]), cell); rowNode.append(cell);
          });
          grid.append(rowNode);
        });
        box.append(title, grid); host.append(box);
      });
    }
    function buttonState() {
      if (!model) return;
      play.textContent = running ? (zh ? '暂停' : 'Pause') : cursor === model.total ? (zh ? '重播' : 'Replay') : cursor ? (zh ? '继续' : 'Resume') : (zh ? '播放' : 'Play');
      play.setAttribute('aria-pressed', String(running)); lab.dataset.playing = String(running);
      status.setAttribute('aria-live', running ? 'off' : 'polite');
      lab.querySelector('[data-step]').disabled = cursor === model.total;
    }
    function pause() {
      running = false; cancelAnimationFrame(frame); frame = 0; lastTime = null; buttonState();
    }
    function positionToken() {
      if (!geometry || !state.active || state.phase !== 1 || motion.matches) {token.style.display = 'none'; return;}
      token.style.display = '';
      const t = Math.max(0, Math.min(1, progress)), u = 1-t, {a,b,c,d} = geometry;
      const x = u*u*u*a.x + 3*u*u*t*b.x + 3*u*t*t*c.x + t*t*t*d.x;
      const y = u*u*u*a.y + 3*u*u*t*b.y + 3*u*t*t*c.y + t*t*t*d.y;
      token.setAttribute('transform', `translate(${x},${y})`); token.querySelector('text').textContent = state.active.value;
    }
    function drawPath() {
      geometry = null;
      if (!state || !state.active || state.phase === 0) {path.style.display = 'none'; if(state) positionToken(); return;}
      const origin = stage.getBoundingClientRect();
      const from = cells.get(key(state.inputKey, state.active.from)).getBoundingClientRect();
      const to = cells.get(key(state.outputKey, state.active.to)).getBoundingClientRect();
      const fromBox = host.querySelector(`[data-matrix="${state.inputKey}"]`).getBoundingClientRect();
      const toBox = host.querySelector(`[data-matrix="${state.outputKey}"]`).getBoundingClientRect();
      svg.setAttribute('viewBox', `0 0 ${origin.width || 1} ${origin.height || 1}`);
      // Cell highlights identify the exact coordinates; keep the moving value
      // in the gap between panels so its path never obscures other cell values.
      const below = toBox.top >= fromBox.bottom + 5;
      const a = below ? {x:fromBox.left+fromBox.width/2-origin.left,y:fromBox.bottom-origin.top+14}
        : {x:fromBox.right-origin.left+20,y:from.top+from.height/2-origin.top};
      const d = below ? {x:toBox.left+toBox.width/2-origin.left,y:toBox.top-origin.top-16}
        : {x:toBox.left-origin.left-22,y:to.top+to.height/2-origin.top};
      const b = below ? {x:a.x,y:(a.y+d.y)/2} : {x:(a.x+d.x)/2,y:a.y};
      const c = below ? {x:d.x,y:(a.y+d.y)/2} : {x:(a.x+d.x)/2,y:d.y};
      geometry = {a,b,c,d}; path.style.display = '';
      path.setAttribute('d', `M${a.x},${a.y} C${b.x},${b.y} ${c.x},${c.y} ${d.x},${d.y}`); positionToken();
    }
    function render(nextCursor, rebuild = false) {
      cursor = nextCursor; state = model.snapshot(cursor); lab.dataset.cursor = cursor;
      if (rebuild) buildMatrices();
      cells.forEach(cell => {delete cell.dataset.active; delete cell.dataset.collision;});
      state.matrices.forEach(matrix => matrix.values.forEach((row, i) => row.forEach((value, j) => {
        const cell = cells.get(key(matrix.key, [i,j])); cell.textContent = text(value);
        cell.setAttribute('aria-label', `[${i},${j}]: ${text(value)}`);
      })));
      const {op,pass,dim} = model.config;
      const labels = zh ? ['选中索引','读取源值','更新目标'] : ['Select index','Read source','Update target'];
      const active = state.active;
      if (active) {
        cells.get(key('index',active.index)).dataset.active = 'index';
        const fromCell = cells.get(key(state.inputKey,active.from)), toCell = cells.get(key(state.outputKey,active.to));
        if (state.phase >= 1) fromCell.dataset.active = 'source';
        if (state.phase >= 1) toCell.dataset.active = 'target';
        if (state.phase === 2 && pass === 'backward' && op === 'scatter') cells.get(key('dbase',active.mapped)).dataset.active = 'target';
        const address = active.index.join(','), source = `${state.inputKey}[${active.from}]`, target = `${state.outputKey}[${active.to}]`;
        const add = pass === 'backward' ? op === 'gather' : op === 'scatter_add';
        const value = state.matrices.find(m=>m.key===state.outputKey).values[active.to[0]][active.to[1]];
        const assignment = `${target} ${add ? '+=' : '='} ${source} (${active.value})`;
        lab.querySelector('[data-equation]').textContent = state.phase === 0 ? `index[${address}] = ${active.k}` : assignment;
        status.textContent = `${state.activeIndex+1}/${model.steps.length} · ${labels[state.phase]} · ${cursor}/${model.total}`;
        detail.textContent = state.phase === 0
          ? (zh ? `读取 index[${address}]=${active.k}，替换${dim===0?'行':'列'}坐标。` : `Read index[${address}]=${active.k}; replace the ${dim===0?'row':'column'} coordinate.`)
          : state.phase === 1
            ? (zh ? `沿索引找到 ${source}，取出数值 ${active.value}。` : `Follow the index to ${source} and read ${active.value}.`)
            : (zh ? `${assignment}，更新后 ${target}=${value}。` : `${assignment}; the updated ${target} is ${value}.`);
        if (state.phase===2 && pass==='backward' && op==='scatter') detail.textContent += ` dbase[${active.mapped}]=0.`;
        if (state.counts[active.mapped[0]][active.mapped[1]]>1 && state.phase===2) toCell.dataset.collision='true';
      } else {
        status.textContent = zh ? '准备就绪 · 0/18' : 'Ready · 0/18';
        lab.querySelector('[data-equation]').textContent = pass==='backward'
          ? op==='gather' ? 'dx = zeros_like(x)' : 'dsrc = · ; dbase = g'
          : op==='gather' ? 'out.shape = index.shape' : 'out = base.clone()';
        detail.textContent = zh ? '点击播放，观察每个索引对应的读写路径。· 表示尚未写入。' : 'Play to follow each indexed read and write. A dot marks a value not yet written.';
      }
      if (cursor===model.total) status.textContent = zh ? '完成 · 18/18' : 'Complete · 18/18';
      warning.hidden = !state.collision;
      warning.textContent = zh ? '重复覆盖：冲突目标显示 ?；反向展示实现返回的 dsrc，不能视为正确的覆盖梯度。'
        : 'Repeated overwrite: conflicting targets show ?. Backward shows the returned dsrc, which is not a correct overwrite derivative.';
      seek.value = cursor; seek.setAttribute('aria-valuetext',status.textContent);
      lab.querySelectorAll('[data-phase]').forEach((el,i)=>el.setAttribute('aria-current',String(i===state.phase)));
      buttonState(); drawPath();
    }
    function tick(now) {
      if (!running) return;
      if (lastTime!==null) elapsed += Math.min(now-lastTime,100)*Number(lab.querySelector('[data-speed]').value);
      lastTime=now;
      const next=Math.min(model.total,Math.floor(elapsed/phaseDuration)+1);
      progress=(elapsed%phaseDuration)/phaseDuration;
      if (next!==cursor) render(next); else positionToken();
      if (elapsed>=model.total*phaseDuration) {pause(); return;}
      frame=requestAnimationFrame(tick);
    }
    function setCursor(value) {pause(); elapsed=Math.max(0,value-1)*phaseDuration; progress=0; render(value);}
    function configure() {
      pause(); model=window.GatherScatterAnimation.create({op:lab.querySelector('[data-op]').value,
        pass:lab.querySelector('[data-pass]').value,dim:lab.querySelector('[data-dim]').value,indices:lab.querySelector('[data-indices]').value});
      elapsed=0; progress=0;
      const c=model.config;
      lab.querySelector('[data-gif]').href=new URL(`gifs/${c.op}-${c.pass}-dim${c.dim}-${c.indices}.gif`,assets).href;
      render(0,true);
    }
    play.addEventListener('click',()=>{
      if(running){pause();return;}
      if(cursor===model.total){elapsed=0;progress=0;render(0);}
      running=true;lastTime=null;buttonState();frame=requestAnimationFrame(tick);
    });
    lab.querySelector('[data-step]').addEventListener('click',()=>setCursor(Math.min(model.total,cursor+1)));
    lab.querySelector('[data-reset]').addEventListener('click',()=>setCursor(0));
    lab.querySelector('[data-end]').addEventListener('click',()=>setCursor(model.total));
    seek.addEventListener('input',()=>setCursor(Number(seek.value)));
    lab.querySelectorAll('[data-op],[data-pass],[data-dim],[data-indices]').forEach(el=>el.addEventListener('change',configure));
    document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
    new MutationObserver(()=>{if(running&&!lab.getClientRects().length)pause();}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
    new IntersectionObserver(entries=>{if(!entries[0].isIntersecting&&running)pause();}).observe(lab);
    new ResizeObserver(drawPath).observe(stage);
    motion.addEventListener('change',()=>{if(motion.matches)pause();if(state)positionToken();});
    configure();
  });
})();
