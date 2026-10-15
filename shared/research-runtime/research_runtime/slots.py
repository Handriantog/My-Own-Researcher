"""Kernel-owned cross-process slots; always acquire run then provider."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import time

from .context import Cancellation


class SlotError(RuntimeError):
    pass


@contextmanager
def request_slot(context, provider, *, path, timeout=600, cancel_event=None):
    import fcntl
    path = Path(path).expanduser()
    if not path.is_absolute():
        raise ValueError('Inference lock path must be absolute')
    path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    deadline = started + timeout
    cancelled = Cancellation(context, cancel_event)
    namespace = path.parent / (path.name + '.slots')
    namespace.mkdir(exist_ok=True)
    # Run ownership must span every provider and service on this host. Provider
    # lock overrides still isolate their legacy pools, never the reviewed run.
    run_path = Path(os.environ.get('RESEARCH_LOCK_PATH', str(
        Path(__file__).resolve().parents[3] / 'backend' / 'uploads' / '.inference' / 'requests.lock'))).expanduser()
    if not run_path.is_absolute():
        raise ValueError('RESEARCH_LOCK_PATH must be absolute')
    run_namespace = run_path.parent / (run_path.name + '.slots')
    run_namespace.mkdir(parents=True, exist_ok=True)
    provider_key = hashlib.sha256(provider.encode()).hexdigest()[:16]
    run_key = hashlib.sha256((context.run_id if context else 'legacy').encode()).hexdigest()[:24]
    descriptors = []

    def acquire(prefix, count, legacy=False, directory=namespace):
        while True:
            if cancelled.is_set():
                raise SlotError('Inference request cancelled.')
            for index in range(count):
                descriptor = os.open(path if legacy else directory / f'{prefix}.{index}', os.O_CREAT | os.O_RDWR, 0o600)
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    os.close(descriptor)
                else:
                    descriptors.append(descriptor)
                    return
            if time.monotonic() >= deadline:
                raise SlotError('Inference request queue timed out. Reduce parallel requests and retry.')
            time.sleep(min(.025, max(0, deadline - time.monotonic())))

    try:
        acquire(f'run-{run_key}', context.concurrency if context else 1,
                legacy=context is None, directory=run_namespace)
        acquire(f'provider-{provider_key}', 8)
        if cancelled.is_set():
            raise SlotError('Inference request cancelled.')
        yield time.monotonic() - started
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
