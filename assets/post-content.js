// Shared code typography/highlighting and illustration geometry.
// Article files keep their original text, links and interaction handlers.
(function () {
  'use strict';

  const aliases = { py: 'python', py3: 'python', cxx: 'cpp', 'c++': 'cpp', cuda: 'cpp', cu: 'cpp',
    sh: 'bash', zsh: 'bash', shellscript: 'bash', console: 'shell', js: 'javascript', ts: 'typescript',
    html: 'xml', svg: 'xml', yml: 'yaml', toml: 'ini', text: 'plaintext', txt: 'plaintext',
    plain: 'plaintext', none: 'plaintext', output: 'plaintext', log: 'plaintext', mermaid: 'plaintext' };

  function languageFor(text, declared) {
    if (declared) return aliases[declared.toLowerCase()] || declared.toLowerCase();
    // Diagrams, call trees and terminal output are not programming languages.
    if ((text.match(/^\s*[│├└┌┐┬┴─→↓]/gm) || []).length >= 2) return 'plaintext';
    if (/^\s*(?:\d+\s+)?(?:openat|ioctl|mmap|futex|read|write)\(.*\)\s+=/m.test(text)) return 'plaintext';
    if (/^\s*\/\*[0-9a-f]+\*\/\s+(?:@!?P\d+\s+)?[A-Z][A-Z0-9.]+\s/m.test(text)) return 'sass';
    if (/^\s*(?:\.version\s+\d|\.target\s+sm_|\.(?:reg|param)\s|\.visible\s+\.entry|(?:ld|st|fence|bar|mov)\.[\w.]+\s)/m.test(text) && /%|\.entry|\.sys/.test(text)) return 'ptx';
    if (/^\s*(?:cmake_minimum_required|find_package|add_executable|target_link_libraries)\s*\(/mi.test(text)) return 'cmake';
    if (/^\s*-\s+func:|^#.*\.ya?ml\b/m.test(text)) return 'yaml';
    if (/^\s*(?:#include\s*[<"]|#define\s+|template\s*<|__(?:global|device|host)__)/m.test(text) || /\b(?:std|at|c10|torch|cutlass|cute|cuda)::\w+|\bTORCH_(?:LIBRARY|FN)/.test(text)) return 'cpp';
    if (/^\s*(?:async\s+)?def\s+\w+\s*\(|^\s*(?:from\s+[\w.]+\s+import\s|import\s+[\w.]+)|^\s*@(?:triton|cute|cuda)\./m.test(text)) return 'python';
    if (/^\s*(?:const|let|var)\s+\w+\s*=|\bfunction\s*\w*\s*\(|\b(?:document|console)\./m.test(text)) return 'javascript';
    if (/^\s*(?:pub\s+)?(?:async\s+)?fn\s+\w+|^\s*use\s+\w+::/m.test(text)) return 'rust';
    if (/^\s*(?:SELECT\s+.+\s+FROM|CREATE\s+TABLE|INSERT\s+INTO)/mi.test(text)) return 'sql';
    if (/^\s*(?:<!doctype\s+html|<\/?(?:html|head|body|div|script|style|svg|meta|link)\b)/mi.test(text)) return 'xml';
    if (/^\s*(?:diff --git |@@ [-+]\d|--- a\/)/m.test(text)) return 'diff';
    if (/^#!.*\b(?:ba|z)?sh\b|^\s*(?:\$\s+|(?:sudo|export|pip3?|python[\d.]*|torchrun|nvcc|nsys|ncu|ssh|git|cmake|make|curl|wget|nvidia-smi|adb|pkg|apt|brew|lsmod|lspci|modinfo|strace|ltrace|ls|cat|cd|echo|printf|rg|grep|sed|awk|chmod|mkdir|modprobe|numactl|srun|sbatch|docker|gcc|g\+\+|clang\+\+|termux-[\w-]+)\s)/m.test(text)) return 'bash';
    if (/\b(?:torch|triton|tl|np|plt|self|cuda|cute)\./.test(text) && /[=(\[]/.test(text)) return 'python';
    if (/^\s*(?:class\s+\w+.*:|(?:with|for|if|elif|while|try)\b.*:)/m.test(text)) return 'python';
    if (/^\s*(?:(?:static|inline|const|unsigned|extern)\s+)*(?:void|int|float|double|bool|Tensor|size_t|auto|uint\d+_t)\s+\w+|^\s*(?:class|struct|enum)\s+\w+[^\n]*\{/m.test(text) || /\b(?:cuda|nccl|nvshmem|ibv_)\w+\([^\n]*\);|\breturn\s+[^\n]+;|\bm\.(?:def|impl|fallback)\([^\n]*\);/.test(text)) return 'cpp';
    if (/^\s*[\[{]/.test(text)) {
      try { JSON.parse(text); return 'json'; } catch (_) {}
    }
    if (/^\s*\[[\w.-]+\]\s*$/m.test(text) && /^\s*[\w.-]+\s*=/m.test(text)) return 'ini';
    if (/^[\w.#:-][^\n]*\{\s*$/m.test(text) && /[\w-]+:\s*[^\n]+;/.test(text)) return 'css';
    return 'plaintext';
  }

  // Expose only the classifier to the dependency-free Node regression checks.
  if (typeof document === 'undefined') {
    if (typeof module !== 'undefined') module.exports = { languageFor };
    return;
  }
  const assetURL = new URL('.', document.currentScript.src);
  const main = document.querySelector('main.content');
  if (!main) return;
  const widgets = '.dt-app, .gs-lab, .p2p-lab, .loader-lab, .dl-lab, [data-post-format="off"]';
  const compact = '.cheatsheet-sheet, .termux-sheet, .man-sheet, .mpl-code, .p2p-code-panel';
  const mediaWidgets = `${widgets}, .cheatsheet-sheet, .termux-sheet, .man-sheet, .katex, mjx-container, .MathJax, .MathJax_SVG, .MathJax_Display`;
  const codeState = new WeakMap();
  let highlighter = null;

  function declaredLanguage(pre, code) {
    if (pre.matches('.source-tree, .inspection-output, .trace-block, .nohighlight') || code.classList.contains('nohighlight')) return 'plaintext';
    const explicit = code.dataset.language || code.dataset.lang || pre.dataset.language || pre.dataset.lang;
    if (explicit) return explicit;
    return `${code.className} ${pre.className}`.match(/(?:language|lang)-([\w+-]+)/)?.[1] || '';
  }

  function prepareCode(pre) {
    if (pre.closest(widgets) || pre.matches('.mermaid')) return;
    pre.classList.add('post-code-block');
    pre.classList.toggle('post-code-compact', !!pre.closest(compact));
    if (pre.parentElement.matches('.highlight, .codehilite')) pre.parentElement.classList.add('post-code-container');
    // A focusable pre keeps long lines available to keyboard readers.
    if (!pre.hasAttribute('tabindex')) pre.tabIndex = 0;
    if (!highlighter) return;
    const code = pre.querySelector(':scope > code') || pre;
    const source = code.textContent;
    const declared = declaredLanguage(pre, code);
    const language = languageFor(source, declared);
    if (codeState.get(pre) === source + '\0' + language) return;
    codeState.set(pre, source + '\0' + language);
    pre.dataset.postLanguage = language;
    if (language === 'plaintext' || !highlighter.getLanguage(language) || source.length > 150000) {
      pre.dataset.postHighlight = 'plain';
      return;
    }
    // Already tokenized Pygments listings retain their span boundaries.
    if (pre.closest('.highlight, .codehilite') && pre.querySelector('.k, .kn, .s1, .s2')) {
      pre.dataset.postHighlight = 'existing';
      return;
    }
    const nodes = [];
    const walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement.closest('button, script, style, .annotation, .lineno, .linenos, .headerlink')) continue;
      if (node.nodeValue.trim()) nodes.push(node);
    }
    // Highlight text leaves separately so source anchors and annotations survive.
    nodes.forEach(text => {
      const result = highlighter.highlight(text.nodeValue, { language, ignoreIllegals: true });
      const template = document.createElement('template');
      template.innerHTML = result.value;
      text.replaceWith(template.content);
    });
    pre.dataset.postHighlight = 'done';
  }

  function prepareArt(art) {
    if (art.closest(mediaWidgets) || art.parentElement.closest('svg')) return;
    if (art.closest('button, nav, .diagram-toolbar, .p2p-toolbar, .sequence-header')) return;
    const tag = art.tagName.toLowerCase();
    const viewBox = tag === 'svg' ? art.viewBox?.baseVal : null;
    const nativeWidth = viewBox?.width || (tag === 'img' ? art.naturalWidth : 0) || Number(art.getAttribute('width'));
    if (nativeWidth && nativeWidth < 200) return;
    let frame = art.closest('figure, .diagram-frame, .flow-frame, .post-media');
    if (!frame) {
      const parent = art.parentElement;
      if (parent.tagName === 'DIV' && parent.children.length === 1 && parent.textContent.trim() === art.textContent.trim()) frame = parent;
      else {
        frame = document.createElement('figure');
        const child = parent.tagName === 'A' && parent.children.length === 1 ? parent : art;
        child.before(frame);
        frame.appendChild(child);
      }
    }
    frame.classList.add('post-media');
    art.classList.add('post-art');
    const viewport = art.closest('.diagram-viewport, .loader-viewport, .p2p-viewport, .gs-viewport, .trace-viewport, .sequence-viewport');
    if (viewport) viewport.classList.add('post-media-viewport');
    if (nativeWidth >= 200) {
      art.style.setProperty('--post-art-width', `${nativeWidth}px`);
      // The frame and its caption share one centered axis, with room for controls.
      frame.style.setProperty('--post-media-native-width', `${nativeWidth + 2}px`);
    }
    if (tag === 'img' && !art.complete && !art.dataset.postLoadBound) {
      art.dataset.postLoadBound = 'true';
      art.addEventListener('load', () => prepareArt(art), { once: true });
    }
    if (tag === 'object' && !art.dataset.postLoadBound) {
      art.dataset.postLoadBound = 'true';
      const readSize = () => {
        try {
          const width = art.contentDocument?.documentElement.viewBox?.baseVal.width;
          if (width >= 200) {
            art.style.setProperty('--post-art-width', `${width}px`);
            frame.style.setProperty('--post-media-native-width', `${width + 2}px`);
          }
        } catch (_) { /* The declared size remains usable for cross-origin SVGs. */ }
      };
      art.addEventListener('load', readSize);
      readSize();
    }
  }

  function refresh(root = main) {
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    if (root.matches('pre')) prepareCode(root);
    root.querySelectorAll('pre').forEach(prepareCode);
    const selector = 'svg[viewBox], img, object[type="image/svg+xml"]';
    if (root.matches(selector)) prepareArt(root);
    root.querySelectorAll(selector).forEach(prepareArt);
  }

  refresh();
  main.addEventListener('click', event => {
    const button = event.target.closest('button[data-fit], button[data-zoom], button[data-size], button[data-trace-fit]');
    if (!button) return;
    const frame = button.closest('.post-media');
    if (frame) frame.dataset.postMediaMode = (button.dataset.fit || button.dataset.zoom || button.dataset.size || button.dataset.traceFit) === 'fit' ? 'fit' : 'actual';
  });
  main.addEventListener('change', event => {
    const select = event.target.closest('.diagram-toolbar select');
    if (!select || !select.querySelector('option[value="fit"]')) return;
    const frame = select.closest('.post-media');
    if (frame) frame.dataset.postMediaMode = select.value === 'fit' ? 'fit' : 'actual';
  });
  const observer = new MutationObserver(records => {
    const roots = new Set();
    records.forEach(record => {
      const pre = record.target.parentElement?.closest('pre') || record.target.closest?.('pre');
      if (pre) roots.add(pre);
      record.addedNodes.forEach(node => { if (node.nodeType === Node.ELEMENT_NODE) roots.add(node); });
    });
    roots.forEach(refresh);
  });
  observer.observe(main, { childList: true, subtree: true, characterData: true });

  const script = document.createElement('script');
  script.src = new URL('vendor/highlightjs/highlight.min.js', assetURL).href;
  script.onload = () => {
    highlighter = window.hljs;
    highlighter.registerLanguage('ptx', hljs => ({
      name: 'PTX', contains: [hljs.C_LINE_COMMENT_MODE, hljs.C_BLOCK_COMMENT_MODE, hljs.QUOTE_STRING_MODE,
        { scope: 'variable', match: /%[A-Za-z_$][\w.$]*/ },
        { scope: 'meta', match: /\.[A-Za-z_][\w.]*/ },
        { scope: 'keyword', match: /\b(?:ld|st|mov|cvt|cvta|add|sub|mul|mad|fma|setp|selp|bra|ret|call|bar|fence|membar|atom|red|cp|wmma|mma|wgmma|tcgen05)(?:\.[\w]+)*/ },
        hljs.C_NUMBER_MODE]
    }));
    highlighter.registerLanguage('sass', hljs => ({
      name: 'SASS', contains: [hljs.C_BLOCK_COMMENT_MODE, hljs.C_LINE_COMMENT_MODE,
        { scope: 'variable', match: /\b(?:U?R\d+|RZ|U?P\d+|PT|SR_[A-Z_]+)\b/ },
        { scope: 'keyword', match: /\b[A-Z][A-Z0-9]*(?:\.[A-Z0-9]+)*\b/ },
        hljs.C_NUMBER_MODE]
    }));
    const grammar = document.createElement('script');
    grammar.src = new URL('vendor/highlightjs/cmake.min.js', assetURL).href;
    const complete = () => {
      refresh();
      document.documentElement.dataset.postContentReady = 'true';
    };
    grammar.onload = complete;
    grammar.onerror = complete;
    document.head.appendChild(grammar);
  };
  script.onerror = () => { document.documentElement.dataset.postContentReady = 'plain'; };
  document.head.appendChild(script);
})();
