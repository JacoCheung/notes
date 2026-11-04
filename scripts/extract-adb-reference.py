#!/usr/bin/env python3
"""Extract the complete, version-pinned AOSP help into the reference's data file.

Usage: python3 scripts/extract-adb-reference.py SOURCE_DIRECTORY
SOURCE_DIRECTORY contains the upstream files named in reference.json's sources.
Downloads/caches belong outside the worktree. No Android commands are executed.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'assets/cheatsheets/adb-reference/reference.json'
STRING = re.compile(r'"(?:\\.|[^"\\])*"')
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[{}()]')
SPEC = {
    'adb': ('adb-commandline.cpp', 'static void help()', None),
    'pm': ('pm.java', 'public void onHelp()', 420),
    'art': ('ArtShellCommand.java', 'public static void printHelp(', 201),
    'links': ('domain.java', 'public void printHelp(', 66),
    'am': ('am.java', 'static void dumpHelp(', 368),
    'timer': ('AnrTimer.cpp', 'static std::string help()', None),
    'intent': ('Intent.java', 'public static void printIntentArgsHelp(', None),
}


def end_of(text, start, left='{', right='}'):
    depth = 0
    for token in TOKEN.finditer(text, start):
        if token[0] == left:
            depth += 1
        elif token[0] == right:
            depth -= 1
            if depth == 0:
                return token.end()
    raise ValueError('Unbalanced source')


def extract(text, key, signature):
    start = text.index('{', text.index(signature))
    finish = end_of(text, start)
    body = text[start + 1:finish - 1]
    line = text[:start + 1].count('\n') + 1
    if key == 'am':
        # dumping=true is dumpsys help; the else branch is the am CLI help.
        conditional = body.index('{', body.index('if (dumping)'))
        start = body.index('{', end_of(body, conditional))
        line += body[:start + 1].count('\n')
        body = body[start + 1:end_of(body, start) - 1]
    constants = {
        'DEFAULT_STAGED_READY_TIMEOUT_MS': '60000',
        'SUPPORTED_PERMISSION_FLAGS_LIST': '[review-required, revoked-compat, revoke-when-requested, user-fixed, user-set]',
        'PROFILE_DEBUG_LOCATION': '/data/misc/profman',
        'PROFILER_OUTPUT_VERSION_FLAG': '--profiler-output-version',
    }
    records = []
    if key in ('adb', 'timer', 'intent'):
        if key == 'adb':
            start = body.index('fprintf(stdout,', body.index('fprintf(stdout,') + 1)
            block_start = body.index('(', start) + 1
            block_end = end_of(body, block_start - 1, '(', ')') - 1
        elif key == 'intent':
            block_start = body.index('{', body.index('new String[]')) + 1
            block_end = end_of(body, block_start - 1) - 1
        else:
            block_start = body.index('=', body.index('static const char* msg')) + 1
            block_end = body.index(';', block_start)
        block = body[block_start:block_end]
        for token in TOKEN.finditer(block):
            if not token[0].startswith('"'):
                continue
            value = ast.literal_eval(token[0]) + ('\n' if key == 'intent' else '')
            records.append({'text': value, 'line': line + body[:block_start + token.start()].count('\n')})
    else:
        for match in re.finditer(r'\bpw\.println\(', body):
            start = match.end() - 1
            expression = body[start + 1:end_of(body, start, '(', ')') - 1]
            parts = re.findall(r'"(?:\\.|[^"\\])*"|\b[A-Z][A-Z_]+\b', expression)
            residue = expression
            value = ''
            for part in parts:
                residue = residue.replace(part, '', 1)
                value += ast.literal_eval(part) if part.startswith('"') else constants[part]
            assert not residue.replace('+', '').strip(), expression
            records.append({'text': value + '\n', 'line': line + body[:match.start()].count('\n')})
    expected = SPEC[key][2]
    if expected:
        assert len(records) == expected, (key, len(records), expected)
    # Verify resolved constants against this source snapshot.
    if key == 'pm':
        assert 'DEFAULT_STAGED_READY_TIMEOUT_MS = 60 * 1000' in text
        assert 'List.of("review-required", "revoked-compat",' in text
        assert '"revoke-when-requested", "user-fixed", "user-set")' in text
    if key == 'art':
        assert 'PROFILE_DEBUG_LOCATION = "/data/misc/profman"' in text
    if key == 'am':
        assert 'PROFILER_OUTPUT_VERSION_FLAG = "--profiler-output-version"' in text
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_directory', type=Path)
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    sections = []
    for key, (filename, signature, _) in SPEC.items():
        raw = (args.source_directory / filename).read_bytes()
        expected = data['sources'][filename]['sha256']
        assert hashlib.sha256(raw).hexdigest() == expected, f'Wrong source version: {filename}'
        records = extract(raw.decode(), key, signature)
        full = ''.join(record['text'] for record in records)
        sections.append({'id': key, 'source': filename, 'records': records,
                         'sha256': hashlib.sha256(full.encode()).hexdigest()})
        print(key, len(records), 'source strings;', len(full.splitlines()), 'help lines')
    data['sections'] = sections
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
