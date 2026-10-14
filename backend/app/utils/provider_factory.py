"""Select local agent adapters without silently falling back to an API."""
import os
from research_runtime import current_context

from research_agents import get_provider


def agent_provider(provider=None):
    context = current_context()
    selected = provider if provider is not None else (context.provider if context else os.environ.get('LLM_PROVIDER', 'openai'))
    if selected.strip().lower() == 'openai':
        return None
    return get_provider(selected).id


def create_agent_client(provider):
    selected = agent_provider(provider)
    if selected is None:
        return None
    if selected == 'codex':
        from .codex_provider import CodexClient
        return CodexClient()
    from .agent_provider import AgentClient
    return AgentClient(selected)


def create_agent_model(provider=None):
    selected = agent_provider(provider)
    if selected is None:
        return None
    if selected == 'codex':
        from .codex_model import CodexModel
        return CodexModel()
    from .agent_model import AgentModel
    return AgentModel(selected)


def create_reviewed_openai_model():
    """A reviewed run uses one explicit API configuration for every platform."""
    context = current_context()
    if not context or context.provider != 'openai':
        return None
    from .reviewed_openai_model import ReviewedOpenAIModel
    return ReviewedOpenAIModel(context)
