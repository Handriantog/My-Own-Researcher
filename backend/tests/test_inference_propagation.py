import json
from pathlib import Path
from types import SimpleNamespace

import httpx

from research_runtime import InferenceContext, inference_scope, current_context


def test_llm_client_captures_reviewed_openai_model_and_usage(tmp_path, monkeypatch):
    from app.utils import llm_client
    from app.config import Config
    monkeypatch.setattr(Config, 'LLM_PROVIDER', 'openai')
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'fake')
    monkeypatch.setenv('OPENAI_LOCK_PATH', str(tmp_path / 'api.lock'))
    def completion(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=kwargs['model']))],
                               usage={'prompt_tokens': 14, 'completion_tokens': 3})
    monkeypatch.setattr(llm_client, 'OpenAI', lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=completion))))
    ctx = InferenceContext('run-model', 'openai', 'selected', 2, str(tmp_path / 'usage.sqlite3'))
    with inference_scope(ctx):
        client = llm_client.LLMClient()
    assert client.chat([{'role':'user','content':'test'}]) == 'selected'
    from research_runtime.usage import usage_summary
    assert usage_summary(ctx.usage_path)['total_tokens'] == 17


def test_agent_client_preserves_context_after_scope_exits(monkeypatch):
    from app.utils.agent_provider import AgentClient
    def infer(self, prompt, schema, cancel_event=None):
        return {'content': current_context().model, 'tool_calls': []}, {}
    monkeypatch.setattr(AgentClient, '_infer', infer)
    ctx = InferenceContext('run-model', 'codex', 'selected', 2)
    with inference_scope(ctx):
        client = AgentClient('codex')
    result = client.create(messages=[{'role':'user','content':'test'}])
    assert result.choices[0].message.content == 'selected'
    assert result.model == 'selected'
    assert result.usage is None


def test_graph_jobs_receive_portable_context_not_backend_file_paths(monkeypatch):
    from app.local_graph.client import LocalGraphClient
    seen = []
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={'batch_id': 'b1'})
    client = LocalGraphClient('http://127.0.0.1:8000', 'token', transport=httpx.MockTransport(respond))
    ctx = InferenceContext('run-graph', 'codex', 'selected', 3, '/private/usage', '/private/stop')
    monkeypatch.delenv('GRAPH_LLM_PROVIDER', raising=False)
    with inference_scope(ctx):
        client.batch.create(metadata={'graph_id':'g1'})
    saved = seen[0]['params']['metadata']['inference_context']
    assert saved['model'] == 'selected' and saved['concurrency'] == 3
    assert saved['usage_path'] is None and saved['stop_path'] is None
    monkeypatch.setenv('GRAPH_LLM_PROVIDER', 'claude-code')
    monkeypatch.setenv('AGENT_MODEL', 'graph-model')
    with inference_scope(ctx):
        client.graph.add(graph_id='g1', type='text', data='test')
    saved = seen[1]['params']['inference_context']
    assert saved['provider'] == 'claude-code' and saved['model'] == 'graph-model'
