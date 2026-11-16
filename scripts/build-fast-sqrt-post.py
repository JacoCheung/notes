#!/usr/bin/env python3
"""Build the bilingual fast-square-root article from prose and measured results."""
from html import escape
from pathlib import Path
import json
import re
from post_series import render_series_nav

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/special-optimization/fast-sqrt'
RESULTS = json.loads((ASSETS / 'results.json').read_text())
MEASURED = RESULTS['measurements']
REFS = json.loads((ASSETS / 'sources.json').read_text())['refs']

META = dict(
    title='快速平方根与逆平方根近似',
    title_en='Fast square roots and reciprocal square roots',
    slug='fast-square-root', date='2026-11-16',
    tags='数值计算, 浮点数, 牛顿迭代, C++',
    tags_en='Numerical Computing, Floating Point, Newton Iteration, C++',
    reading='12 分钟', reading_en='12 min',
    summary='一次整数移位与减法，就能给平方根倒数提供可用的初值。文章用浮点编码和牛顿迭代解释这一近似，并给出可运行实现、误差实测和位模式交互演示。',
    summary_en='An integer shift and subtraction can seed a reciprocal square root. Bit-level examples and Newton iteration explain the approximation, supported by runnable accuracy measurements.',
    series='special-optimization', series_title='特殊优化',
    series_title_en='Specialized Optimization', series_order='2',
)


def table(headers, rows, caption):
    cells = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return ('<div class="fs-scroll" tabindex="0" role="region" aria-label="' + escape(caption, quote=True) + '">'
            '<table><caption>' + caption + '</caption><thead><tr>' +
            ''.join(f'<th scope="col">{header}</th>' for header in headers) +
            '</tr></thead><tbody>' + cells + '</tbody></table></div>')


def percent(value, signed=False):
    return f'{value * 100:+.7f}%' if signed else f'{value * 100:.7f}%'


def bits25(lang):
    labels = ['符号', '指数 E', '小数 M'] if lang == 'zh' else ['Sign', 'Exponent E', 'Fraction M']
    return '<figure class="fs-bits"><div>' + ''.join(
        f'<span><small>{label}</small><code>{bits}</code></span>' for label, bits in zip(labels,
            ['0', '10000011', '10010000000000000000000'])
    ) + '</div><figcaption>25 = 1.5625 × 2⁴ · 0x41c80000</figcaption></figure>'


def example_table(lang):
    zh = lang == 'zh'
    sample = next(sample for sample in MEASURED['samples'] if sample['x'] == 25)
    rows = [[str(step['newton_steps']), f"{step['inverse_sqrt']['value']:.10f}",
             percent(step['inverse_sqrt']['relative_error'], True),
             f"{step['sqrt_from_product']['value']:.9f}"] for step in sample['steps']]
    return table(['迭代次数', '逆平方根 y', '相对误差', '平方根 x × y'] if zh else
                 ['Updates', 'Reciprocal root y', 'Relative error', 'Square root x × y'], rows,
                 'x = 25：逐轮结果，参考值为 0.2 与 5' if zh else 'x = 25: iteration results, with references 0.2 and 5')


def error_table(lang):
    zh = lang == 'zh'
    steps = MEASURED['exhaustive_interval']['results']['steps']
    rows = [[str(s['newton_steps']), percent(s['inverse_sqrt']['max_absolute_relative_error']),
             percent(s['sqrt_from_product']['max_absolute_relative_error'])] for s in steps]
    return table(['迭代次数', '逆平方根最大相对误差', '平方根乘积最大相对误差'] if zh else
                 ['Updates', 'Maximum reciprocal-root error', 'Maximum square-root product error'], rows,
                 '[1, 4) 全部 16,777,216 个输入的最大绝对相对误差' if zh else
                 'Maximum absolute relative error over all 16,777,216 inputs in [1, 4)')


def ftz_table(lang):
    zh = lang == 'zh'
    data = MEASURED['x86_ftz_daz_at_flt_min']
    assert data['supported']
    rows = [[('渐进下溢' if zh else 'Gradual underflow'), data['strict_xhalf_bits'],
             percent(data['strict_historical']['relative_error'], True), percent(data['strict_stable']['relative_error'], True)],
            [('次正规数清零' if zh else 'Flush subnormals to zero'), data['ftz_daz_xhalf_bits'],
             percent(data['ftz_daz_historical']['relative_error'], True), percent(data['ftz_daz_stable']['relative_error'], True)]]
    return table(['模式', '0.5 × x 的位模式', '原始排列误差', '调整排列误差'] if zh else
                 ['Mode', 'Bits of 0.5 × x', 'Historical grouping error', 'Reordered error'], rows,
                 'x = 2⁻¹²⁶，一次逆平方根迭代的相对误差' if zh else
                 'x = 2⁻¹²⁶: relative error after one reciprocal-root update')


def algorithm(lang):
    lines = (ASSETS / 'verify.cpp').read_text().splitlines()
    first = lines.index('// BEGIN ALGORITHM') + 1
    last = lines.index('// END ALGORITHM')
    code = '\n'.join(lines[first:last])
    label = f'verify.cpp · {first + 1}–{last}'
    return f'<figure><pre><code class="language-cpp">{escape(code)}</code></pre><figcaption>{label}</figcaption></figure>'


def explorer(lang):
    zh = lang == 'zh'
    title = '位模式与迭代演示' if zh else 'Bit patterns and iteration'
    hint = ('改变 x，观察整数位模式、初值和两次修正。每步按 32 位浮点数舍入。' if zh else
            'Change x to inspect the bits, seed, and two updates. Each arithmetic step rounds to binary32.')
    headers = ['迭代次数', 'y', 'y 相对误差', 'x × y', 'x × y 相对误差'] if zh else ['Updates', 'y', 'Error in y', 'x × y', 'Error in x × y']
    minimum = '最小正规数' if zh else 'Smallest normal'
    return f'''<section class="fs-explorer" data-fs-explorer data-language="{lang}" aria-labelledby="{lang}-explorer-title">
<h3 id="{lang}-explorer-title">{title}</h3><p>{hint}</p>
<form class="fs-controls"><label for="{lang}-fs-input">{'输入 x' if zh else 'Input x'}</label>
<input id="{lang}-fs-input" data-fs-input type="number" value="25" step="any" aria-describedby="{lang}-fs-message">
<button type="button" data-fs-preset="25">x = 25</button><button type="button" data-fs-preset="4">x = 4</button>
<button type="button" data-fs-preset="1.1754943508222875e-38">{minimum}</button></form>
<p class="fs-message" id="{lang}-fs-message" data-fs-message role="status" aria-live="polite"></p>
<div data-fs-results><dl class="fs-state"><dt>{'实际浮点输入' if zh else 'Rounded input'}</dt><dd data-fs-value></dd>
<dt>I = bits(x)</dt><dd data-fs-bits></dd><dt>E / M</dt><dd data-fs-fields></dd>
<dt>I &gt;&gt; 1</dt><dd data-fs-shift></dd><dt>J = 0x5f3759df − (I &gt;&gt; 1)</dt><dd data-fs-seed></dd></dl>
<div class="fs-scroll" tabindex="0" role="region" aria-label="{title}"><table><thead><tr>{''.join(f'<th scope="col">{h}</th>' for h in headers)}</tr></thead><tbody data-fs-rows></tbody></table></div></div>
<noscript><p>{'交互需要 JavaScript；本节上方保留 x = 25 的完整计算结果。' if zh else 'The explorer uses JavaScript. The preceding table contains the complete x = 25 results.'}</p></noscript></section>'''


def environment(lang):
    env = RESULTS['environment']
    desc = ('测量环境：' if lang == 'zh' else 'Measurement environment: ')
    desc += f"{env['compiler']} · {env['cpu_model']} · {env['architecture']}. "
    desc += ('最近值舍入；主扫描启用渐进下溢。' if lang == 'zh' else 'Round to nearest; gradual underflow in the main sweep.')
    return f'<p class="fs-environment">{escape(desc)}</p>'


def references(lang):
    return '<ul class="fs-references">' + ''.join(
        f'<li><a href="{escape(ref["url"], quote=True)}">{escape(ref["label"])}</a></li>' for ref in REFS.values()) + '</ul>'


def expand(lang):
    body = (ROOT / f'scripts/content/fast-sqrt.{lang}.html').read_text()
    functions = {'bits25': bits25, 'example-table': example_table, 'error-table': error_table,
                 'ftz-table': ftz_table, 'algorithm': algorithm, 'explorer': explorer,
                 'environment': environment, 'references': references}
    # The downloadable file is complete; this command uses a C++20-capable compiler.
    command = '''c++ -O3 -std=c++20 -ffp-contract=off -fno-fast-math \\
    -Wall -Wextra -Wpedantic verify.cpp -o verify
./verify > measurements.json'''
    body = body.replace('{{build-command}}', f'<pre><code class="language-bash">{escape(command)}</code></pre>')
    body = re.sub(r'\{\{([\w-]+)\}\}', lambda m: functions[m[1]](lang), body)
    body = re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]', lambda m:
                  f'<a href="{escape(REFS[m[1]]["url"], quote=True)}">{m[2]}</a>', body)
    assert not re.search(r'\{\{[\w-]+\}\}|\[\[[\w-]+\|', body)
    return body


def main():
    for key in ['summary', 'summary_en']:
        assert not any(ch in META[key] for ch in '&<>"\'')
    zh_length = sum(0.5 if ord(ch) < 128 else 1 for ch in META['summary'])
    assert 50 <= zh_length <= 80, zh_length
    assert 20 <= len(META['summary_en'].split()) <= 30
    metadata = '\n'.join(f'<meta name="post:{k}" content="{escape(v, quote=True)}">' for k, v in META.items())
    head = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>快速平方根与逆平方根近似</title>
''' + metadata + '''
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/special-optimization/fast-sqrt/style.css?v=1">
<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','style','pre','code']}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js" defer></script>
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/special-optimization/fast-sqrt/page.js?v=1" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>
'''
    nav = render_series_nav(META, ROOT / 'posts')
    html = head + nav + '</aside><main class="content fast-sqrt-article"><div class="lang-zh">' + expand('zh') + '</div><div class="lang-en">' + expand('en') + '</div></main></div></body></html>\n'
    output = ROOT / 'posts/fast-square-root.html'
    output.write_text(html)
    print(f'Built {output.relative_to(ROOT)}; summaries: {zh_length:g} Chinese characters, {len(META["summary_en"].split())} English words')


if __name__ == '__main__':
    main()
