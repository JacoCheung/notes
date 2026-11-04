/* Local-only tree editor. Names are always rendered as text, never HTML. */
(() => {
  'use strict';
  const app = document.querySelector('#directory-tree');
  if (!app) return;
  const tree = app.querySelector('#dt-tree');
  const output = app.querySelector('#dt-output');
  const symbolButtons = document.querySelectorAll('[data-tree-symbol]');
  const symbolStatus = document.querySelector('#dt-symbol-status');
  const storageKey = 'notes.directory-tree.v1';
  const undoStack = [], redoStack = [];
  let nextId = 1, root = { id: 0, name: 'project', children: [] };
  let selected = 0, format = 'unicode', editing = null, storageAvailable = true;
  let statusTimer, symbolTimer;
  const en = () => document.documentElement.lang === 'en';
  const t = (zh, english) => en() ? english : zh;
  const nameOf = node => node.name.trim() || t('新目录', 'new-folder');
  const clean = name => name.replace(/[\u0000-\u001f\u007f\u2028\u2029]/g, ' ');
  const button = action => app.querySelector(`[data-action="${action}"]`);

  function entries() {
    const result = [], stack = [{ node: root, parent: null }];
    while (stack.length) {
      const entry = stack.pop();
      result.push(entry);
      for (let i = entry.node.children.length - 1; i >= 0; i--)
        stack.push({ node: entry.node.children[i], parent: entry.node });
    }
    return result;
  }
  const locate = id => entries().find(entry => entry.node.id === id);
  const snapshot = () => JSON.stringify({ root, selected, nextId });
  function remember(value = snapshot()) {
    undoStack.push(value);
    if (undoStack.length > 60) undoStack.shift();
    redoStack.length = 0;
  }
  function save() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, root, format }));
      storageAvailable = true;
    } catch (_) { storageAvailable = false; }
    app.querySelector('#dt-storage').textContent = storageAvailable
      ? t('自动保存到此浏览器', 'Autosaved in this browser')
      : t('浏览器存储不可用，请复制结果保存', 'Browser storage unavailable; copy your tree to save it');
  }
  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      if (!saved || saved.version !== 1) return;
      const ids = new Set(), stack = [{ node: saved.root, depth: 0 }];
      let maxId = 0;
      while (stack.length) {
        const { node, depth } = stack.pop();
        if (!node || !Number.isSafeInteger(node.id) || node.id < 0 || ids.has(node.id) ||
            typeof node.name !== 'string' || !Array.isArray(node.children) || depth > 200 || ids.size > 10000)
          return;
        ids.add(node.id);
        maxId = Math.max(maxId, node.id);
        node.name = clean(node.name);
        node.children.forEach(child => stack.push({ node: child, depth: depth + 1 }));
      }
      root = saved.root;
      selected = root.id;
      nextId = maxId + 1;
      format = saved.format === 'ascii' ? 'ascii' : 'unicode';
    } catch (_) { /* An unavailable or invalid saved draft leaves the empty root. */ }
  }

  function treeText() {
    const symbols = format === 'ascii'
      ? { branch: '|-- ', end: '`-- ', pipe: '|   ' }
      : { branch: '├── ', end: '└── ', pipe: '│   ' };
    const lines = [nameOf(root)];
    function visit(parent, prefix) {
      parent.children.forEach((node, index) => {
        const last = index === parent.children.length - 1;
        lines.push(prefix + (last ? symbols.end : symbols.branch) + nameOf(node));
        visit(node, prefix + (last ? '    ' : symbols.pipe));
      });
    }
    visit(root, '');
    return lines.join('\n');
  }
  function updateOutput() {
    output.textContent = treeText();
    app.querySelectorAll('[data-format]').forEach(control => {
      control.setAttribute('aria-pressed', String(control.dataset.format === format));
    });
    save();
  }
  function updateControls() {
    button('sibling').disabled = selected === root.id;
    button('remove').disabled = selected === root.id;
    button('undo').disabled = !undoStack.length;
    button('redo').disabled = !redoStack.length;
    const count = entries().length;
    app.querySelector('#dt-count').textContent = t(`${count} 个节点`, `${count} node${count === 1 ? '' : 's'}`);
  }
  function announce(message) {
    clearTimeout(statusTimer);
    app.querySelector('#dt-status').textContent = message;
    statusTimer = setTimeout(() => { app.querySelector('#dt-status').textContent = ''; }, 4500);
  }
  const itemFor = id => tree.querySelector(`[data-node="${id}"]`);
  function focusNode() {
    const item = itemFor(selected);
    if (item) item.focus({ preventScroll: true });
    if (item) item.querySelector('.dt-row').scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  function select(id, focus = true) {
    if (!locate(id)) return;
    selected = id;
    tree.querySelectorAll('[role="treeitem"]').forEach(item => {
      const active = Number(item.dataset.node) === id;
      item.tabIndex = active ? 0 : -1;
      item.setAttribute('aria-selected', String(active));
    });
    updateControls();
    if (focus) focusNode();
  }
  function render(focus = false) {
    function makeItem(node, level, index, size) {
      const item = document.createElement('div');
      item.className = 'dt-item';
      item.dataset.node = node.id;
      item.setAttribute('role', 'treeitem');
      item.setAttribute('aria-level', level);
      item.setAttribute('aria-posinset', index + 1);
      item.setAttribute('aria-setsize', size);
      item.setAttribute('aria-labelledby', `dt-name-${node.id}`);
      const row = document.createElement('div');
      row.className = 'dt-row';
      const icon = document.createElement('span');
      icon.className = 'dt-node-icon';
      icon.setAttribute('aria-hidden', 'true');
      const label = document.createElement('span');
      label.className = 'dt-node-name';
      label.id = `dt-name-${node.id}`;
      label.textContent = nameOf(node);
      label.title = nameOf(node);
      row.append(icon, label);
      if (node === root) {
        const badge = document.createElement('span');
        badge.className = 'dt-root-label';
        badge.textContent = t('根节点', 'root');
        row.append(badge);
      }
      item.append(row);
      if (node.children.length) {
        item.setAttribute('aria-expanded', 'true');
        const group = document.createElement('div');
        group.className = 'dt-group';
        group.setAttribute('role', 'group');
        node.children.forEach((child, i) => group.append(makeItem(child, level + 1, i, node.children.length)));
        item.append(group);
      }
      return item;
    }
    tree.replaceChildren(makeItem(root, 1, 0, 1));
    if (!locate(selected)) selected = root.id;
    select(selected, focus);
    updateOutput();
  }
  function finishNaming(focus = false) {
    if (!editing) return;
    const { id, input, before, remembered } = editing;
    const node = locate(id).node;
    const name = clean(input.value).trim() || t('新目录', 'new-folder');
    if (name !== node.name && !remembered) remember(before);
    node.name = name;
    editing = null;
    const label = itemFor(id).querySelector('.dt-node-name');
    label.textContent = name;
    label.title = name;
    label.hidden = false;
    input.remove();
    updateControls();
    updateOutput();
    if (focus) focusNode();
  }
  function startNaming(initial) {
    finishNaming();
    const { node } = locate(selected);
    const row = itemFor(selected).querySelector('.dt-row');
    const label = row.querySelector('.dt-node-name');
    const input = document.createElement('input');
    input.className = 'dt-name-input';
    input.type = 'text';
    input.autocomplete = 'off';
    input.setAttribute('autocapitalize', 'off');
    input.setAttribute('autocorrect', 'off');
    input.spellcheck = false;
    input.setAttribute('aria-label', t('节点名称', 'Node name'));
    input.value = node.name;
    editing = { id: selected, input, before: snapshot(), remembered: false };
    label.hidden = true;
    label.after(input);
    function change() {
      if (!editing || editing.input !== input) return;
      if (!editing.remembered) { remember(editing.before); editing.remembered = true; }
      node.name = clean(input.value);
      label.textContent = nameOf(node);
      updateOutput();
      updateControls();
    }
    input.addEventListener('input', change);
    input.addEventListener('blur', () => {
      if (editing && editing.input === input) finishNaming();
    });
    input.focus({ preventScroll: true });
    input.select();
    if (initial !== undefined) { input.value = initial; change(); input.setSelectionRange(initial.length, initial.length); }
  }
  function add(child) {
    finishNaming();
    remember();
    const { node, parent } = locate(selected);
    const newNode = { id: nextId++, name: t('新目录', 'new-folder'), children: [] };
    if (child || !parent) node.children.push(newNode);
    else parent.children.splice(parent.children.indexOf(node) + 1, 0, newNode);
    selected = newNode.id;
    render(true);
    startNaming();
  }
  function remove() {
    finishNaming();
    const { node, parent } = locate(selected);
    if (!parent) return;
    remember();
    const index = parent.children.indexOf(node);
    parent.children.splice(index, 1);
    selected = (parent.children[index] || parent.children[index - 1] || parent).id;
    render(true);
    announce(t('已删除子树，可撤销', 'Subtree deleted. Undo is available.'));
  }
  function history(redo) {
    finishNaming();
    const from = redo ? redoStack : undoStack, to = redo ? undoStack : redoStack;
    if (!from.length) return;
    to.push(snapshot());
    ({ root, selected, nextId } = JSON.parse(from.pop()));
    render(true);
  }
  function preset(example) {
    finishNaming();
    remember();
    nextId = 0;
    const node = (name, children = []) => ({ id: nextId++, name, children });
    root = example
      ? node('project', [node('src', [node('components', [node('Button.tsx'), node('Card.tsx')]), node('main.ts')]), node('public', [node('logo.svg')]), node('README.md')])
      : node('project');
    selected = root.id;
    render();
    announce(t('已更新目录，可撤销', 'Tree replaced. Undo is available.'));
  }
  async function copyText(text) {
    let copied = false;
    try { await navigator.clipboard.writeText(text); copied = true; } catch (_) {
      const previous = document.activeElement;
      const input = document.createElement('textarea');
      input.value = text;
      input.className = 'dt-copy-fallback';
      document.body.append(input);
      input.select();
      try { copied = document.execCommand('copy'); } catch (_) { /* Leave manual selection available. */ }
      input.remove();
      if (previous) previous.focus({ preventScroll: true });
    }
    return copied;
  }
  function selectText(element) {
    element.focus({ preventScroll: true });
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }
  async function copy() {
    finishNaming();
    const copied = await copyText(treeText());
    if (!copied) selectText(output);
    announce(copied ? t('目录树已复制', 'Tree copied') : t('已选中结果，请按 Ctrl / ⌘ + C 复制', 'Text selected. Press Ctrl / ⌘ + C to copy.'));
  }
  symbolButtons.forEach(control => control.addEventListener('click', async () => {
    const text = control.dataset.treeSymbol;
    const copied = await copyText(text);
    clearTimeout(symbolTimer);
    symbolButtons.forEach(button => delete button.dataset.copied);
    if (copied) {
      control.dataset.copied = 'true';
      symbolStatus.textContent = text.trim()
        ? t('已复制，含尾部空格', 'Copied with trailing spaces')
        : t('已复制 4 个空格', 'Copied 4 spaces');
    } else {
      selectText(control.querySelector('code'));
      symbolStatus.textContent = t('已选中符号，请按 Ctrl / ⌘ + C 复制', 'Symbol selected. Press Ctrl / ⌘ + C to copy.');
    }
    symbolTimer = setTimeout(() => {
      delete control.dataset.copied;
      symbolStatus.textContent = '';
    }, 4500);
  }));

  app.addEventListener('click', event => {
    const control = event.target.closest('button');
    if (!control || control.disabled) return;
    if (control.dataset.format) {
      finishNaming();
      format = control.dataset.format;
      updateOutput();
      return;
    }
    const actions = { child: () => add(true), sibling: () => add(false), rename: startNaming,
      remove, undo: () => history(false), redo: () => history(true), example: () => preset(true), reset: () => preset(false), copy };
    const action = actions[control.dataset.action];
    if (action) action();
  });
  // Commit before pointer focus moves; this avoids replacing a clicked row during blur.
  tree.addEventListener('pointerdown', event => {
    if (event.target.closest('input')) return;
    const row = event.target.closest('.dt-row');
    if (!row) return;
    const id = Number(row.parentElement.dataset.node);
    event.preventDefault();
    finishNaming();
    select(id);
  });
  tree.addEventListener('click', event => {
    if (event.target.closest('input')) return;
    const row = event.target.closest('.dt-row');
    if (row) select(Number(row.parentElement.dataset.node));
  });
  tree.addEventListener('dblclick', event => {
    if (event.target.closest('input')) return;
    const row = event.target.closest('.dt-row');
    if (row) { select(Number(row.parentElement.dataset.node)); startNaming(); }
  });
  tree.addEventListener('keydown', event => {
    if (event.isComposing || event.keyCode === 229) return;
    const input = event.target.matches('input');
    const key = event.key;
    if (event.ctrlKey || event.metaKey) {
      if (!input && key.toLowerCase() === 'z') { event.preventDefault(); history(event.shiftKey); }
      return;
    }
    if (event.altKey || event.shiftKey) return;
    if (key === 'Tab' || key === 'Enter') { event.preventDefault(); add(key === 'Tab'); return; }
    if (key === 'Escape') {
      event.preventDefault();
      if (editing) finishNaming(true);
      else button('child').focus();
      return;
    }
    if (['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(key)) {
      if (input && ['Home', 'End'].includes(key)) return;
      event.preventDefault();
      finishNaming();
      const rows = entries().map(entry => entry.node);
      const index = rows.findIndex(node => node.id === selected);
      let target;
      if (key === 'ArrowUp') target = rows[index - 1];
      if (key === 'ArrowDown') target = rows[index + 1];
      if (key === 'Home') target = rows[0];
      if (key === 'End') target = rows[rows.length - 1];
      select(target ? target.id : selected);
      return;
    }
    if (input) return;
    if (key === 'F2') { event.preventDefault(); startNaming(); }
    else if (key === 'Delete' || key === 'Backspace') { event.preventDefault(); remove(); }
    else if (key.length === 1) { event.preventDefault(); startNaming(key); }
  });
  function language() {
    finishNaming();
    app.setAttribute('aria-label', t('目录树生成器', 'Directory tree generator'));
    tree.setAttribute('aria-label', t('目录结构', 'Directory structure'));
    const labels = { actions: t('节点操作', 'Node actions'), history: t('编辑历史', 'Edit history'),
      format: t('输出格式', 'Output format'), output: t('生成的目录树', 'Generated directory tree') };
    app.querySelectorAll('[data-label]').forEach(element => element.setAttribute('aria-label', labels[element.dataset.label]));
    symbolButtons.forEach(control => {
      const rowLabel = control.closest('tr').querySelector(en() ? '.lang-en' : '.lang-zh').textContent;
      const label = t(`复制 ${control.dataset.alphabet} ${rowLabel}（包含空格）`, `Copy ${control.dataset.alphabet} ${rowLabel} (including spaces)`);
      control.title = label;
      control.setAttribute('aria-label', label);
      delete control.dataset.copied;
    });
    clearTimeout(symbolTimer);
    symbolStatus.textContent = '';
    render();
  }
  load();
  language();
  new MutationObserver(language).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
})();
