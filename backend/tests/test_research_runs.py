import io
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from werkzeug.datastructures import FileStorage
from research_runtime import current_context
from app.services.research_drafts import ResearchDrafts
from app.services.research_runs import ResearchRuns, STAGES
from app.services.research_settings import validate_settings
from app.services.research_storage import atomic_json


class Stages:
    def __init__(self):
        self.calls = []
        self.hook = None
    def execute(self, stage, run, update, stopped):
        self.calls.append((stage, current_context().model))
        if self.hook:
            self.hook(stage, run)
        if stage == 'report':
            update(report_id='report_complete')
    def stop(self, run):
        pass
    def synchronize_usage(self, run):
        pass


def setup_run(tmp_path):
    drafts = ResearchDrafts(tmp_path)
    draft = drafts.create([FileStorage(stream=io.BytesIO(b'Research source'),filename='source.txt')], 'Question?')
    stages = Stages()
    runs = ResearchRuns(root=tmp_path, stages=stages)
    settings = validate_settings({'provider':'codex','model':'selected'}, provider='codex')
    return runs, draft, settings, stages


def terminal(runs, run_id):
    for _ in range(300):
        run = runs.get(run_id)
        if run['status'] in {'completed','failed','stopped','interrupted'}:
            return run
        time.sleep(.01)
    pytest.fail('Research did not reach a terminal status')


def test_start_is_idempotent_and_reaches_report_with_captured_settings(tmp_path):
    runs, draft, settings, stages = setup_run(tmp_path)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _:runs.start(draft['draft_id'], settings, 'same-key'),range(3)))
    assert len({r['run_id'] for r in results}) == 1
    result = terminal(runs,results[0]['run_id'])
    assert result['report_id'] == 'report_complete'
    assert result['status'] == 'completed'
    assert stages.calls == [(stage,'selected') for stage in STAGES]
    assert result['original_estimate'] == result['estimate']
    with pytest.raises(ValueError, match='different'):
        runs.start(draft['draft_id'], {**settings,'model':'different'}, 'same-key')


@pytest.mark.parametrize('stop_stage', STAGES)
def test_stop_never_launches_a_later_stage(tmp_path, stop_stage):
    runs, draft, settings, stages = setup_run(tmp_path)
    def hook(stage, run):
        if stage == stop_stage:
            runs.stop(run['run_id'])
    stages.hook = hook
    run = runs.start(draft['draft_id'],settings,'stop-key')
    result = terminal(runs,run['run_id'])
    assert result['status'] == 'stopped'
    assert [stage for stage,_ in stages.calls] == list(STAGES[:STAGES.index(stop_stage)+1])


def test_restart_marks_recovery_without_running_and_resume_uses_checkpoint(tmp_path):
    runs, draft, settings, stages = setup_run(tmp_path)
    def fail(stage, run):
        if stage == 'simulation':
            raise RuntimeError('interrupted request')
    stages.hook = fail
    run = runs.start(draft['draft_id'],settings,'restart-key')
    failed = terminal(runs,run['run_id'])
    assert failed['status'] == 'failed'
    assert failed['simulation_restart_required'] is True
    # Simulate a server dying between stage execution and failure persistence.
    failed['status'] = 'running'
    atomic_json(runs.folder(run['run_id']) / 'run.json', failed)
    after = Stages()
    restarted = ResearchRuns(root=tmp_path, stages=after)
    assert restarted.get(run['run_id'])['status'] == 'interrupted'
    assert after.calls == []
    restarted.resume(run['run_id'])
    result = terminal(restarted,run['run_id'])
    assert result['status'] == 'completed'
    assert [stage for stage,_ in after.calls] == ['simulation','memory','report']


def test_settings_snapshot_does_not_change_after_start(tmp_path):
    runs, draft, settings, stages = setup_run(tmp_path)
    run = runs.start(draft['draft_id'],settings,'immutable-key')
    settings['model'] = 'later-default'
    result = terminal(runs,run['run_id'])
    assert result['settings']['model'] == 'selected'
    assert all(model == 'selected' for _,model in stages.calls)


def test_stop_after_recovery_cancels_stage_without_launching_inference(tmp_path, monkeypatch):
    runs,draft,settings,stages=setup_run(tmp_path)
    monkeypatch.setattr(runs,'_launch',lambda run_id:None)
    run=runs.start(draft['draft_id'],settings,'recovered-stop')
    runs.update(run['run_id'],stage='graph',status='running')
    stopped=[]
    stages.stop=lambda value:stopped.append(value['run_id'])
    restarted=ResearchRuns(root=tmp_path,stages=stages)
    assert restarted.raw(run['run_id'])['status']=='interrupted'
    restarted.stop(run['run_id'])
    assert terminal(restarted,run['run_id'])['status']=='stopped'
    assert stopped==[run['run_id']]
    assert stages.calls==[]


@pytest.mark.parametrize('graph_provider', ['graphiti','zep'])
def test_missing_graph_usage_never_claims_complete_coverage(tmp_path, monkeypatch, graph_provider):
    from research_runtime.usage import record_usage
    from app.services.research_stages import ResearchStages
    runs,draft,settings,stages=setup_run(tmp_path)
    monkeypatch.setattr(runs,'_launch',lambda run_id:None)
    run=runs.start(draft['draft_id'],settings,'usage',graph_settings={'provider':graph_provider})
    record_usage(runs.context(run),'backend-call',{'input_tokens':100,'output_tokens':20})
    monkeypatch.setattr('app.utils.zep.get_zep_client',lambda **kw: (_ for _ in ()).throw(RuntimeError('offline')))
    runs.stages=ResearchStages(None,tmp_path)
    result=runs.get(run['run_id'])
    assert result['usage']['coverage']=='partial'
    assert result['usage']['total_tokens']==120
    assert result['usage']['graph_coverage']=='unknown'


def test_existing_project_cannot_launch_two_owners_or_reuse_another_simulation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.models.project import ProjectManager
    from app.services.simulation_manager import SimulationManager
    runs,draft,settings,stages=setup_run(tmp_path)
    project=SimpleNamespace(simulation_requirement='Question',files=[],research_run_id='run_existing')
    monkeypatch.setattr(ProjectManager,'get_project',lambda id:project)
    monkeypatch.setattr(ProjectManager,'get_extracted_text',lambda id:'Saved sources')
    monkeypatch.setattr(runs,'_launch',lambda run_id:None)
    with pytest.raises(ValueError,match='already has a research run'):
        runs.start(None,settings,'project-duplicate',project_id='proj_test')
    project.research_run_id=None
    monkeypatch.setattr(SimulationManager,'get_simulation',lambda self,id:SimpleNamespace(project_id='proj_other'))
    with pytest.raises(ValueError,match='does not belong'):
        runs.start(None,settings,'project-mismatch',project_id='proj_test',simulation_id='sim_other')
