"""Durable call-level telemetry. Nested token fields are non-additive subsets."""
import json
from pathlib import Path
import sqlite3
import time


def normalize_usage(usage):
    if hasattr(usage, 'model_dump'):
        usage = usage.model_dump()
    usage = usage if isinstance(usage, dict) else {}

    def number(*values):
        for value in values:
            if type(value) is int and value >= 0:
                return value
        return None

    inp = usage.get('input_tokens_details') or usage.get('prompt_tokens_details') or {}
    out = usage.get('output_tokens_details') or usage.get('completion_tokens_details') or {}
    return {
        'input_tokens': number(usage.get('input_tokens'), usage.get('prompt_tokens')),
        'output_tokens': number(usage.get('output_tokens'), usage.get('completion_tokens')),
        'cached_tokens': number(usage.get('cached_input_tokens'), usage.get('cache_read_input_tokens'), inp.get('cached_tokens')),
        'reasoning_tokens': number(usage.get('reasoning_tokens'), out.get('reasoning_tokens')),
    }


def _connection(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return db


def record_usage(context, call_id, usage, *, queue_seconds=0, inference_seconds=0, error=False):
    if context is None or not context.usage_path:
        return
    data = dict(normalize_usage(usage), call_id=call_id, provider=context.provider,
                model=context.model, queue_seconds=queue_seconds, inference_seconds=inference_seconds,
                error=error, recorded_at=time.time())
    import_records(context.usage_path, [data])


def import_records(path, records):
    db = _connection(path)
    try:
        with db:
            for record in records:
                db.execute('INSERT OR IGNORE INTO calls VALUES (?, ?)',
                           (record['call_id'], json.dumps(record)))
    finally:
        db.close()


def usage_records(path):
    if not path or not Path(path).exists():
        return []
    db = _connection(path)
    try:
        return [json.loads(row[0]) for row in db.execute('SELECT data FROM calls ORDER BY rowid')]
    finally:
        db.close()


def usage_summary(path):
    records = usage_records(path)
    keys = ('input_tokens', 'output_tokens', 'cached_tokens', 'reasoning_tokens')
    totals = {key: sum(r[key] for r in records if r.get(key) is not None)
              if any(r.get(key) is not None for r in records) else None for key in keys}
    reported = sum(r.get('input_tokens') is not None and r.get('output_tokens') is not None for r in records)
    reasoning = sum(r.get('reasoning_tokens') is not None for r in records)
    def coverage(count):
        return 'unknown' if not count else ('complete' if count == len(records) else 'partial')
    total = sum(r['input_tokens'] + r['output_tokens'] for r in records
                if r.get('input_tokens') is not None and r.get('output_tokens') is not None) if reported else None
    return dict(totals, total_tokens=total, calls=len(records), reported_calls=reported,
                coverage=coverage(reported), reasoning_coverage=coverage(reasoning),
                queue_seconds=sum(r.get('queue_seconds', 0) for r in records),
                inference_seconds=sum(r.get('inference_seconds', 0) for r in records))


from contextlib import contextmanager
import uuid


@contextmanager
def tracked_request(context):
    metrics = {'usage': {}, 'queue_seconds': 0}
    started = time.monotonic()
    failed = True
    try:
        yield metrics
        failed = False
    finally:
        record_usage(context, uuid.uuid4().hex, metrics['usage'],
                     queue_seconds=metrics['queue_seconds'],
                     inference_seconds=max(0, time.monotonic() - started - metrics['queue_seconds']),
                     error=failed)
