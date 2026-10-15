"""Research run scheduling around the npm-delivered subscription engine."""
import os
from pathlib import Path
from contextlib import contextmanager

from myown_llm_integrator import ProviderError as CodexProviderError
from myown_llm_integrator.codex import run_codex as _run_codex
from myown_llm_integrator.process import DEFAULT, _environment, _positive_seconds
from research_runtime import current_context, Cancellation
from research_runtime.usage import tracked_request

@contextmanager
def _request_slot(cancel_event=None, *, prefix='CODEX', label='Codex', provider=None):
    from research_runtime.slots import request_slot, SlotError
    if os.name != 'posix':
        raise CodexProviderError(f'{label} provider requires macOS or Linux.')
    default = Path(__file__).resolve().parents[3] / 'backend' / 'uploads' / ('.' + prefix.lower()) / 'requests.lock'
    path = Path(os.environ.get(f'{prefix}_LOCK_PATH', str(default))).expanduser()
    if not path.is_absolute():
        raise CodexProviderError(f'{prefix}_LOCK_PATH must be an absolute path shared by all MiroFish processes.')
    timeout = _positive_seconds(f'{prefix}_QUEUE_TIMEOUT_SECONDS', '600')
    try:
        with request_slot(current_context(), provider or prefix.lower(), path=path,
                          timeout=timeout, cancel_event=cancel_event) as queued:
            yield queued
    except SlotError as error:
        raise CodexProviderError(str(error)) from error


def run_codex(prompt: str, schema: dict, cancel_event=None):
    context = current_context()
    cancel_event = Cancellation(context, cancel_event)
    with tracked_request(context) as metrics, _request_slot(cancel_event) as queued:
        metrics['queue_seconds'] = queued
        result, usage = _run_codex(prompt, schema, cancel_event=cancel_event,
                                  model=context.model if context else DEFAULT, serialize=False)
        metrics['usage'] = usage
        return result, usage
