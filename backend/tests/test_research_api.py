import io
import time
from pathlib import Path
import pytest

from app import create_app
from app.config import Config
from app.services import research_settings
from app.services.research_runs import ResearchRuns


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(Config,'UPLOAD_FOLDER',str(tmp_path))
    monkeypatch.setattr(Config,'LLM_PROVIDER','codex')
    monkeypatch.setattr(research_settings,'provider_metadata',lambda:{'id':'codex','connection':'unknown','models':[]})
    monkeypatch.setattr(research_settings,'graph_metadata',lambda:{'provider':'zep','status':'configured'})
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_draft_review_and_defaults_do_not_start_inference(client,monkeypatch):
    from app.services.ontology_generator import OntologyGenerator
    monkeypatch.setattr(OntologyGenerator,'generate',lambda *a,**k:pytest.fail('Review started inference'))
    response = client.post('/api/research/drafts',data={
        'files':(io.BytesIO(b'Local text for review.'),'brief.txt'),'question':'Should we launch?'})
    assert response.status_code == 201
    draft = response.json['data']
    settings = {'provider':'codex','model':None,'concurrency':2,'depth':'quick','platform':'reddit'}
    response = client.post('/api/research/estimate',json={'draft_id':draft['draft_id'],'settings':settings})
    assert response.status_code == 200 and response.json['data']['upper']>0
    assert client.put('/api/research/settings',json=settings).status_code == 200
    assert client.get('/api/research/settings').json['data']['provider']['connection'] == 'unknown'
    assert 'source.txt' not in str(draft)


def test_browser_inference_requires_review_but_programmatic_client_keeps_legacy_behavior(client):
    response = client.post('/api/graph/ontology/resume',json={'project_id':'proj_legacy'},headers={'X-Research-Client':'browser'})
    assert response.status_code == 409 and response.json['code'] == 'review_required'
    assert response.json['review']['project_id'] == 'proj_legacy'
    legacy = client.post('/api/graph/ontology/resume',json={'project_id':'proj_legacy'})
    assert legacy.status_code == 404


def test_start_rejects_invalid_parallelism_before_launch(client):
    response = client.post('/api/research/runs',json={'draft_id':'draft_x','idempotency_key':'key','settings':{'provider':'codex','concurrency':9}})
    assert response.status_code == 400


def test_retry_resolves_existing_run_before_changed_provider_or_graph_preflight(client,monkeypatch):
    runs=client.application.extensions['research_runs']
    monkeypatch.setattr(runs,'_launch',lambda run_id:None)
    draft=client.post('/api/research/drafts',data={'files':(io.BytesIO(b'Source'),'s.txt'),'question':'Question'}).json['data']
    payload={'draft_id':draft['draft_id'],'idempotency_key':'lost-response','settings':{'provider':'codex'}}
    first=client.post('/api/research/runs',json=payload)
    assert first.status_code==202
    monkeypatch.setattr(research_settings,'settings_payload',lambda:pytest.fail('Retry must not probe services'))
    monkeypatch.setattr(Config,'LLM_PROVIDER','openai')
    retry=client.post('/api/research/runs',json=payload)
    assert retry.status_code==202
    assert retry.json['data']['run_id']==first.json['data']['run_id']
    changed=client.post('/api/research/runs',json={**payload,'settings':{'provider':'codex','model':'other'}})
    assert changed.status_code==400
