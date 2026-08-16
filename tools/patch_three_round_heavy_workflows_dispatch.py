from pathlib import Path

FILES = [
    Path('.github/workflows/hu-three-round-sequential-reference.yml'),
    Path('.github/workflows/hu-three-round-br-reference.yml'),
    Path('.github/workflows/hu-three-round-br-parallel.yml'),
    Path('.github/workflows/hu-three-round-training-work.yml'),
    Path('.github/workflows/hu-three-round-quality-work.yml'),
]

for path in FILES:
    text = path.read_text(encoding='utf-8')
    start = text.find('on:\n')
    jobs = text.find('\njobs:\n')
    if start < 0 or jobs < 0 or jobs <= start:
        raise SystemExit(f'workflow header anchor not found: {path}')
    text = text[:start] + 'on:\n  workflow_dispatch:\n' + text[jobs:]
    path.write_text(text, encoding='utf-8')
    print(f'patched {path}')

print('THREE-ROUND HEAVY WORKFLOWS -> EXPLICIT DISPATCH: APPLIED')
