// lang-toggle.js — adds a 🌐 button to each post page that flips the
// document's lang attribute between "zh-CN" and "en", and persists the
// choice to localStorage so it stays in sync with the landing-page toggle.
// CSS rules (also injected here) show only the matching <div class="lang-zh">
// or <div class="lang-en"> branch inside the post.
(function () {
  let lang = 'zh';
  try {
    const saved = localStorage.getItem('lang');
    if (saved === 'en' || saved === 'zh') lang = saved;
  } catch (e) {}
  document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';

  const style = document.createElement('style');
  style.textContent =
    'html[lang="en"]  .lang-zh { display: none !important; }' +
    'html[lang="zh-CN"] .lang-en { display: none !important; }' +
    '#post-lang-toggle, #post-home-link {' +
      'position:fixed;top:18px;' +
      'background:#f6f8fa;color:#1f2328;' +
      'border:1px solid #d0d7de;border-radius:6px;' +
      'padding:8px 12px;font-size:0.85rem;' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;' +
      'cursor:pointer;z-index:1000;' +
      'box-shadow:0 2px 10px rgba(0,0,0,0.12);' +
      'text-decoration:none;display:inline-block;' +
    '}' +
    '#post-lang-toggle { right:18px; }' +
    '#post-home-link   { left:18px; }' +
    '#post-lang-toggle:hover, #post-home-link:hover { border-color: #0969da; }' +
    '@media (prefers-color-scheme: dark) {' +
      '#post-lang-toggle, #post-home-link { background:#1b1f24; color:#e6e6e6; border-color:#2a2f36; }' +
      '#post-lang-toggle:hover, #post-home-link:hover { border-color: #5fb3ff; }' +
    '}';
  document.head.appendChild(style);

  function setLangLabel(btn) {
    btn.textContent = lang === 'en' ? '🌐 中文' : '🌐 EN';
    btn.title      = lang === 'en' ? '切换为中文' : 'Switch to English';
  }
  function setHomeLabel(a) {
    a.textContent = lang === 'en' ? '← Notes' : '← 笔记主页';
    a.title       = lang === 'en' ? 'Back to all posts' : '回到文章列表';
  }
  function attach() {
    // Home link (top-left)
    const home = document.createElement('a');
    home.id = 'post-home-link';
    home.href = '../index.html';
    setHomeLabel(home);
    document.body.appendChild(home);

    // Language toggle (top-right)
    const btn = document.createElement('button');
    btn.id = 'post-lang-toggle';
    setLangLabel(btn);
    btn.addEventListener('click', function () {
      lang = lang === 'en' ? 'zh' : 'en';
      document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
      setLangLabel(btn);
      setHomeLabel(home);
      try { localStorage.setItem('lang', lang); } catch (e) {}
    });
    document.body.appendChild(btn);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();
