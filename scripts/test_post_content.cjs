const test = require('node:test');
const assert = require('node:assert/strict');
const { languageFor } = require('../assets/post-content.js');
const hljs = require('../assets/vendor/highlightjs/highlight.min.js');

test('explicit language declarations take precedence over content', () => {
  assert.equal(languageFor('torch.mm(x, y)', 'text'), 'plaintext');
  assert.equal(languageFor('// device code', 'cuda'), 'cpp');
  assert.equal(languageFor('x = 1', 'py'), 'python');
});

test('source languages used by the articles are recognized', () => {
  const examples = [
    ['python', 'import torch\nclass Net:\n    def forward(self, x):\n        return x + 1'],
    ['cpp', '__global__ void add(float* x) { x[threadIdx.x] += 1; }'],
    ['cpp', 'at::Tensor add(const at::Tensor& x) { return x; }'],
    ['bash', 'g++ -std=c++17 example.cpp -o example'],
    ['bash', 'nsys profile --trace=cuda,nvtx python demo.py'],
    ['cmake', 'cmake_minimum_required(VERSION 3.18)\nfind_package(Torch REQUIRED)'],
    ['ptx', 'ld.global.f32 %f1, [%rd1];\nst.global.f32 [%rd2], %f1;'],
    ['sass', '/*0000*/ MOV R1, c[0x0][0x28] ;'],
    ['yaml', '# native_functions.yaml\n- func: relu(Tensor self) -> Tensor\n  dispatch:\n    CUDA: relu'],
    ['json', '{"workers": 2, "enabled": true}'],
  ];
  for (const [language, source] of examples) assert.equal(languageFor(source), language, source);
});

test('call trees, trace logs and numeric output remain plain', () => {
  for (const source of [
    'emit_nvtx()\n  ├─ enableProfiler()\n  └─ pushNVTXCallbacks()',
    'CPU\n  → cudaLaunchKernel()\n  → GPU execution',
    '123 ioctl(3, 0xc0104600, 0x7ff) = 0',
    '[3, 0] [[3.0, 30.0], [0.0, 0.0]]\n[4, 1] [[4.0, 40.0], [1.0, 10.0]]',
  ]) assert.equal(languageFor(source), 'plaintext', source);
});

test('highlighted HTML escapes source markup and preserves text', () => {
  const source = 'const char* text = "<img src=x onerror=alert(1)>";';
  const rendered = hljs.highlight(source, { language: 'cpp' }).value;
  assert.ok(!rendered.includes('<img'));
  assert.ok(rendered.includes('&lt;img'));
  assert.ok(rendered.includes('hljs-string'));
});
