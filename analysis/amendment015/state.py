"""Persistent wall clock, deadlines and immutable JSON for amendment 015."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/derived/a9/amendment015'
COMMIT = '2d7e19d20bdaacf0e6af7f7dd7b4022c1fbb339d'
START = datetime(2026, 11, 18, 15, 57, 28, tzinfo=timezone.utc)
END = START + timedelta(hours=336)


def utcnow():
    return datetime.now(timezone.utc)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')
    os.replace(temp, path)


def freeze(path, value):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise RuntimeError('FROZEN_CONFIGURATION_MISMATCH:' + str(path))
    else:
        atomic(path, value)
    return digest(path)


def ledger(stage=None, *, begin_references=False, stop=None):
    path = OUT / 'time_ledger.json'
    value = json.loads(path.read_text())
    now = utcnow()
    if value['commit'] != COMMIT or datetime.fromisoformat(value['start_utc']) != START:
        raise RuntimeError('LEDGER_START_MISMATCH')
    value.update(updated_utc=now.isoformat(), consumed_seconds=(now-START).total_seconds(),
                 remaining_seconds=max(0., (END-now).total_seconds()))
    if stage and stage != value.get('stage'):
        for event in reversed(value['stage_events']):
            if 'finished_utc' not in event:
                event.update(finished_utc=now.isoformat(), wall_seconds=(now-datetime.fromisoformat(event['started_utc'])).total_seconds())
                break
        value['stage'] = stage
        value['stage_events'].append(dict(stage=stage, started_utc=now.isoformat()))
    if begin_references and value.get('reference_preparation_start_utc') is None:
        value.update(reference_preparation_start_utc=now.isoformat(),
                     reference_deadline_utc=min(END, now+timedelta(hours=24)).isoformat())
    if stop is not None:
        value['technical_stop'] = stop
    if value.get('reference_preparation_start_utc'):
        begin = datetime.fromisoformat(value['reference_preparation_start_utc'])
        deadline = datetime.fromisoformat(value['reference_deadline_utc'])
        value.update(reference_consumed_seconds=(now-begin).total_seconds(),
                     reference_remaining_seconds=max(0., (deadline-now).total_seconds()))
    atomic(path, value)
    return value


def check_deadline(*, references=False, refresh=True):
    # Workers read deadlines; only the coordinator writes the global ledger.
    value = ledger() if refresh else json.loads((OUT/'time_ledger.json').read_text())
    now = utcnow()
    if now >= END:
        raise TimeoutError('GLOBAL_336H_DEADLINE')
    if references and (not value.get('reference_deadline_utc') or
                       now >= datetime.fromisoformat(value['reference_deadline_utc'])):
        raise TimeoutError('GLOBAL_24H_REFERENCE_DEADLINE')
    return value
