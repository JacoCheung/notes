// Shared post-page shell: navigation, language/theme controls, metadata,
// heading anchors, table-of-contents state, and back-to-top behavior.
(function () {
  document.documentElement.classList.add('post-document');

  try {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
      document.documentElement.dataset.theme = savedTheme;
    }
  } catch (_) {}

  let lang = 'zh';
  try {
    const savedLang = localStorage.getItem('lang');
    if (savedLang === 'en' || savedLang === 'zh') lang = savedLang;
  } catch (_) {}

  const branchStyle = document.createElement('style');
  branchStyle.textContent =
    'html[lang="en"] .lang-zh{display:none!important}' +
    'html[lang="zh-CN"] .lang-en{display:none!important}';
  document.head.appendChild(branchStyle);

  function meta(name) {
    const element = document.querySelector(`meta[name="post:${name}"]`);
    return element ? element.content : '';
  }

  function formatDate(value) {
    if (!value) return '';
    const parts = value.split('-').map(Number);
    if (parts.length !== 3 || parts.some(Number.isNaN)) return value;
    const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
    return new Intl.DateTimeFormat(lang === 'en' ? 'en-US' : 'zh-CN', {
      year: 'numeric',
      month: lang === 'en' ? 'long' : 'numeric',
      day: 'numeric',
      timeZone: 'UTC',
    }).format(date);
  }

  function updatePostMeta() {
    const date = formatDate(meta('date'));
    const reading = lang === 'en' ? (meta('reading_en') || meta('reading')) : meta('reading');
    const value = [date, reading].filter(Boolean).join(' · ');
    document.querySelectorAll('.post-meta[data-generated="true"]').forEach(element => {
      element.textContent = value;
    });
  }

  function setThemeLabel(button) {
    const current = document.documentElement.dataset.theme || 'auto';
    const labels = lang === 'en'
      ? { auto: 'automatic', light: 'light', dark: 'dark' }
      : { auto: '跟随系统', light: '亮色', dark: '暗色' };
    button.textContent = '◐';
    button.title = lang === 'en'
      ? `Theme: ${labels[current]}. Switch theme.`
      : `主题：${labels[current]}。切换主题。`;
    button.setAttribute('aria-label', button.title);
  }

  function cycleTheme(button) {
    const current = document.documentElement.dataset.theme || '';
    const next = current === '' ? 'light' : current === 'light' ? 'dark' : '';
    if (next) {
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (_) {}
    } else {
      delete document.documentElement.dataset.theme;
      try { localStorage.removeItem('theme'); } catch (_) {}
    }
    setThemeLabel(button);
  }

  function updateLanguage(nav) {
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
    const notes = nav.querySelector('[data-nav="notes"]');
    const github = nav.querySelector('[data-nav="github"]');
    const language = nav.querySelector('#post-lang-toggle');
    const theme = nav.querySelector('#post-theme-toggle');

    notes.textContent = lang === 'en' ? 'notes' : '笔记';
    notes.title = lang === 'en' ? 'Back to all posts' : '回到文章列表';
    github.textContent = 'github';
    language.textContent = lang === 'en' ? '中文' : 'EN';
    language.title = lang === 'en' ? 'Switch to Chinese' : '切换为英文';
    setThemeLabel(theme);
    updatePostMeta();
    renderSeriesNavigation();
    updateTocLanguage();
    positionToc();
  }

  function createNavigation() {
    const shell = document.createElement('header');
    shell.className = 'site-nav';
    shell.innerHTML = `
      <nav class="site-nav-inner" aria-label="Site navigation">
        <a class="site-brand" href="../index.html"><strong>Jaco</strong> Cheung</a>
        <div class="site-nav-links">
          <a class="active" data-nav="notes" href="../index.html"></a>
          <a class="nav-github" data-nav="github" href="https://github.com/JacoCheung/notes"></a>
          <button id="post-lang-toggle" type="button"></button>
          <button class="theme-icon" id="post-theme-toggle" type="button"></button>
        </div>
      </nav>`;

    const language = shell.querySelector('#post-lang-toggle');
    const theme = shell.querySelector('#post-theme-toggle');
    language.addEventListener('click', function () {
      lang = lang === 'en' ? 'zh' : 'en';
      try { localStorage.setItem('lang', lang); } catch (_) {}
      updateLanguage(shell);
      updateActiveToc();
    });
    theme.addEventListener('click', function () { cycleTheme(theme); });
    document.body.prepend(shell);
    updateLanguage(shell);
    return shell;
  }

  function createPostHeaders(main) {
    const headings = Array.from(main.querySelectorAll('h1')).filter(heading =>
      !heading.closest('svg, .diagram-frame') && !heading.closest('.post-header')
    );

    headings.forEach(heading => {
      const header = document.createElement('header');
      header.className = 'post-header';
      heading.parentNode.insertBefore(header, heading);
      header.appendChild(heading);

      const postMeta = document.createElement('p');
      postMeta.className = 'post-meta';
      postMeta.dataset.generated = 'true';
      header.appendChild(postMeta);
    });
    updatePostMeta();
    return headings.length ? headings[0].closest('.post-header') : null;
  }

  function moveTocIntoReadingOrder(main, header) {
    if (!header || header.parentElement !== main) return;
    const toc = document.querySelector(
      '.layout > aside.toc, body > nav.toc, .layout > nav.toc, body > #toc, .layout > #toc'
    );
    if (toc && toc.parentElement !== main) header.insertAdjacentElement('afterend', toc);
  }

  let postToc = null;
  let tocCollapsed = false;
  const tocSections = [];
  const tocSectionStorageKey = 'post-toc-sections:' + (meta('slug') || location.pathname);
  let tocSectionState = {};
  try { tocCollapsed = localStorage.getItem('post-toc-collapsed') === '1'; } catch (_) {}
  try {
    const saved = JSON.parse(localStorage.getItem(tocSectionStorageKey));
    if (saved && typeof saved === 'object' && !Array.isArray(saved)) tocSectionState = saved;
  } catch (_) {}

  function isTocSectionCollapsed(section) {
    return typeof tocSectionState[section.id] === 'boolean'
      ? tocSectionState[section.id] : tocCollapsed;
  }

  function visibleTocSections() {
    return tocSections.filter(section => !section.language || section.language === lang);
  }

  function saveTocSectionState() {
    try { localStorage.setItem(tocSectionStorageKey, JSON.stringify(tocSectionState)); } catch (_) {}
  }

  function updateTocLanguage() {
    if (!postToc) return;
    postToc.setAttribute('aria-label', lang === 'en' ? 'Table of contents' : '文章目录');
    postToc.querySelector('.toc-title').textContent = lang === 'en' ? 'Contents' : '目录';
    tocSections.forEach(section => {
      const collapsed = isTocSectionCollapsed(section);
      section.subsections.hidden = collapsed;
      section.button.setAttribute('aria-expanded', String(!collapsed));
      const english = section.language ? section.language === 'en' : lang === 'en';
      const action = english ? (collapsed ? 'Expand' : 'Collapse') : (collapsed ? '展开' : '折叠');
      section.button.setAttribute('aria-label', action + (english ? ': ' : '：') + section.link.textContent);
      section.button.title = section.button.getAttribute('aria-label');
    });
    const sections = visibleTocSections();
    const anyCollapsed = sections.some(isTocSectionCollapsed);
    const button = postToc.querySelector('.post-toc-toggle');
    button.hidden = !sections.length;
    button.textContent = lang === 'en'
      ? (anyCollapsed ? 'Expand all' : 'Collapse all')
      : (anyCollapsed ? '全部展开' : '全部折叠');
    button.setAttribute('aria-expanded', String(!anyCollapsed));
    if (sections.length) button.setAttribute('aria-controls', sections.map(section => section.subsections.id).join(' '));
    else button.removeAttribute('aria-controls');
    updateActiveToc();
  }

  function positionToc() {
    if (!postToc) return;
    const header = Array.from(document.querySelectorAll('main.content .post-header'))
      .find(element => element.getClientRects().length > 0);
    if (header) header.insertAdjacentElement('afterend', postToc);
  }

  function createTableOfContents(main) {
    const headings = Array.from(main.querySelectorAll('h2, h3')).filter(heading =>
      !heading.closest('aside.toc, nav.toc, #toc, svg, .diagram-frame, .post-header')
    );
    if (!headings.length) return;

    postToc = document.querySelector('aside.toc, nav.toc, #toc');
    if (!postToc) {
      postToc = document.createElement('aside');
      postToc.className = 'toc';
      main.prepend(postToc);
    }
    const existingLabels = new Map(Array.from(postToc.querySelectorAll('a[href^="#"]'))
      .map(link => [link.getAttribute('href').slice(1), link.textContent.trim()]));
    const series = postToc.querySelector('.post-series-nav');
    // Older posts wrap their sidebar in a second, mobile-only disclosure.
    // The shared control now handles the same outline at every screen size.
    const wrapper = postToc.closest('details.article-toc');
    if (wrapper) wrapper.replaceWith(postToc);
    postToc.classList.add('toc', 'post-toc');
    postToc.classList.remove('collapsed');
    postToc.innerHTML = '<div class="post-toc-header"><div class="toc-title"></div>' +
      '<button class="post-toc-toggle" type="button"></button></div>' +
      '<div class="post-toc-body" id="post-toc-outline"></div>';
    if (series) postToc.appendChild(series);

    const lists = new Map();
    headings.forEach((heading, index) => {
      if (!heading.id) {
        let id = `post-section-${index + 1}`;
        while (document.getElementById(id)) id += '-heading';
        heading.id = id;
      }
      const branch = heading.closest('.lang-zh, .lang-en');
      const language = branch ? (branch.classList.contains('lang-en') ? 'en' : 'zh') : '';
      if (!lists.has(language)) {
        const section = document.createElement('div');
        if (language) section.className = `lang-${language}`;
        const list = document.createElement('ul');
        list.className = 'toc-sections';
        section.appendChild(list);
        postToc.querySelector('.post-toc-body').appendChild(section);
        lists.set(language, { list, chapter: null });
      }
      const state = lists.get(language);
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = '#' + heading.id;
      const label = heading.cloneNode(true);
      label.querySelectorAll('.headerlink').forEach(anchor => anchor.remove());
      link.textContent = (heading.tagName === 'H2' && existingLabels.get(heading.id)) || label.textContent.trim();
      if (heading.tagName === 'H2' || !state.chapter) {
        const row = document.createElement('div');
        row.className = 'toc-section-heading';
        row.appendChild(link);
        item.className = 'toc-section';
        item.appendChild(row);
        state.list.appendChild(item);
        state.chapter = { id: heading.id, language, item, row, link, subsections: null, button: null };
      } else {
        const chapter = state.chapter;
        if (!chapter.subsections) {
          chapter.subsections = document.createElement('ul');
          chapter.subsections.className = 'toc-subsections';
          let id = `post-toc-subsections-${tocSections.length + 1}`;
          while (document.getElementById(id)) id += '-list';
          chapter.subsections.id = id;
          chapter.item.appendChild(chapter.subsections);
          chapter.button = document.createElement('button');
          chapter.button.type = 'button';
          chapter.button.className = 'toc-section-toggle';
          chapter.button.setAttribute('aria-controls', id);
          chapter.button.innerHTML = '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false"><path d="m3 4.5 3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
          chapter.button.addEventListener('click', () => {
            tocSectionState[chapter.id] = !isTocSectionCollapsed(chapter);
            saveTocSectionState();
            updateTocLanguage();
          });
          chapter.row.appendChild(chapter.button);
          tocSections.push(chapter);
        }
        item.appendChild(link);
        chapter.subsections.appendChild(item);
      }
    });
    postToc.querySelector('.post-toc-toggle').addEventListener('click', () => {
      // A mixed outline expands on the next click; a fully expanded one collapses.
      // Keep both language branches in step when applying the global preference.
      tocCollapsed = !visibleTocSections().some(isTocSectionCollapsed);
      tocSectionState = {};
      try { localStorage.setItem('post-toc-collapsed', tocCollapsed ? '1' : '0'); } catch (_) {}
      saveTocSectionState();
      updateTocLanguage();
    });
    updateTocLanguage();
    positionToc();
  }

  let seriesNavigation = null;
  let seriesPosts = [];

  function renderSeriesNavigation() {
    if (!seriesNavigation || !seriesPosts.length) return;

    const title = seriesNavigation.querySelector('.post-series-title');
    const list = seriesNavigation.querySelector('.post-series-list');
    const currentSlug = meta('slug');
    const seriesTitle = lang === 'en'
      ? (meta('series_title_en') || meta('series_title'))
      : meta('series_title');

    seriesNavigation.setAttribute('aria-label', lang === 'en' ? 'Posts in this series' : '同系列文章');
    title.textContent = seriesTitle;
    list.replaceChildren();

    seriesPosts.forEach((post, index) => {
      const item = document.createElement('li');
      const order = document.createElement('span');
      const postTitle = lang === 'en' ? (post.title_en || post.title) : post.title;
      const isCurrent = post.slug === currentSlug;

      item.className = isCurrent ? 'current' : '';
      order.className = 'post-series-order';
      order.textContent = String(index + 1).padStart(2, '0');
      item.appendChild(order);

      if (isCurrent) {
        const current = document.createElement('span');
        current.className = 'post-series-current';
        current.textContent = postTitle;
        current.title = postTitle;
        current.setAttribute('aria-current', 'page');
        item.appendChild(current);
      } else {
        const link = document.createElement('a');
        link.href = `${post.slug}.html`;
        link.textContent = postTitle;
        link.title = postTitle;
        item.appendChild(link);
      }

      list.appendChild(item);
    });
  }

  async function createSeriesNavigation() {
    const series = meta('series');
    const toc = document.querySelector('aside.toc, nav.toc, #toc');
    if (!series || !toc) return;
    // Generated posts already include bilingual links, available without fetch.
    if (toc.querySelector('.post-series-nav[data-static-series]')) return;

    try {
      const response = await fetch(new URL('../posts.json', window.location.href));
      if (!response.ok) return;
      const posts = await response.json();
      seriesPosts = posts
        .filter(post => post.series === series)
        .sort((left, right) => {
          const order = (left.series_order || 0) - (right.series_order || 0);
          return order || left.date.localeCompare(right.date) || left.title.localeCompare(right.title);
        });
      if (!seriesPosts.length) return;

      seriesNavigation = document.createElement('section');
      seriesNavigation.className = 'post-series-nav';
      seriesNavigation.setAttribute('aria-label', lang === 'en' ? 'Posts in this series' : '同系列文章');
      seriesNavigation.innerHTML = `
        <div class="post-series-title"></div>
        <ol class="post-series-list"></ol>`;
      toc.appendChild(seriesNavigation);
      renderSeriesNavigation();
    } catch (_) {}
  }

  function addHeadingAnchors(main) {
    main.querySelectorAll('h2[id], h3[id], h4[id]').forEach(heading => {
      if (heading.querySelector(':scope > .headerlink')) return;
      const anchor = document.createElement('a');
      anchor.className = 'headerlink';
      anchor.href = `#${heading.id}`;
      anchor.title = lang === 'en' ? 'Link to this section' : '链接到本节';
      anchor.textContent = '#';
      heading.appendChild(anchor);
    });
  }

  let tocEntries = [];
  function collectTocEntries() {
    tocEntries = Array.from(document.querySelectorAll('aside.toc a[href^="#"], nav.toc a[href^="#"]'))
      .map(link => {
        const id = decodeURIComponent(link.getAttribute('href').slice(1));
        return { link, heading: document.getElementById(id) };
      })
      .filter(entry => entry.heading);
  }

  function updateActiveToc() {
    const visible = tocEntries.filter(entry => entry.heading.getClientRects().length > 0);
    if (!visible.length) return;
    const marker = window.scrollY + 120;
    let active = visible[0];
    visible.forEach(entry => {
      if (entry.heading.getBoundingClientRect().top + window.scrollY <= marker) active = entry;
    });
    const subsections = active.link.closest('.toc-subsections');
    const activeLink = subsections && subsections.hidden
      ? subsections.parentElement.querySelector('.toc-section-heading > a') : active.link;
    tocEntries.forEach(entry => entry.link.classList.toggle('active', entry.link === activeLink));
  }

  function attachTocTracking() {
    collectTocEntries();
    let scheduled = false;
    window.addEventListener('scroll', function () {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(function () {
        updateActiveToc();
        scheduled = false;
      });
    }, { passive: true });
    updateActiveToc();
  }

  function createBackToTop() {
    const button = document.createElement('button');
    button.id = 'post-back-to-top';
    button.type = 'button';
    button.textContent = '↑';
    button.title = lang === 'en' ? 'Back to top' : '回到顶部';
    button.setAttribute('aria-label', button.title);
    button.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    window.addEventListener('scroll', function () {
      button.classList.toggle('visible', window.scrollY > 420);
    }, { passive: true });
    document.body.appendChild(button);
  }

  function attach() {
    document.body.classList.add('post-page');
    createNavigation();
    const main = document.querySelector('main.content');
    if (main) {
      const header = createPostHeaders(main);
      moveTocIntoReadingOrder(main, header);
      createTableOfContents(main);
      addHeadingAnchors(main);
    }
    createSeriesNavigation();
    attachTocTracking();
    createBackToTop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();
