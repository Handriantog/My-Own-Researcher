"""Immutable inference settings propagated explicitly across worker boundaries."""
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import asdict, dataclass, replace
import json
import os
import re
import threading

_CONTEXT = ContextVar('research_inference_context', default=None)
ENV_KEY = 'RESEARCH_INFERENCE_CONTEXT'


@dataclass(frozen=True)
class InferenceContext:
    run_id: str
    provider: str
    model: str | None = None
    concurrency: int = 1
    usage_path: str | None = None
    stop_path: str | None = None
    graph_provider: str | None = None
    graph_model: str | None = None

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.run_id):
            raise ValueError('Invalid research run ID')
        if not isinstance(self.provider, str) or not re.fullmatch(r'[a-z0-9-]{1,64}', self.provider):
            raise ValueError('Invalid inference provider')
        if type(self.concurrency) is not int or not 1 <= self.concurrency <= 8:
            raise ValueError('Parallel AI requests must be an integer from 1 to 8')
        if self.model is not None and (not isinstance(self.model, str) or not self.model.strip()
                                      or len(self.model) > 200 or any(ord(c) < 32 for c in self.model)):
            raise ValueError('Invalid model ID')

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        return cls(**value) if value else None

    def for_provider(self, provider, model=None):
        return replace(self, provider=provider, model=self.model if provider == self.provider else model)

    def environment(self, base):
        return dict(base, **{ENV_KEY: json.dumps(self.to_dict())})

    def cancelled(self):
        return bool(self.stop_path and os.path.exists(self.stop_path))


def current_context():
    context = _CONTEXT.get()
    if context is None and os.environ.get(ENV_KEY):
        context = InferenceContext.from_dict(json.loads(os.environ[ENV_KEY]))
    return context


@contextmanager
def inference_scope(context):
    token = _CONTEXT.set(context)
    try:
        yield context
    finally:
        _CONTEXT.reset(token)


def ContextThread(*args, **kwargs):
    """Capture settings while preserving the standard Thread construction seam."""
    captured = copy_context()
    target = kwargs.get('target')
    if target is not None:
        kwargs['target'] = lambda *a, **k: captured.run(target, *a, **k)
    return threading.Thread(*args, **kwargs)


def contextual_call(function, *args, **kwargs):
    """Capture one independent context for a thread-pool submission."""
    captured = copy_context()
    return lambda: captured.run(function, *args, **kwargs)


class Cancellation:
    def __init__(self, context=None, event=None):
        self.context, self.event = context, event

    def is_set(self):
        return bool((self.event and self.event.is_set()) or
                    (self.context and self.context.cancelled()))
