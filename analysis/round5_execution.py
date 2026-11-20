"""Shared provenance and committed-amendment checks for T15/T16."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

from a15_stability import protected_hashes
from a16_generator import ROOT, sha


def amendment006():
    name = 'analysis/emenda_A16_A9_006.md'
    revision = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', name], cwd=ROOT, text=True).strip()
    original = subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
    actual = (ROOT / name).read_bytes()
    if original.replace(b'\r\n', b'\n') != actual.replace(b'\r\n', b'\n'):
        raise RuntimeError('Amendment 006 differs from committed version')
    return dict(revision=revision, sha256=sha(ROOT / name))


def historical_hashes():
    result = protected_hashes()
    result.pop('paper/manuscript.tex')
    paths = [ROOT / 'analysis/a5_report.md', ROOT / 'analysis/a4_report.md',
             ROOT / 'analysis/preregistro_A16_A9.md', ROOT / 'analysis/a16_power_report.md']
    paths += list((ROOT / 'analysis').glob('emenda_A[45]_*.md'))
    paths += [ROOT / 'analysis' / f'emenda_A16_A9_{i:03d}.md' for i in range(1, 7)]
    original_config = json.loads((ROOT / 'data/derived/a16/power/configuration.json').read_text(encoding='utf-8'))
    for name, digest in original_config['sources'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Original scientific source changed: ' + name)
        paths.append(ROOT / name)
    for name in ('power', 'generator'):
        paths += [p for p in (ROOT / 'data/derived/a16' / name).rglob('*')
                  if p.is_file() and not p.name.endswith('.tmp') and p.suffix != '.log']
    result.update({p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)})
    return result


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n'
    for attempt in range(6):
        try:
            temporary.write_text(text, encoding='utf-8')
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.02 * 2 ** attempt)


def freeze(path, specification):
    specification['configuration_sha256'] = hashlib.sha256(
        json.dumps(specification, sort_keys=True).encode()).hexdigest()
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != specification:
            raise RuntimeError('Frozen execution configuration differs: ' + str(path))
    else:
        atomic_json(path, specification)
    return specification


def check_historical(expected):
    current = historical_hashes()
    if current != expected:
        changed = [name for name in set(current) | set(expected) if current.get(name) != expected.get(name)]
        raise RuntimeError('Historical artifacts changed: ' + ', '.join(sorted(changed)[:10]))
