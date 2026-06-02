// lang-toggle.js — adds a 🌐 button to each post page that flips the
// document's lang attribute between "zh-CN" and "en", and persists the
// choice to localStorage so it stays in sync with the landing-page toggle.
// CSS for the toggles lives in /assets/site.css; this script only injects
// the show/hide rule for the .lang-zh / .lang-en branches and the buttons.
// Also restores the theme choice (auto / light / dark) saved on landing.
(function () {
  // Restore theme from landing.
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') {
      document.documentElement.dataset.theme = saved;
    }
  } catch (e) {}

  let lang = 'zh';
  try {
    const saved = localStorage.getItem('lang');
    if (saved === 'en' || saved === 'zh') lang = saved;
  } catch (e) {}
  document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';

  const style = document.createElement('style');
  style.textContent =
    'html[lang="en"]  .lang-zh { display: none !important; }' +
    'html[lang="zh-CN"] .lang-en { display: none !important; }';
  document.head.appendChild(style);

  function setLangLabel(btn) {
    btn.textContent = lang === 'en' ? '中文' : 'EN';
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
