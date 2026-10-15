"""Application provider defaults; definitions are owned by MyOwnLlmIntegrator."""
import os
from myown_llm_integrator.registry import (
    Provider, PROVIDERS, ALIASES, get_provider, is_agent_provider, model_name,
)

def graph_provider() -> str:
    # Preserve the existing openai-backend/Codex-graph arrangement unless overridden.
    selected = os.environ.get('GRAPH_LLM_PROVIDER', '').strip()
    if not selected:
        selected = os.environ.get('LLM_PROVIDER', 'codex').strip().lower()
        if selected == 'openai':
            selected = 'codex'
    return get_provider(selected).id
