const I18N = {
  en: {
    tagline: 'systems, hardware, and ML at scale',
    nav_notes: 'blog',
    series: 'Series',
    tags: 'Tags',
    archive: 'Archive',
    loading: 'Loading posts…',
    empty: 'No posts match the current filter.',
    error: message => `Failed to load posts: ${message}`,
    clear: '× clear',
    filter_series: 'Series',
    filter_tag: 'Tag',
    filter_year: 'Archive',
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
    tags: '标签',
    archive: '归档',
    loading: '正在加载文章…',
    empty: '没有文章符合当前筛选条件。',
    error: message => `加载文章列表失败：${message}`,
    clear: '× 清除',
    filter_series: '系列',
    filter_tag: '标签',
    filter_year: '归档',
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
let filter = { type: '', value: '' };

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

function buildTagLabelMap(allPosts) {
  const labels = {};
  allPosts.forEach(post => {
    const tags = post.tags || [];
    const tagsEn = post.tags_en || [];
    tags.forEach((tag, index) => {
      labels[tag] = language === 'en' && tagsEn[index] ? tagsEn[index] : tag;
    });
  });
  return labels;
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
  document.getElementById('nav-notes').textContent = text().nav_notes;
  document.getElementById('tagline').textContent = text().tagline;
  document.getElementById('series-nav-title').textContent = text().series;
  document.getElementById('tag-nav-title').textContent = text().tags;
  document.getElementById('archive-nav-title').textContent = text().archive;
  document.getElementById('clear-filter').textContent = text().clear;

  const languageButton = document.getElementById('lang-toggle');
  languageButton.textContent = text().lang_button;
  languageButton.title = text().lang_title;
  setThemeLabel();

  const loading = document.getElementById('loading-msg');
  if (loading && !posts.length) loading.textContent = text().loading;
  if (posts.length) render();
}

function setFilter(type, value) {
  filter = { type, value };
  render();
}

function clearFilter() {
  filter = { type: '', value: '' };
  render();
}

function renderSeries() {
  const map = new Map();
  posts.forEach(post => {
    if (!post.series) return;
    if (!map.has(post.series)) {
      map.set(post.series, {
        key: post.series,
        title: post.series_title || post.series,
        titleEn: post.series_title_en || post.series_title || post.series,
        count: 0,
      });
    }
    map.get(post.series).count += 1;
  });

  const series = Array.from(map.values()).sort((left, right) =>
    left.titleEn.localeCompare(right.titleEn, 'en', { sensitivity: 'base' }) ||
    left.key.localeCompare(right.key, 'en')
  );

  const list = document.getElementById('series-nav-list');
  list.innerHTML = series.map(item => {
    const title = language === 'en' ? item.titleEn : item.title;
    const active = filter.type === 'series' && filter.value === item.key;
    return `<li><button class="series-filter${active ? ' active' : ''}" type="button" data-series="${escapeHtml(item.key)}"><span>${escapeHtml(title)}</span><span class="count">(${item.count})</span></button></li>`;
  }).join('');

  list.querySelectorAll('[data-series]').forEach(button => {
    button.addEventListener('click', () => setFilter('series', button.dataset.series));
  });
}

function renderTags() {
  const counts = new Map();
  posts.forEach(post => (post.tags || []).forEach(tag => counts.set(tag, (counts.get(tag) || 0) + 1)));
  const labels = buildTagLabelMap(posts);
  const tags = Array.from(counts.keys()).sort((left, right) =>
    (labels[left] || left).localeCompare(labels[right] || right, text().locale)
  );

  const bar = document.getElementById('filter-bar');
  bar.innerHTML = tags.map(tag => {
    const active = filter.type === 'tag' && filter.value === tag;
    return `<button class="tag-chip${active ? ' active' : ''}" type="button" data-tag="${escapeHtml(tag)}">${escapeHtml(labels[tag] || tag)} <span>${counts.get(tag)}</span></button>`;
  }).join('');

  bar.querySelectorAll('[data-tag]').forEach(button => {
    button.addEventListener('click', () => setFilter('tag', button.dataset.tag));
  });
}

function renderArchive() {
  const counts = new Map();
  posts.forEach(post => {
    const year = String(post.date || '').slice(0, 4);
    if (year) counts.set(year, (counts.get(year) || 0) + 1);
  });
  const years = Array.from(counts.keys()).sort().reverse();
  const list = document.getElementById('archive-nav-list');
  list.innerHTML = years.map(year => {
    const active = filter.type === 'year' && filter.value === year;
    return `<li><button class="series-filter archive-filter${active ? ' active' : ''}" type="button" data-year="${year}"><span>${year}</span><span class="count">(${counts.get(year)})</span></button></li>`;
  }).join('');
  list.querySelectorAll('[data-year]').forEach(button => {
    button.addEventListener('click', () => setFilter('year', button.dataset.year));
  });
}

function filteredPosts() {
  if (!filter.type) return posts;
  if (filter.type === 'series') return posts.filter(post => post.series === filter.value);
  if (filter.type === 'tag') return posts.filter(post => (post.tags || []).includes(filter.value));
  return posts.filter(post => String(post.date || '').startsWith(filter.value));
}

function renderActiveFilter() {
  const panel = document.getElementById('active-filter');
  const label = document.getElementById('active-filter-label');
  panel.classList.toggle('visible', Boolean(filter.type));
  if (!filter.type) {
    label.textContent = '';
    return;
  }

  let value = filter.value;
  let prefix = text().filter_year;
  if (filter.type === 'series') {
    const post = posts.find(item => item.series === filter.value);
    value = post ? (language === 'en' ? (post.series_title_en || post.series_title) : post.series_title) : value;
    prefix = text().filter_series;
  } else if (filter.type === 'tag') {
    value = buildTagLabelMap(posts)[filter.value] || value;
    prefix = text().filter_tag;
  }
  label.textContent = `${prefix}: ${value}`;
}

function renderPosts() {
  const visible = filteredPosts().slice().sort((left, right) =>
    right.date.localeCompare(left.date) || (left.series_order || 0) - (right.series_order || 0)
  );
  const list = document.getElementById('post-list');
  const tagLabels = buildTagLabelMap(posts);

  if (!visible.length) {
    list.innerHTML = `<div class="empty">${escapeHtml(text().empty)}</div>`;
    return;
  }

  list.innerHTML = visible.map(post => {
    const seriesTitle = language === 'en'
      ? (post.series_title_en || post.series_title || '')
      : (post.series_title || '');
    const seriesBadge = seriesTitle ? `<span class="series-badge">${escapeHtml(seriesTitle)}</span>` : '';
    const reading = pick(post, 'reading');
    return `
      <a class="post" href="posts/${escapeHtml(post.slug)}.html">
        ${seriesBadge}
        <div class="post-title">${escapeHtml(pick(post, 'title'))}</div>
        <div class="post-meta">${escapeHtml(formatDate(post.date))}${reading ? ` · ${escapeHtml(reading)}` : ''}</div>
        <div class="post-summary">${escapeHtml(pick(post, 'summary'))}</div>
        <div class="post-tags">${(post.tags || []).map(tag => `<span class="post-tag">${escapeHtml(tagLabels[tag] || tag)}</span>`).join('')}</div>
      </a>`;
  }).join('');
}

function render() {
  renderSeries();
  renderTags();
  renderArchive();
  renderActiveFilter();
  renderPosts();
}

function loadPosts() {
  fetch(`posts.json?_=${Date.now()}`)
    .then(response => {
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.json();
    })
    .then(data => {
      posts = data;
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

document.querySelectorAll('.reveal').forEach(element => element.classList.add('shown'));
applyLanguage();
loadPosts();
