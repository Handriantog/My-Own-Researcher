"""Validated local defaults and bounded, non-inference provider discovery."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess

from myown_llm_integrator.discovery import codex_catalog as _codex_catalog, codex_cli_catalog as _codex_cli_catalog
from research_agents import get_provider, graph_provider
from research_codex.transport import _environment
from research_runtime import InferenceContext
from ..config import Config
from .research_storage import research_root, atomic_json, read_json, file_lock


def configured_provider():
    value = Config.LLM_PROVIDER
    return value if value == 'openai' else get_provider(value).id


def configured_model(provider):
    return (Config.LLM_MODEL_NAME if provider == 'openai' else
            os.environ.get('CODEX_MODEL' if provider == 'codex' else 'AGENT_MODEL')) or None


def validate_settings(value, *, provider=None):
    if not isinstance(value, dict):
        raise ValueError('Research settings must be an object')
    selected = provider or configured_provider()
    if value.get('provider', selected) != selected:
        raise ValueError('The connected provider changed. Refresh and review the settings again.')
    model = value.get('model') or None
    concurrency = value.get('concurrency', 2)
    InferenceContext('validation', selected, model, concurrency)
    depth, platform = value.get('depth', 'quick'), value.get('platform', 'reddit')
    if depth not in {'quick', 'moderate', 'full'}:
        raise ValueError('Research depth must be quick, moderate, or full')
    if platform not in {'reddit', 'twitter', 'parallel'}:
        raise ValueError('Choose Reddit, Twitter, or both platforms')
    return dict(provider=selected, model=model, concurrency=concurrency, depth=depth, platform=platform)


def load_defaults(*, provider=None, root=None):
    provider = provider or configured_provider()
    saved = read_json(research_root(root) / 'defaults.json', {})
    if saved.get('provider') != provider:
        saved = {**saved, 'provider':provider, 'model':None}
    try:
        return validate_settings(saved, provider=provider)
    except ValueError:
        return validate_settings({}, provider=provider)


def save_defaults(value, *, root=None):
    saved = validate_settings(value, provider=value.get('provider'))
    root = research_root(root)
    with file_lock(root / 'defaults.lock'):
        atomic_json(root / 'defaults.json', saved)
    return saved



def provider_metadata():
    provider = configured_provider()
    result = dict(id=provider, name='OpenAI-compatible API' if provider == 'openai' else get_provider(provider).name,
                  connection='unknown', installed=None, models=[], discovery='unsupported',
                  configured_model=configured_model(provider))
    if provider == 'openai':
        if not Config.LLM_API_KEY:
            result['connection'] = 'unavailable'
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL, timeout=5, max_retries=0)
                try:
                    models = client.models.list()
                    result['models'] = [{'id':m.id,'name':m.id,'source':'discovered'} for m in models.data[:200]]
                    result.update(connection='connected', discovery='available')
                finally:
                    client.close()
            except Exception as error:
                result['connection'] = 'unavailable' if getattr(error, 'status_code', None) == 401 else 'unknown'
                result['discovery'] = 'unavailable'
    else:
        binary = shutil.which(os.environ.get('CODEX_BIN' if provider == 'codex' else 'AGENT_BIN', get_provider(provider).executable))
        result['installed'] = bool(binary)
        if not binary:
            result['connection'] = 'unavailable'
        elif provider == 'codex':
            try:
                check = subprocess.run([binary,'--no-daemon','login','status'], capture_output=True,
                                       text=True, timeout=5, env=_environment())
                result['connection'] = 'connected' if check.returncode == 0 and 'logged in using chatgpt' in (check.stdout+check.stderr).lower() else 'unavailable'
            except (OSError, subprocess.TimeoutExpired):
                result['connection'] = 'unknown'
            if result['connection'] != 'unavailable':
                try:
                    result['models'] = _codex_catalog(binary)
                    result['discovery'] = 'available'
                except (OSError, ValueError, TimeoutError):
                    result['discovery'] = 'unavailable'
                    try:
                        result['models'] = _codex_cli_catalog(binary)
                        result['discovery'] = 'catalog'
                    except (OSError, ValueError, subprocess.TimeoutExpired):
                        pass
    configured = result['configured_model']
    if configured and configured not in {m['id'] for m in result['models']}:
        result['models'].insert(0, {'id':configured,'name':configured,'source':'configured'})
    return result


def graph_metadata():
    result = {'provider':Config.GRAPH_PROVIDER, 'status':'unknown', 'inference_provider':None, 'model':None}
    if Config.GRAPH_PROVIDER == 'graphiti':
        selected = graph_provider()
        result.update(inference_provider=selected, model=configured_model(selected))
        try:
            from ..utils.zep import get_zep_client
            health = get_zep_client(timeout=5).health()
            result['status'] = health.get('status', 'unknown')
            result['supports_run_settings'] = health.get('inference_context_version') == 1
            if not result['supports_run_settings']:
                result.update(status='unavailable', error='Restart the graph platform with the updated application to apply run settings.')
        except Exception:
            result.update(status='unavailable', error='Start the local graph platform and check its configuration.')
    else:
        result['status'] = 'configured' if Config.ZEP_API_KEY else 'unavailable'
    return result


def settings_payload():
    # Independent probes are bounded and contain no inference.
    with ThreadPoolExecutor(max_workers=2) as pool:
        provider = pool.submit(provider_metadata)
        graph = pool.submit(graph_metadata)
        return {'defaults':load_defaults(), 'provider':provider.result(), 'graph':graph.result()}
