"""Compatibility shim supplying the reviewed model to package-owned presets."""
from myown_llm_integrator.presets import build_command as _build_command
from myown_llm_integrator.process import DEFAULT
from research_runtime import current_context


def build_command(provider, prompt, schema, root, env):
    context = current_context()
    return _build_command(provider, prompt, schema, root, env,
                          model=context.model if context else DEFAULT)
