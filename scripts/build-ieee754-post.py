#!/usr/bin/env python3
"""Publish the supplied IEEE 754 notes as a bilingual Programmer Essentials article."""
from html import escape
from pathlib import Path
import json
import re
from post_series import render_series_nav

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/programmer-essentials/ieee754'
RESULTS = json.loads((ASSETS / 'results.json').read_text())
MEASURED = RESULTS['measurements']
REFS = json.loads((ASSETS / 'sources.json').read_text())['refs']
META = dict(
    title='IEEE 754 浮点数', title_en='IEEE 754 floating-point numbers',
    slug='ieee754-floating-point', date='2026-11-16',
    tags='浮点数, IEEE 754, 数值计算, C++',
    tags_en='Floating Point, IEEE 754, Numerical Computing, C++',
    reading='8 分钟', reading_en='8 min',
    summary='八位二进制有效精度能精确表示 258，却无法精确表示 257。指数确定数值尺度，小数位决定相邻值的间隔；文中用编码表和可运行示例验证这些边界。',
    summary_en='Eight significant binary bits represent 258 exactly but not 257. Exponents set the scale, while fraction bits set spacing, demonstrated through encoding tables and runnable examples.',
    series='programmer-essentials', series_title='程序员必备清单',
    series_title_en='Programmer Essentials', series_order='3',
)


def math(tex):
    return '\\(' + tex + '\\)'


def table(headers, rows, caption, kind=''):
    return ('<div class="ieee-scroll" tabindex="0" role="region" aria-label="' + escape(caption, quote=True) + '">'
            '<table class="' + kind + '"><caption>' + caption + '</caption><thead><tr>' +
            ''.join(f'<th scope="col">{heading}</th>' for heading in headers) + '</tr></thead><tbody>' +
            ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows) + '</tbody></table></div>')


def special_table(lang):
    rows = []
    for expression, key, result in [
        ('0.0 / 0.0', 'zero_over_zero_is_nan', 'NaN'),
        ('1.0 / +0.0', 'one_over_zero_is_positive_infinity', '+∞'),
        ('0.0 × +∞', 'zero_times_infinity_is_nan', 'NaN'),
        ('+∞ − +∞', 'infinity_minus_infinity_is_nan', 'NaN'),
        ('std::fmod(+∞, 1.0)', 'fmod_infinity_one_is_nan', 'NaN'),
        ('std::fmod(1.0, 0.0)', 'fmod_one_zero_is_nan', 'NaN'),
    ]:
        assert MEASURED[key]
        rows.append([f'<code>{expression}</code>', result])
    return table(['浮点运算', '默认结果'] if lang == 'zh' else ['Floating-point operation', 'Default result'], rows,
                 '特殊值运算示例' if lang == 'zh' else 'Special-value arithmetic examples')


def bit_example(lang):
    labels = ['符号 s', '指数 E', '小数 M'] if lang == 'zh' else ['Sign s', 'Exponent E', 'Fraction M']
    return '<figure class="ieee-bits"><div>' + ''.join(
        f'<span><small>{label}</small><code>{bits}</code></span>' for label, bits in zip(labels,
            ['0', '01111111', '10000000000000000000000'])
    ) + '</div><figcaption>1.5 = 1.1₂ × 2⁰ · 0x3fc00000</figcaption></figure>'


def format_bit_layout(lang):
    zh = lang == 'zh'
    formats = [
        ('fp32', 'IEEE 754 单精度 FP32' if zh else 'IEEE 754 single precision · FP32', 8, 23, 127),
        ('fp16', 'IEEE 754 半精度 FP16' if zh else 'IEEE 754 half precision · FP16', 5, 10, 15),
        ('bf16', 'bfloat16', 8, 7, 127),
        ('tf32', 'TensorFloat-32 · 逻辑精度示意' if zh else 'TensorFloat-32 · logical precision model', 8, 10, 127),
        ('fp8-e5m2', 'FP8 E5M2', 5, 2, 15),
        ('fp8-e4m3fn', 'FP8 E4M3FN', 4, 3, 7),
        ('fp24', 'ATI / AMD FP24 · R300 / R400', 7, 16, 63),
    ]
    rows = []
    for key, title, exponent_width, fraction_width, bias in formats:
        total = 1 + exponent_width + fraction_width
        exponent = bias - 3
        fraction = 1 << (fraction_width - 2)
        fields = [('sign', '符号' if zh else 'sign', '0'),
                  ('exponent', f'指数（{exponent_width} 位）' if zh else f'exponent ({exponent_width} bits)', f'{exponent:0{exponent_width}b}'),
                  ('fraction', f'小数（{fraction_width} 位）' if zh else f'fraction ({fraction_width} bits)', f'{fraction:0{fraction_width}b}')]
        if total == 8:
            # Stack the label and bit count above the narrow FP8 fields.
            names = ['符号', '指数', '小数'] if zh else ['sign', 'exponent', 'fraction']
            fields = [(kind, f'{name}<br>{len(bits)} 位' if zh else
                       f'{name}<br>{len(bits)} {"bit" if len(bits) == 1 else "bits"}', bits)
                      for (kind, _, bits), name in zip(fields, names)]
        labels = ''.join(f'<span class="ieee-field-label ieee-field-{kind}" style="grid-column:span {len(bits)}">{label}</span>'
                         for kind, label, bits in fields)
        cells = ''.join(f'<span class="ieee-layout-bit ieee-bit-{kind}">{bit}</span>'
                        for kind, label, bits in fields for bit in bits)
        boundaries = {total - 1, total - 2, fraction_width, fraction_width - 1, 0}
        indices = ''.join(f'<span>{bit if bit in boundaries else ""}</span>' for bit in range(total - 1, -1, -1))
        description = (f'符号 0；指数 {fields[1][2]}；小数 {fields[2][2]}。' if zh else
                       f'Sign 0; exponent {fields[1][2]}; fraction {fields[2][2]}.')
        rows.append(f'''<div class="ieee-layout-row" data-format="{key}" style="--bit-count:{total}" role="group" aria-labelledby="{lang}-layout-{key}" aria-describedby="{lang}-layout-{key}-description">
<div class="ieee-layout-title" id="{lang}-layout-{key}">{title}</div>
<span class="ieee-layout-description" id="{lang}-layout-{key}-description">{description}</span>
<div class="ieee-layout-grid ieee-layout-labels" aria-hidden="true">{labels}</div>
<div class="ieee-layout-grid ieee-layout-values" aria-hidden="true">{cells}</div>
<div class="ieee-layout-grid ieee-layout-indices" aria-hidden="true">{indices}</div>
</div>''')
    caption = ('各行表示同一个数 0.15625 = 1.01₂ × 2⁻³，所有单元格等宽。TF32 的 18–0 是拼接精度字段的逻辑编号，数据使用 32 位容器，内部布局由实现决定。FP24 为历史 ATI R300 / R400 的着色器计算格式。' if zh else
               'Every row represents 0.15625 = 1.01₂ × 2⁻³ with equal-width bit cells. TF32 positions 18–0 label concatenated precision fields; data uses a 32-bit container with an implementation-defined layout. FP24 is the historical ATI R300 / R400 shader computation format.')
    caption += ' ' + ' · '.join(f'<a href="{escape(REFS[key]["url"], quote=True)}">{key.upper()}</a>' for key in ('tf32', 'fp8', 'fp24'))
    label = '浮点格式位布局对照，可横向滚动' if zh else 'Floating-point bit layouts; horizontally scrollable'
    return (f'<figure class="ieee-format-figure"><div class="ieee-layout-scroll" tabindex="0" role="region" aria-label="{label}">'
            '<div class="ieee-layout-diagram">' + ''.join(rows) + '</div></div>'
            f'<figcaption>{caption}</figcaption></figure>')


def decode_table(lang):
    zh = lang == 'zh'
    labels = ['正规数', '次正规数', '正零 / 负零', '正无穷 / 负无穷', '非数'] if zh else ['Normal', 'Subnormal', 'Signed zero', 'Signed infinity', 'NaN']
    rows = [[labels[0], math('0&lt;E&lt;E_{\\max}'), math('(-1)^s(1+M/2^m)2^{E-b}')],
            [labels[1], math('E=0,\\quad M\\ne0'), math('(-1)^s(M/2^m)2^{1-b}')],
            [labels[2], math('E=0,\\quad M=0'), math('(-1)^s0')],
            [labels[3], math('E=E_{\\max},\\quad M=0'), math('(-1)^s\\infty')],
            [labels[4], math('E=E_{\\max},\\quad M\\ne0'), 'NaN']]
    return table(['类别', '编码条件', '解码结果'] if zh else ['Category', 'Encoding condition', 'Decoded value'], rows,
                 '全 1 指数保留给特殊值的编码规则' if zh else 'Encoding with the all-ones exponent reserved for special values')


def format_table(lang):
    zh = lang == 'zh'
    formats = [
        ('FP32 / binary32', 8, 23, 127, -149, -126, '(2-2^{-23})2^{127}', 16777217),
        ('FP16 / binary16', 5, 10, 15, -24, -14, '65504', 2049),
        ('bfloat16', 8, 7, 127, -133, -126, '(2-2^{-7})2^{127}', 257),
        ('TF32（e8m10 模型）' if zh else 'TF32 (e8m10 model)', 8, 10, 127, -136, -126, '(2-2^{-10})2^{127}', 2049),
        ('FP8 E5M2', 5, 2, 15, -16, -14, '57344', 9),
        ('FP8 E4M3FN', 4, 3, 7, -9, -6, '448', 17),
    ]
    rows = [[name, f'{e} / {m}', str(b), math(f'2^{{{sub}}}'), math(f'2^{{{normal}}}'), math(maximum)]
            for name,e,m,b,sub,normal,maximum,first in formats]
    ranges = table(['格式', '指数 / 小数位', '偏置', '最小正次正规数', '最小正正规数', '最大有限值'] if zh else
                   ['Format', 'Exponent / fraction bits', 'Bias', 'Smallest positive subnormal', 'Smallest positive normal', 'Largest finite value'], rows,
                   '编码范围；TF32 一行采用 e8m10 数值模型，具体指令另看约定' if zh else
                   'Encoding ranges; the TF32 row is an e8m10 value model, subject to instruction-specific behavior', 'ieee-ranges')
    rows = [[name, str(m + 1), math(f'2^{{{-m}}}'), f'{first:,}'] for name,e,m,b,sub,normal,maximum,first in formats]
    precision = table(['格式', '有效精度 p', '1 上方间隔', '首个不能精确表示的正整数'] if zh else
                      ['Format', 'Precision p', 'Spacing above 1', 'First positive integer not represented exactly'], rows,
                      '有效精度与整数边界；TF32 按 10 位小数模型' if zh else
                      'Precision and integer boundaries; TF32 assumes a 10-bit fraction')
    return ranges + precision


def snippet(marker):
    lines = (ASSETS / 'verify.cpp').read_text().splitlines()
    start = lines.index('// BEGIN ' + marker) + 1
    end = lines.index('// END ' + marker)
    return '<figure><pre><code class="language-cpp">' + escape('\n'.join(lines[start:end])) + f'</code></pre><figcaption>verify.cpp · {start+1}–{end}</figcaption></figure>'


def classification_table(lang):
    zh = lang == 'zh'
    names = {'positive zero':'正零','negative zero':'负零','minimum subnormal':'最小正次正规数','minimum normal':'最小正正规数','one':'1','one and a half':'1.5','maximum finite':'最大有限值','positive infinity':'正无穷','quiet NaN':'静默非数'}
    categories = {'zero':'零','subnormal':'次正规数','normal':'正规数','infinity':'无穷','nan':'非数'}
    rows = [[names[s['name']] if zh else s['name'], '<code>'+s['bits']+'</code>', str(s['sign']),
             str(s['exponent_field']), str(s['fraction_field']), categories[s['category']] if zh else s['category']]
            for s in MEASURED['classification']]
    return table(['样例', '32 位模式', 's', 'E', 'M', '类别'] if zh else ['Sample', '32-bit pattern', 's', 'E', 'M', 'Category'], rows,
                 'C++ 程序的单精度分类结果' if zh else 'Binary32 classification results from the C++ program')


def bf16_table(lang):
    rows = [[str(p['input']), str(p['rounded'])] for p in MEASURED['bf16_software_quantization']]
    return table(['输入整数', '舍入到 bfloat16 精度'] if lang == 'zh' else ['Input integer', 'Rounded to bfloat16 precision'], rows,
                 '软件量化：最近值、平局取偶数' if lang == 'zh' else 'Software quantization: nearest, ties to even')


def references(lang):
    refs = {r['url']: r['label'] for r in REFS.values()}
    return '<ul class="ieee-references">' + ''.join(f'<li><a href="{escape(url,quote=True)}">{escape(label)}</a></li>' for url,label in refs.items()) + '</ul>'


def expand(lang):
    source = (ROOT / f'scripts/content/ieee754.{lang}.html').read_text()
    blocks = {'special-table': special_table, 'bit-example': bit_example, 'format-bit-layout': format_bit_layout, 'decode-table': decode_table,
              'format-table': format_table, 'classify-code': lambda _: snippet('CLASSIFY'),
              'classification-table': classification_table, 'bf16-table': bf16_table,
              'bf16-code': lambda _: snippet('BF16'), 'references': references}
    command = '''c++ -std=c++20 -O2 -ffp-contract=off -fno-fast-math verify.cpp -o verify
./verify > measurements.json'''
    env = RESULTS['environment']
    env_text = ('实测环境：' if lang=='zh' else 'Measured environment: ') + env['compiler'] + ' · ' + env['architecture'] + '.'
    source = source.replace('{{build-command}}', f'<pre><code class="language-bash">{escape(command)}</code></pre><p class="ieee-environment">{escape(env_text)}</p>')
    source = re.sub(r'\{\{([\w-]+)\}\}',lambda m:blocks[m[1]](lang),source)
    source = re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]',lambda m:f'<a href="{escape(REFS[m[1]]["url"],quote=True)}">{m[2]}</a>',source)
    assert not re.search(r'\{\{[\w-]+\}\}|\[\[[\w-]+\|',source)
    return source


def main():
    zh_length = sum(0.5 if ord(c)<128 else 1 for c in META['summary'])
    en_words = len(META['summary_en'].split())
    assert 50<=zh_length<=80 and 20<=en_words<=30,(zh_length,en_words)
    for k in ('summary','summary_en'): assert not any(c in META[k] for c in '&<>"\'')
    metadata = '\n'.join(f'<meta name="post:{k}" content="{escape(v,quote=True)}">' for k,v in META.items())
    head = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IEEE 754 浮点数</title>
''' + metadata + '''
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/programmer-essentials/ieee754/style.css?v=1">
<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','style','pre','code']}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js" defer></script>
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>
'''
    html = head + render_series_nav(META,ROOT/'posts') + '</aside><main class="content ieee-article"><div class="lang-zh">' + expand('zh') + '</div><div class="lang-en">' + expand('en') + '</div></main></div></body></html>\n'
    (ROOT/'posts/ieee754-floating-point.html').write_text(html)
    print(f'Built posts/ieee754-floating-point.html; summaries: {zh_length:g} Chinese characters, {en_words} English words')


if __name__=='__main__': main()
