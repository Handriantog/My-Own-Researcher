"""Settings isolation, slot ownership and honest usage accounting."""
import multiprocessing as mp
import os
import threading
import time
from dataclasses import FrozenInstanceError

import pytest

from research_runtime import InferenceContext, current_context, inference_scope, ContextThread
from research_runtime.slots import request_slot
from research_runtime.usage import record_usage, usage_summary


def context(**overrides):
    return InferenceContext(**({'run_id': 'run-a', 'provider': 'codex', 'model': 'chosen',
                                'concurrency': 2} | overrides))


def test_context_is_immutable_and_inherited_only_by_captured_workers():
    ctx = context()
    with pytest.raises(FrozenInstanceError):
        ctx.model = 'changed'
    seen = []
    with inference_scope(ctx):
        worker = ContextThread(target=lambda: seen.append(current_context()))
    worker.start()
    worker.join()
    assert seen == [ctx]
    assert current_context() is None
    assert InferenceContext.from_dict(ctx.to_dict()) == ctx


@pytest.mark.parametrize('value', [0, 9, 1.5, True, '2'])
def test_invalid_parallelism_rejected(value):
    with pytest.raises(ValueError):
        context(concurrency=value)


def slot_worker(path, ctx, active, peak, entered, release):
    with request_slot(ctx, 'codex', path=path, timeout=3):
        with active.get_lock():
            active.value += 1
            peak.value = max(peak.value, active.value)
        entered.put(True)
        release.wait(3)
        with active.get_lock():
            active.value -= 1


def test_multiprocess_run_limit_and_process_death_release(tmp_path):
    env = mp.get_context('spawn')
    active, peak = env.Value('i', 0), env.Value('i', 0)
    entered, release = env.Queue(), env.Event()
    args = (str(tmp_path / 'override.lock'), context(), active, peak, entered, release)
    workers = [env.Process(target=slot_worker, args=args) for _ in range(3)]
    try:
        for worker in workers:
            worker.start()
        entered.get(timeout=3)
        entered.get(timeout=3)
        time.sleep(.15)
        assert peak.value == 2
        release.set()
        entered.get(timeout=3)
    finally:
        release.set()
        for worker in workers:
            worker.join(5)
            if worker.is_alive():
                worker.kill()
    assert all(w.exitcode == 0 for w in workers)
    # Killing a holder must release its kernel-owned slot.
    release.clear()
    victim = env.Process(target=slot_worker, args=(args[0], context(concurrency=1), active, peak, entered, release))
    victim.start()
    entered.get(timeout=3)
    victim.kill()
    victim.join()
    with request_slot(context(concurrency=1), 'codex', path=args[0], timeout=.2):
        pass


def test_provider_ceiling_and_legacy_pool(tmp_path):
    from contextlib import ExitStack
    path = str(tmp_path / 'shared.lock')
    with ExitStack() as stack:
        for n in range(8):
            stack.enter_context(request_slot(context(run_id=f'run-{n}'), 'codex', path=path, timeout=.2))
        with pytest.raises(RuntimeError, match='timed out'):
            with request_slot(context(run_id='ninth'), 'codex', path=path, timeout=.1):
                pass
    with request_slot(None, 'codex', path=path, timeout=.2):
        with pytest.raises(RuntimeError, match='timed out'):
            with request_slot(None, 'codex', path=path, timeout=.1):
                pass


def test_wait_can_be_cancelled_without_leaking_slot(tmp_path):
    stop = threading.Event()
    stop.set()
    path = str(tmp_path / 'cancel.lock')
    with pytest.raises(RuntimeError, match='cancel'):
        with request_slot(context(), 'codex', path=path, cancel_event=stop, timeout=.2):
            pass
    with request_slot(context(), 'codex', path=path, timeout=.2):
        pass


def test_usage_is_deduplicated_and_missing_values_stay_unknown(tmp_path):
    path = str(tmp_path / 'usage.sqlite3')
    ctx = context(usage_path=path)
    record_usage(ctx, 'call-a', {'input_tokens': 100, 'output_tokens': 20,
        'input_tokens_details': {'cached_tokens': 40}, 'output_tokens_details': {'reasoning_tokens': 5}})
    record_usage(ctx, 'call-a', {'input_tokens': 100, 'output_tokens': 20})
    record_usage(ctx, 'call-b', {})
    result = usage_summary(path)
    assert result['calls'] == 2
    assert result['input_tokens'] == 100 and result['output_tokens'] == 20
    assert result['total_tokens'] == 120  # nested counts are subsets, not additive
    assert result['cached_tokens'] == 40 and result['reasoning_tokens'] == 5
    assert result['coverage'] == 'partial'
    assert result['reasoning_coverage'] == 'partial'
    empty = usage_summary(str(tmp_path / 'none.sqlite3'))
    assert empty['total_tokens'] is None and empty['coverage'] == 'unknown'


def test_codex_requests_use_each_runs_model_and_record_usage(tmp_path, monkeypatch):
    import json
    import sys
    from research_codex.transport import run_codex
    binary = tmp_path / 'fake-codex'
    binary.write_text(f'''#!{sys.executable}
import json, pathlib, sys
args = sys.argv[1:]
if 'login' in args:
    print('Logged in using ChatGPT')
else:
    model = args[args.index('--model') + 1] if '--model' in args else 'default'
    pathlib.Path(args[args.index('-o') + 1]).write_text(json.dumps({{'model': model}}))
    print(json.dumps({{'type':'turn.completed','usage':{{'input_tokens':10,'output_tokens':2}}}}))
''')
    binary.chmod(0o700)
    monkeypatch.setenv('CODEX_BIN', str(binary))
    monkeypatch.setenv('CODEX_LOCK_PATH', str(tmp_path / 'cli.lock'))
    monkeypatch.setenv('CODEX_MODEL', 'environment-model')
    path = str(tmp_path / 'usage.sqlite3')
    with inference_scope(context(model='reviewed-model', usage_path=path)):
        result, _ = run_codex('hello', {})
    assert result['model'] == 'reviewed-model'
    assert os.environ['CODEX_MODEL'] == 'environment-model'
    assert usage_summary(path)['total_tokens'] == 12


def test_agent_presets_honor_context_without_environment_mutation(tmp_path, monkeypatch):
    from research_agents.presets import build_command
    from research_agents.registry import get_provider
    monkeypatch.setenv('AGENT_MODEL', 'environment-model')
    with inference_scope(context(provider='claude-code', model='reviewed-model')):
        args, _, _ = build_command(get_provider('claude-code'), 'hello', {}, tmp_path, {})
    assert args[args.index('--model') + 1] == 'reviewed-model'
    assert os.environ['AGENT_MODEL'] == 'environment-model'


def test_one_run_limit_is_shared_by_different_providers_and_lock_paths(tmp_path):
    ctx = context(run_id='mixed-provider-regression', concurrency=1)
    with request_slot(ctx, 'codex', path=tmp_path/'codex'/'requests.lock', timeout=.2):
        with pytest.raises(RuntimeError, match='timed out'):
            with request_slot(ctx.for_provider('claude-code'), 'claude-code',
                              path=tmp_path/'agent'/'requests.lock', timeout=.1):
                pass
