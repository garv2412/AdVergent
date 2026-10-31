"""Check tracked and untracked source whitespace without traversing dependencies."""
from pathlib import Path
import subprocess

paths = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard']).decode().split('\0')
suffixes = {'.py', '.ts', '.tsx', '.css', '.json', '.toml', '.yaml', '.yml', '.ps1', '.md', '.txt', '.sql'}
issues = []
checked = 0
for value in paths:
    path = Path(value)
    if not path.is_file() or path.suffix not in suffixes:
        continue
    checked += 1
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if line != line.rstrip(' \t'):
            issues.append(f'{path}:{number}: trailing whitespace')
if issues:
    raise SystemExit('\n'.join(issues))
print(f'PASS: {checked} tracked/untracked source and document files checked directly')
