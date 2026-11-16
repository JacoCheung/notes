"""Content-preservation and definition cases for the two RDMA articles."""
from html.parser import HTMLParser
import unittest

from abbreviations import annotate_abbreviations


class VisibleText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.parts = []
        self.feed(html)

    def handle_data(self, text):
        self.parts.append(text)


class AbbreviationTests(unittest.TestCase):
    def test_definition_spans_inline_markup(self):
        s = '<p><code>WQE</code>（Work Queue Element，工作队列项）。之后写 WQE。</p>'
        result = annotate_abbreviations(s, 'zh')
        self.assertIn('<code>WQE</code>（Work Queue Element', result)
        self.assertEqual(result.count('data-term="WQE"'), 1)

    def test_reverse_and_chinese_definitions(self):
        s = '<p>send queue (<code>SQ</code>); SQ. DMA（直接内存访问），再做 DMA。</p>'
        result = annotate_abbreviations(s, 'en')
        self.assertIn('(<code>SQ</code>)', result)
        self.assertIn('DMA（直接内存访问）', result)
        self.assertEqual(result.count('data-term="SQ"'), 1)
        self.assertEqual(result.count('data-term="DMA"'), 1)

    def test_full_names_do_not_gain_nested_hints(self):
        s = ('<p>MMIO（Memory-Mapped I/O）；GIN (GPU-Initiated Networking)。'
             '<code>ACD</code> 表示 Access Counters Disabled。GPU performs MMIO.</p>')
        result = annotate_abbreviations(s, 'zh')
        self.assertIn('MMIO（Memory-Mapped I/O）', result)
        self.assertIn('GIN (GPU-Initiated Networking)', result)
        self.assertIn('<code>ACD</code> 表示', result)
        self.assertEqual(result.count('<abbr '), 2)

    def test_expansion_words_in_normal_prose_stay_eligible(self):
        result = annotate_abbreviations('<p>GPUDirect RDMA carries payload.</p>', 'en')
        self.assertIn('data-term="RDMA"', result)

    def test_plural_definitions(self):
        s = '<p>CQEs (Completion Queue Entries); completion queue entries (CQEs). Poll CQEs.</p>'
        result = annotate_abbreviations(s, 'en')
        self.assertEqual(result.count('data-term="CQE"'), 1)

    def test_code_and_diagram_links_remain_unchanged(self):
        protected = ('<h2 id="GPU">GPU</h2><pre><code>GPU &lt; CPU</code></pre>'
                     '<svg><a href="/GPU"><text>GPU CQE</text></a></svg>'
                     '<p><a href="/CPU">CPU</a> <code>NCCL_GIN_TYPE</code></p>')
        self.assertEqual(annotate_abbreviations(protected, 'zh'), protected)

    def test_ascii_boundaries_preserve_identifiers(self):
        s = '<p>向GPU提交；PCIe DMA-BUF GPUs QPs。NCCL_GIN_TYPE libnccl.so GPU0</p>'
        result = annotate_abbreviations(s, 'zh')
        self.assertEqual(result.count('<abbr '), 5)
        self.assertIn('NCCL_GIN_TYPE libnccl.so GPU0', result)

    def test_component_definition_and_explicit_definition(self):
        s = ('<table><tr data-component-row="gpu"><td>GPU / VRAM</td><td>GPU memory</td>'
             '</tr></table><p data-abbr-definition="DMA">DMA uses NIC resources.</p>')
        result = annotate_abbreviations(s, 'zh')
        self.assertIn('<td>GPU / VRAM</td>', result)
        self.assertEqual(result.count('data-term="GPU"'), 1)
        self.assertNotIn('data-term="DMA"', result)
        self.assertEqual(result.count('data-term="NIC"'), 1)

    def test_visible_text_and_entities_are_preserved(self):
        s = '<p>CPU &amp; GPU，&lt;code&gt; <u>MMIO</u> <code>PCF [7:3]</code></p>'
        result = annotate_abbreviations(s, 'zh')
        self.assertEqual(''.join(VisibleText(s).parts), ''.join(VisibleText(result).parts))
        self.assertIn('&amp;', result)
        self.assertIn('&lt;code&gt;', result)

    def test_idempotent_and_localized(self):
        once = annotate_abbreviations('<p>RDMA</p>', 'zh')
        self.assertEqual(annotate_abbreviations(once, 'zh'), once)
        self.assertIn('远程直接内存访问', once)
        self.assertNotIn('远程直接内存访问', annotate_abbreviations('<p>RDMA</p>', 'en'))


if __name__ == '__main__':
    unittest.main()
