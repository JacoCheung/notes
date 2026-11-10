const I18N = {
  en: {
    tagline: 'systems, hardware, and ML at scale',
    nav_notes: 'blog',
    series: 'Series',
    other_posts: 'Other posts',
    post_count: count => `${count} ${count === 1 ? 'post' : 'posts'}`,
    series_navigation: 'Blog series',
    search_label: 'Search articles',
    search_placeholder: 'Title, summary, or series name',
    search_clear: 'Clear',
    search_clear_label: 'Clear search',
    search_count: count => `${count} ${count === 1 ? 'article found' : 'articles found'}`,
    search_empty: 'No matching articles. Try fewer keywords.',
    search_empty_filtered: 'No matching articles in this series. Try fewer keywords or clear the series filter.',
    loading: 'Loading posts…',
    empty: 'No posts match the current filter.',
    error: message => `Failed to load posts: ${message}`,
    clear: '× clear',
    filter_series: 'Series',
    lang_button: '中文',
    lang_title: 'Switch to Chinese',
    theme: { auto: 'automatic', light: 'light', dark: 'dark' },
    theme_title: value => `Theme: ${value}. Switch theme.`,
    locale: 'en-US',
    html_lang: 'en',
  },
  zh: {
    tagline: '系统、硬件与大模型训练基础设施',
    nav_notes: '笔记',
    series: '系列',
    other_posts: '其他文章',
    post_count: count => `${count} 篇`,
    series_navigation: '博客系列',
    search_label: '搜索文章',
    search_placeholder: '标题、摘要或系列名称',
    search_clear: '清除',
    search_clear_label: '清除搜索',
    search_count: count => `找到 ${count} 篇文章`,
    search_empty: '没有找到匹配的文章，请尝试减少关键词。',
    search_empty_filtered: '当前系列中没有匹配的文章，请尝试减少关键词或清除系列筛选。',
    loading: '正在加载文章…',
    empty: '没有文章符合当前筛选条件。',
    error: message => `加载文章列表失败：${message}`,
    clear: '× 清除',
    filter_series: '系列',
    lang_button: 'EN',
    lang_title: '切换为英文',
    theme: { auto: '跟随系统', light: '亮色', dark: '暗色' },
    theme_title: value => `主题：${value}。切换主题。`,
    locale: 'zh-CN',
    html_lang: 'zh-CN',
  },
};

let language = 'en';
let posts = [];
let postsLoaded = false;
let selectedSeries = null;
let searchQuery = '';
let composingSearch = false;
const expandedSeries = new Set();
const collapsedSearchSeries = new Set();
let mobileNavigation = null;

try {
  const savedLanguage = localStorage.getItem('lang');
  if (savedLanguage === 'en' || savedLanguage === 'zh') language = savedLanguage;
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'light' || savedTheme === 'dark') {
    document.documentElement.dataset.theme = savedTheme;
  }
} catch (_) {}

const text = () => I18N[language];

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[character]));
}

function pick(post, field) {
  const translated = post[`${field}_en`];
  return language === 'en' && translated ? translated : (post[field] || '');
}

function formatDate(value) {
  const parts = String(value).split('-').map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return value;
  const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  return new Intl.DateTimeFormat(text().locale, {
    year: 'numeric',
    month: language === 'en' ? 'long' : 'numeric',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

function setThemeLabel() {
  const button = document.getElementById('theme-toggle');
  const current = document.documentElement.dataset.theme || 'auto';
  button.textContent = '◐';
  button.title = text().theme_title(text().theme[current]);
  button.setAttribute('aria-label', button.title);
}

function cycleTheme() {
  const current = document.documentElement.dataset.theme || '';
  const next = current === '' ? 'light' : current === 'light' ? 'dark' : '';
  if (next) {
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (_) {}
  } else {
    delete document.documentElement.dataset.theme;
    try { localStorage.removeItem('theme'); } catch (_) {}
  }
  setThemeLabel();
}

function applyLanguage() {
  document.documentElement.lang = text().html_lang;
  mobileNavigation?.setLanguage(language);
  document.getElementById('nav-notes').textContent = text().nav_notes;
  document.getElementById('tagline').textContent = text().tagline;
  document.getElementById('series-nav-title').textContent = text().series;
  document.getElementById('series-nav').setAttribute('aria-label', text().series_navigation);
  document.getElementById('clear-filter').textContent = text().clear;
  document.getElementById('search-label').textContent = text().search_label;
  document.getElementById('search-input').placeholder = text().search_placeholder;
  document.getElementById('clear-search').textContent = text().search_clear;
  document.getElementById('clear-search').setAttribute('aria-label', text().search_clear_label);

  const languageButton = document.getElementById('lang-toggle');
  languageButton.textContent = text().lang_button;
  languageButton.title = text().lang_title;
  setThemeLabel();

  const loading = document.getElementById('loading-msg');
  if (loading && !posts.length) loading.textContent = text().loading;
  if (postsLoaded) render();
}

function setFilter(value) {
  selectedSeries = value;
  if (searchQuery) collapsedSearchSeries.delete(value);
  else expandedSeries.add(value);
  render();
}

function clearFilter() {
  selectedSeries = null;
  render();
}

function normalizeSearch(value) {
  return String(value || '').normalize('NFKC').toLowerCase().trim();
}

function matchesSearch(post, terms) {
  const content = [
    post.title, post.title_en, post.summary, post.summary_en,
    post.series_title, post.series_title_en,
  ].map(normalizeSearch).join('\n');
  return terms.every(term => content.includes(term));
}

function updateSearch() {
  const input = document.getElementById('search-input');
  document.getElementById('clear-search').hidden = input.value.length === 0;
  const query = normalizeSearch(input.value).replace(/\s+/g, ' ');
  if (query === searchQuery) return;
  searchQuery = query;
  collapsedSearchSeries.clear();
  if (postsLoaded) renderPosts(groupPosts(posts));
}

function clearSearch() {
  const input = document.getElementById('search-input');
  input.value = '';
  updateSearch();
  input.focus();
}

function groupPosts(allPosts) {
  const map = new Map();
  allPosts.forEach(post => {
    const key = post.series || '';
    if (!map.has(key)) {
      map.set(key, {
        key,
        title: post.series_title || key,
        titleEn: post.series_title_en || post.series_title || key,
        posts: [],
      });
    }
    map.get(key).posts.push(post);
  });

  const groups = Array.from(map.values()).sort((left, right) => {
    if (!left.key || !right.key) return Number(!left.key) - Number(!right.key);
    const leftTitle = groupTitle(left).trim();
    const rightTitle = groupTitle(right).trim();
    const leftIsChinese = /^\p{Script=Han}/u.test(leftTitle);
    const rightIsChinese = /^\p{Script=Han}/u.test(rightTitle);
    if (leftIsChinese !== rightIsChinese) return leftIsChinese ? -1 : 1;
    const locale = leftIsChinese ? 'zh-Hans-CN-u-co-pinyin' : 'en';
    return leftTitle.localeCompare(rightTitle, locale, { sensitivity: 'base' }) ||
      left.key.localeCompare(right.key, 'en');
  });
  const order = post => Number.isFinite(post.series_order) && post.series_order > 0
    ? post.series_order : Number.MAX_SAFE_INTEGER;
  groups.forEach(group => group.posts.sort((left, right) =>
    (group.key ? order(left) - order(right) : 0) ||
    String(right.date || '').localeCompare(String(left.date || '')) ||
    String(left.slug).localeCompare(String(right.slug), 'en')
  ));
  return groups;
}

function groupTitle(group) {
  return group.key ? (language === 'en' ? group.titleEn : group.title) : text().other_posts;
}

function renderSeries(groups) {
  const list = document.getElementById('series-nav-list');
  list.innerHTML = groups.map(group => {
    const active = selectedSeries === group.key;
    return `<li><button class="series-filter${active ? ' active' : ''}" type="button" aria-pressed="${active}" data-series="${escapeHtml(group.key)}"><span>${escapeHtml(groupTitle(group))}</span><span class="count">(${group.posts.length})</span></button></li>`;
  }).join('');

  list.querySelectorAll('[data-series]').forEach(button => {
    button.addEventListener('click', () => setFilter(button.dataset.series));
  });
}

function renderActiveFilter(groups) {
  const panel = document.getElementById('active-filter');
  const label = document.getElementById('active-filter-label');
  panel.classList.toggle('visible', selectedSeries !== null);
  if (selectedSeries === null) {
    label.textContent = '';
    return;
  }

  const group = groups.find(item => item.key === selectedSeries);
  label.textContent = `${text().filter_series}: ${group ? groupTitle(group) : selectedSeries}`;
}

function renderPost(post) {
  const reading = pick(post, 'reading');
  return `
    <a class="post" href="posts/${escapeHtml(post.slug)}.html">
      <h3 class="post-title">${escapeHtml(pick(post, 'title'))}</h3>
      <div class="post-meta">${escapeHtml(formatDate(post.date))}${reading ? ` · ${escapeHtml(reading)}` : ''}</div>
      <div class="post-summary">${escapeHtml(pick(post, 'summary'))}</div>
    </a>`;
}

function renderPosts(groups) {
  let visible = selectedSeries === null ? groups : groups.filter(group => group.key === selectedSeries);
  if (searchQuery) {
    const terms = searchQuery.split(' ');
    visible = visible.map(group => ({
      ...group,
      posts: group.posts.filter(post => matchesSearch(post, terms)),
    })).filter(group => group.posts.length);
  }
  document.getElementById('search-status').textContent = searchQuery
    ? text().search_count(visible.reduce((count, group) => count + group.posts.length, 0)) : '';
  const list = document.getElementById('post-list');

  if (!visible.length) {
    const message = searchQuery
      ? (selectedSeries === null ? text().search_empty : text().search_empty_filtered)
      : text().empty;
    list.innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
    return;
  }

  list.innerHTML = visible.map((group, index) => {
    const headingId = `series-heading-${index}`;
    const panelId = `series-posts-${index}`;
    const expanded = searchQuery ? !collapsedSearchSeries.has(group.key) : expandedSeries.has(group.key);
    return `
      <section class="index-series" aria-labelledby="${headingId}" data-series-group="${escapeHtml(group.key)}">
        <header class="index-series-header">
          <h2 id="${headingId}">
            <button class="index-series-toggle" type="button" aria-expanded="${expanded}" aria-controls="${panelId}" data-toggle-series="${escapeHtml(group.key)}">
              <span class="index-series-name">${escapeHtml(groupTitle(group))}</span>
              <span class="index-series-count">${text().post_count(group.posts.length)}</span>
              <svg class="index-series-chevron" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>
            </button>
          </h2>
        </header>
        <div id="${panelId}" class="index-series-posts"${expanded ? '' : ' hidden'}>
          ${group.posts.map(renderPost).join('')}
        </div>
      </section>`;
  }).join('');

  list.querySelectorAll('[data-toggle-series]').forEach(button => {
    button.addEventListener('click', () => {
      const key = button.dataset.toggleSeries;
      const expanded = button.getAttribute('aria-expanded') !== 'true';
      if (searchQuery) {
        if (expanded) collapsedSearchSeries.delete(key);
        else collapsedSearchSeries.add(key);
      } else {
        if (expanded) expandedSeries.add(key);
        else expandedSeries.delete(key);
      }
      button.setAttribute('aria-expanded', String(expanded));
      document.getElementById(button.getAttribute('aria-controls')).hidden = !expanded;
    });
  });
}

function render() {
  const groups = groupPosts(posts);
  renderSeries(groups);
  renderActiveFilter(groups);
  renderPosts(groups);
}

function loadPosts() {
  fetch(`posts.json?_=${Date.now()}`)
    .then(response => {
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    })
    .then(data => {
      posts = data;
      postsLoaded = true;
      document.getElementById('search-input').disabled = false;
      render();
    })
    .catch(error => {
      document.getElementById('post-list').innerHTML =
        `<div class="empty">${escapeHtml(text().error(error.message || error))}</div>`;
    });
}

document.getElementById('lang-toggle').addEventListener('click', function () {
  language = language === 'en' ? 'zh' : 'en';
  try { localStorage.setItem('lang', language); } catch (_) {}
  applyLanguage();
});
document.getElementById('theme-toggle').addEventListener('click', cycleTheme);
document.getElementById('clear-filter').addEventListener('click', clearFilter);
document.getElementById('post-search').addEventListener('submit', event => event.preventDefault());
document.getElementById('clear-search').addEventListener('click', clearSearch);
const searchInput = document.getElementById('search-input');
searchInput.addEventListener('compositionstart', () => { composingSearch = true; });
searchInput.addEventListener('compositionend', () => {
  composingSearch = false;
  updateSearch();
});
searchInput.addEventListener('input', event => {
  if (!composingSearch && !event.isComposing) updateSearch();
});
searchInput.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !composingSearch && !event.isComposing) {
    event.preventDefault();
    clearSearch();
  }
});

document.querySelectorAll('.reveal').forEach(element => element.classList.add('shown'));
mobileNavigation = window.NotesNavigationDrawer?.({
  content: document.getElementById('series-nav'),
  kind: 'series',
  onSelect() {
    const list = document.getElementById('post-list');
    document.getElementById('active-filter').scrollIntoView({ block: 'start', behavior: 'instant' });
    list.querySelector('button, a')?.focus({ preventScroll: true });
  },
});
applyLanguage();
loadPosts();
