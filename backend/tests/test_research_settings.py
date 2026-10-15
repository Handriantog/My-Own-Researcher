import io
import json
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

from app.services.research_settings import validate_settings, load_defaults, save_defaults
from app.services.research_estimates import estimate, workload_label
from app.services.research_drafts import ResearchDrafts


def settings(**values):
    return validate_settings({'provider':'codex', **values}, provider='codex')


def test_defaults_are_validated_and_saved_without_inference(tmp_path):
    saved = save_defaults(settings(model='chosen', concurrency=4), root=tmp_path)
    assert saved['concurrency'] == 4
    assert load_defaults(provider='codex', root=tmp_path)['model'] == 'chosen'
    assert load_defaults(provider='claude-code', root=tmp_path)['model'] is None
    for values in [{'concurrency':9}, {'concurrency':True}, {'depth':'invalid'}, {'platform':'unknown'}, {'provider':'openai'}, {'model':'x\nsecret'}]:
        with pytest.raises(ValueError):
            settings(**values)


def test_local_draft_extracts_and_rejects_empty_sources(tmp_path):
    drafts = ResearchDrafts(tmp_path)
    file = FileStorage(stream=io.BytesIO(b'An office lunch pilot for 200 people.'), filename='../brief.txt')
    draft = drafts.create([file], 'Should we launch?')
    public = drafts.public(draft)
    assert public['files'][0]['filename'] == 'brief.txt'
    assert 'path' not in json.dumps(public)
    assert drafts.text(draft['draft_id']) == 'An office lunch pilot for 200 people.'
    empty = FileStorage(stream=io.BytesIO(b'  '), filename='empty.txt')
    with pytest.raises(ValueError, match='empty|readable'):
        drafts.create([empty], 'Question')


def test_estimate_changes_with_work_not_parallelism():
    source = 'research evidence ' * 1000
    base = estimate(source, settings())
    assert estimate(source, settings(concurrency=8)) == base
    assert estimate(source, settings(depth='full'))['upper'] > base['upper']
    assert estimate(source, settings(platform='parallel'))['upper'] > base['upper']
    assert estimate(source * 4, settings())['upper'] > base['upper']
    assert base['confidence'] == 'preliminary'
    assert base['reasoning_coverage'] == 'unknown'
    assert set(base['stages']) == {'analysis_graph','preparation','simulation_memory','report'}
    refined = estimate(source, settings(), plan={'agents':5,'rounds':24})
    assert refined['confidence'] == 'refined' and refined['assumptions']['agents'] == [5,5]


@pytest.mark.parametrize('upper,label', [(99999,'low'),(100000,'medium'),(499999,'medium'),(500000,'high'),(1999999,'high'),(2000000,'extra_high')])
def test_workload_boundaries(upper,label):
    assert workload_label(upper) == label


def test_codex_model_inventory_uses_only_bounded_metadata_rpc(tmp_path):
    import json
    import sys
    from app.services.research_settings import _codex_catalog
    log=tmp_path/'rpc.jsonl'
    binary=tmp_path/'codex'
    binary.write_text(f'''#!{sys.executable}
import json,sys
for line in sys.stdin:
    request=json.loads(line)
    with open({str(log)!r},'a') as f:f.write(json.dumps(request)+'\\n')
    if 'id' in request:
        # Codex 0.157.1's generated ClientRequest schema requires null/omitted
        # params here. Reject malformed requests like the real server does.
        if request['method']=='account/gatewayOAuth/read' and request.get('params') is not None:
            print(json.dumps({{'id':request['id'],'error':{{'code':-32600,'message':'Invalid request: invalid type: map, expected unit'}}}}),flush=True)
            continue
        result={{'data':[{{'model':'available-model','displayName':'Available'}}]}} if request['method']=='model/list' else {{}}
        print(json.dumps({{'id':request['id'],'result':result}}),flush=True)
''')
    binary.chmod(0o700)
    assert _codex_catalog(str(binary),timeout=1)==[{'id':'available-model','name':'Available','source':'discovered'}]
    methods=[json.loads(line)['method'] for line in log.read_text().splitlines()]
    assert methods==['initialize','initialized','account/gatewayOAuth/read','model/list']


def test_codex_model_inventory_timeout_reaps_child(tmp_path):
    import sys
    import time
    from app.services.research_settings import _codex_catalog
    binary=tmp_path/'codex'
    binary.write_text(f'#!{sys.executable}\nimport time\ntime.sleep(30)\n')
    binary.chmod(0o700)
    started=time.monotonic()
    with pytest.raises(TimeoutError):
        _codex_catalog(str(binary),timeout=.1)
    assert time.monotonic()-started<2


def test_refinement_uses_observed_sizes_from_the_selected_model_only():
    from app.services.research_estimates import request_observations
    chosen={'provider':'codex','model':'selected'}
    records=[{'provider':'codex','model':'selected','input_tokens':8000,'output_tokens':1000} for _ in range(3)]
    records += [{'provider':'codex','model':'other','input_tokens':999999,'output_tokens':1000}]
    assert request_observations(records,chosen)['request_token_range']==[4500,32000]
    assert request_observations(records[:1],chosen)=={}


def test_codex_discovery_falls_back_to_cli_catalog_without_claiming_account_access(monkeypatch, tmp_path):
    import sys
    from app.services import research_settings as service
    log = tmp_path / 'commands.jsonl'
    binary = tmp_path / 'codex'
    # Exercise the published package's CLI boundary rather than mocking its
    # subprocess implementation. The fallback remains metadata-only.
    binary.write_text(f'''#!{sys.executable}
import json,sys
with open({str(log)!r}, 'a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[-2:] == ['login', 'status']:
    print('Logged in using ChatGPT')
else:
    assert sys.argv[-2:] == ['debug', 'models']
    print(json.dumps({{'models': [
        {{'slug': 'gpt-6-astra', 'display_name': 'GPT-6-Astra', 'visibility': 'list'}},
        {{'slug': 'internal-hidden', 'display_name': 'Hidden', 'visibility': 'hide'}}
    ]}}))
''')
    binary.chmod(0o700)
    monkeypatch.setenv('CODEX_BIN', str(binary))
    monkeypatch.setattr(service,'configured_provider',lambda:'codex')
    monkeypatch.setattr(service,'configured_model',lambda provider:None)
    monkeypatch.setattr(service,'_codex_catalog',lambda binary:(_ for _ in ()).throw(ValueError('Metadata unavailable')))
    result=service.provider_metadata()
    assert result['models']==[{'id':'gpt-6-astra','name':'GPT-6-Astra','source':'catalog'}]
    assert result['connection']=='connected'
    assert result['discovery']=='catalog'
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls == [['--no-daemon', 'login', 'status'], ['--no-daemon', 'debug', 'models']]
