"""Build bilingual series links from article metadata, without a runtime fetch."""
from html import escape
from html.parser import HTMLParser


class PostMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            attrs = dict(attrs)
            name = attrs.get('name') or ''
            if name.startswith('post:'):
                self.meta[name[5:]] = attrs.get('content') or ''


def render_series_nav(current, posts_dir):
    """Use generated posts as the catalog; the current build overrides its entry."""
    series = current.get('series')
    if not series:
        return ''

    posts = {}
    for path in sorted(posts_dir.glob('*.html')):
        parser = PostMetadata()
        with path.open(encoding='utf-8') as source:
            for line in source:
                parser.feed(line.split('</head>', 1)[0])
                if '</head>' in line:
                    break
        post = parser.meta
        if post.get('series') == series and post.get('slug') and post.get('title'):
            posts[post['slug']] = post
    posts[current['slug']] = current

    def order(post):
        try:
            number = int(post.get('series_order', 0))
        except (ValueError, TypeError):
            number = 0
        return number, post.get('date', ''), post['title']

    def bilingual(zh, en):
        return (f'<span class="lang-zh">{escape(zh)}</span>'
                f'<span class="lang-en">{escape(en)}</span>')

    items = []
    for index, post in enumerate(sorted(posts.values(), key=order), 1):
        label = bilingual(post['title'], post.get('title_en') or post['title'])
        is_current = post['slug'] == current['slug']
        if is_current:
            entry = f'<span class="post-series-current" aria-current="page">{label}</span>'
        else:
            entry = f'<a href="{escape(post["slug"], quote=True)}.html">{label}</a>'
        items.append(f'<li class="{"current" if is_current else ""}">'
                     f'<span class="post-series-order">{index:02}</span>{entry}</li>')

    title = current.get('series_title') or series
    title_en = current.get('series_title_en') or title
    return (f'<section class="post-series-nav" data-static-series="{escape(series, quote=True)}" '
            f'aria-label="{escape(title, quote=True)}">'
            f'<div class="post-series-title">{bilingual(title, title_en)}</div>'
            '<ol class="post-series-list">' + ''.join(items) + '</ol></section>')
