"""Research scheduling/telemetry around the npm-delivered inference engine."""
from myown_llm_integrator import run_agent as _run_agent, validate_provider
from myown_llm_integrator.transport import parse_output
from myown_llm_integrator.process import DEFAULT
from research_runtime import current_context, Cancellation
from research_runtime.usage import tracked_request
from research_codex.transport import _request_slot, run_codex
from .registry import get_provider


def run_agent(prompt: str, schema: dict, cancel_event=None, *, provider=None):
    selected = get_provider(provider)
    if selected.id == 'codex':
        return run_codex(prompt, schema, cancel_event=cancel_event)
    context = current_context()
    cancel_event = Cancellation(context, cancel_event)
    with tracked_request(context) as metrics, _request_slot(
        cancel_event, prefix='AGENT', label=selected.name, provider=selected.id,
    ) as queued:
        metrics['queue_seconds'] = queued
        result, usage = _run_agent(prompt, schema, cancel_event=cancel_event,
            provider=selected.id, model=context.model if context else DEFAULT, serialize=False)
        metrics['usage'] = usage
        return result, usage
