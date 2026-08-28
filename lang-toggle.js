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
    const toc = document.querySelector('.layout > aside.toc, body > nav.toc, .layout > nav.toc');
    if (toc && toc.parentElement !== main) header.insertAdjacentElement('afterend', toc);
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
      if (entry.heading.offsetTop <= marker) active = entry;
    });
    tocEntries.forEach(entry => entry.link.classList.toggle('active', entry === active));
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
      addHeadingAnchors(main);
    }
    attachTocTracking();
    createBackToTop();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();
