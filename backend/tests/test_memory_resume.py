import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.config import Config
from app.services import zep_graph_memory_updater as module
from app.services.zep_graph_memory_updater import ZepGraphMemoryUpdater, ZepGraphMemoryManager


def local_updater(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'GRAPH_PROVIDER', 'graphiti')
    monkeypatch.setattr(Config, 'OASIS_SIMULATION_DATA_DIR', str(tmp_path))
    client = SimpleNamespace(provider='graphiti', graph=SimpleNamespace(
        resume_simulation=Mock(return_value=SimpleNamespace(episode_uuids=['failed', 'canceled'], reconciled=True)),
        episode=SimpleNamespace(get=Mock(side_effect=RuntimeError('Codex request timed out')))))
    monkeypatch.setattr(module, 'get_zep_client', lambda *a: client)
    monkeypatch.setattr(ZepGraphMemoryManager, '_updaters', {})
    updater = ZepGraphMemoryUpdater('g1', simulation_id='sim1')
    updater._pending_episode_uuids = ['done', 'failed', 'canceled']
    return updater, client


def test_failed_ingestion_is_checkpointed_and_explicit_resume_requeues(tmp_path, monkeypatch):
    updater, client = local_updater(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match='timed out'):
        updater.stop()
    checkpoint = tmp_path / 'sim1' / 'ingestion_checkpoint.json'
    assert set(json.loads(checkpoint.read_text())['episode_uuids']) == {'done', 'failed', 'canceled'}
    ZepGraphMemoryManager._updaters['sim1'] = updater
    ZepGraphMemoryManager.resume_updater('sim1')
    assert updater._pending_episode_uuids == ['failed', 'canceled']
    client.graph.episode.get.side_effect = None
    client.graph.episode.get.return_value = SimpleNamespace(processed=True)
    ZepGraphMemoryManager.stop_updater('sim1')
    assert ZepGraphMemoryManager.get_updater('sim1') is None
    assert json.loads(checkpoint.read_text())['episode_uuids'] == []
    assert set(json.loads(checkpoint.read_text())['progress_episode_uuids']) == {'failed', 'canceled'}
    assert json.loads(checkpoint.read_text())['started_at'] > 0


def test_resume_restores_checkpoint_without_resending_activity(tmp_path, monkeypatch):
    updater, client = local_updater(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError): updater.stop()
    assert ZepGraphMemoryManager.resume_updater('sim1') is True
    restored = ZepGraphMemoryManager.get_updater('sim1')
    assert restored.graph_id == 'g1'
    assert restored._pending_episode_uuids == ['failed', 'canceled']
    assert restored._running is False


def test_ambiguous_unsent_batches_cannot_publish_complete_checkpoint(tmp_path, monkeypatch):
    updater, client = local_updater(tmp_path, monkeypatch)
    updater._failed_batches = [{'error': 'uncertain write'}]
    with pytest.raises(RuntimeError, match='batch'):
        updater.stop()
    assert not (tmp_path / 'sim1' / 'ingestion_checkpoint.json').exists()


def test_runner_can_finalize_saved_ingestion_after_restart_without_new_rounds(tmp_path, monkeypatch):
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    updater, client = local_updater(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError): updater.stop()
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ('_run_states', '_processes', '_monitor_threads', '_graph_memory_enabled'):
        monkeypatch.setattr(SimulationRunner, name, {})
    monkeypatch.setattr(SimulationRunner, '_sync_simulation_status', Mock())
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED, current_round=37, total_rounds=336,
                               stop_requested=True, error='Graph ingestion failed')
    SimulationRunner._save_run_state(state)
    client.graph.episode.get.side_effect = None
    client.graph.episode.get.return_value = SimpleNamespace(processed=True)
    result = SimulationRunner.stop_simulation('sim1')
    assert result.runner_status == RunnerStatus.STOPPED
    assert result.current_round == 37
    assert result.total_rounds == 336
    assert result.error is None
    assert not SimulationRunner._processes
    assert ZepGraphMemoryManager.get_updater('sim1') is None


def test_failed_automatic_finalization_recovers_saving_even_if_stop_flag_was_false(tmp_path, monkeypatch):
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    updater, client = local_updater(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError): updater.stop()
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED, stop_requested=False)
    # Simulate an older saved state that explicitly includes false.
    path = tmp_path / 'sim1' / 'run_state.json'
    path.write_text(json.dumps(state.to_dict()))
    assert SimulationRunner._load_run_state('sim1').stop_requested is True
    SimulationRunner._save_run_state(state)
    assert state.stop_requested is True


def test_async_stop_after_restart_cannot_hide_unjournaled_failed_upload(tmp_path, monkeypatch):
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    updater, client = local_updater(tmp_path, monkeypatch)
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ('_run_states', '_processes', '_monitor_threads', '_graph_memory_enabled', '_stop_threads'):
        monkeypatch.setattr(SimulationRunner, name, {})
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED,
                               error='Activity upload failed before extraction')
    SimulationRunner._save_run_state(state)
    with pytest.raises(ValueError, match='checkpoint|saving'):
        SimulationRunner.request_stop('sim1')
    assert state.runner_status == RunnerStatus.FAILED
    assert not SimulationRunner._stop_threads


def test_retry_reconstructs_rejected_uploads_from_saved_actions_after_backend_restart(tmp_path, monkeypatch):
    updater, client = local_updater(tmp_path, monkeypatch)
    folder = tmp_path / 'sim1'
    (folder / 'twitter').mkdir(parents=True)
    (folder / 'state.json').write_text(json.dumps({'graph_id': 'g1'}))
    actions = [dict(agent_id=1, agent_name='A', action_type='CREATE_POST',
                    action_args={'content': 'Saved opinion'}, round=42, timestamp='2026-10-15T20:00:00'),
               dict(event_type='simulation_end', total_rounds=42)]
    log = folder / 'twitter/actions.jsonl'
    original = '\n'.join(json.dumps(a) for a in actions)
    log.write_text(original)
    assert ZepGraphMemoryManager.resume_updater('sim1') is True
    payloads = client.graph.resume_simulation.call_args.kwargs['episodes']
    assert len(payloads) == 1
    assert 'Saved opinion' in payloads[0]['data']
    assert payloads[0]['metadata']['simulation_id'] == 'sim1'
    assert payloads[0]['metadata']['first_round'] == 42
    assert log.read_text() == original
    restored = ZepGraphMemoryManager.get_updater('sim1')
    assert restored._pending_episode_uuids == ['failed', 'canceled']
    assert json.loads((folder / 'ingestion_checkpoint.json').read_text())['episode_uuids'] == ['failed', 'canceled']


def test_completed_rounds_retry_memory_without_starting_or_archiving_simulation(tmp_path, monkeypatch):
    import threading
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    updater, client = local_updater(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError): updater.stop()
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ('_run_states', '_processes', '_monitor_threads', '_graph_memory_enabled', '_stop_threads'):
        monkeypatch.setattr(SimulationRunner, name, {})
    monkeypatch.setattr(SimulationRunner, '_sync_simulation_status', Mock())
    monkeypatch.setattr(SimulationRunner, 'start_simulation', lambda *a, **k: pytest.fail('Must not restart rounds'))
    monkeypatch.setattr(SimulationRunner, 'cleanup_simulation_logs', lambda *a: pytest.fail('Must not archive results'))
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED, current_round=42, total_rounds=42,
                               twitter_completed=True, error='Graph memory writes failed')
    state.simulation_completed = True
    SimulationRunner._save_run_state(state)
    entered, release = threading.Event(), threading.Event()
    def wait_episode(**kw):
        entered.set(); assert release.wait(5)
        return SimpleNamespace(processed=True)
    client.graph.episode.get.side_effect = wait_episode
    assert hasattr(SimulationRunner, 'retry_memory'), 'Saving findings needs its own recovery operation'
    SimulationRunner.retry_memory('sim1')
    assert entered.wait(5)
    assert state.to_dict()['memory_status'] == 'saving'
    SimulationRunner.retry_memory('sim1')  # overlapping click attaches to the same worker
    worker = SimulationRunner._stop_threads['sim1']
    release.set(); worker.join(5)
    assert state.runner_status == RunnerStatus.COMPLETED
    assert state.current_round == state.total_rounds == 42
    assert state.to_dict()['memory_status'] == 'completed'
    assert client.graph.resume_simulation.call_count == 1
    assert not SimulationRunner._processes


def test_saved_completed_rounds_survive_restart_and_expose_memory_retry(tmp_path, monkeypatch):
    from app.services.simulation_runner import SimulationRunner
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    folder = tmp_path / 'legacy'
    (folder / 'twitter').mkdir(parents=True)
    (folder / 'reddit').mkdir()
    for platform in ('twitter', 'reddit'):
        (folder / platform / 'actions.jsonl').write_text('{"event_type":"simulation_end"}\n')
    (folder / 'run_state.json').write_text(json.dumps(dict(runner_status='failed', current_round=42,
        total_rounds=42, twitter_completed=True, reddit_completed=True, error='Graph writes failed')))
    state = SimulationRunner._load_run_state('legacy')
    assert state.to_dict()['simulation_completed'] is True
    assert state.to_dict()['memory_recovery_required'] is True
    assert state.to_dict()['memory_status'] == 'failed'


def test_start_api_refuses_restart_of_completed_rounds_with_unsaved_findings(monkeypatch):
    from flask import Flask
    from app.api import simulation as api
    from app.services.simulation_runner import SimulationRunState, RunnerStatus
    from app.services.simulation_manager import SimulationStatus
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED)
    state.simulation_completed = True
    monkeypatch.setattr(api.SimulationRunner, 'get_run_state', lambda sid: state)
    monkeypatch.setattr(api, 'SimulationManager', lambda: SimpleNamespace(get_simulation=lambda sid: SimpleNamespace(status=SimulationStatus.FAILED)))
    monkeypatch.setattr(api.SimulationRunner, 'stop_simulation', lambda sid: pytest.fail('Must not restart or stop completed rounds'))
    with Flask(__name__).test_request_context('/api/simulation/start', method='POST', json={'simulation_id':'sim1','force':True}):
        response, code = api.start_simulation()
    assert code == 409
    assert response.get_json()['code'] == 'memory_recovery_required'


def test_reconciliation_consumes_buffered_tail_without_uploading_it_again(tmp_path, monkeypatch):
    from app.services.zep_graph_memory_updater import AgentActivity
    updater, client = local_updater(tmp_path, monkeypatch)
    folder = tmp_path / 'sim1' / 'twitter'
    folder.mkdir(parents=True)
    row = dict(agent_id=1, agent_name='A', action_type='CREATE_POST', action_args={'content':'Tail'}, round=42, timestamp='2026-10-15T20:00:00')
    (folder / 'actions.jsonl').write_text(json.dumps(row)+'\n')
    updater._platform_buffers['twitter'] = [AgentActivity('twitter',1,'A','CREATE_POST',{'content':'Tail'},42,row['timestamp'])]
    ZepGraphMemoryManager._updaters['sim1'] = updater
    client.graph.add = Mock(side_effect=AssertionError('Reconciled tail cannot be uploaded twice'))
    client.graph.episode.get.side_effect = None
    client.graph.episode.get.return_value = SimpleNamespace(processed=True)
    assert ZepGraphMemoryManager.resume_updater('sim1') is True
    ZepGraphMemoryManager.stop_updater('sim1')
    assert client.graph.add.call_count == 0


def test_research_page_classifies_saved_complete_run_as_memory_failure(tmp_path, monkeypatch):
    from app.services.research_runs import ResearchRuns
    from app.services.research_storage import atomic_json
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED, simulation_completed=True)
    monkeypatch.setattr(SimulationRunner, 'get_run_state', lambda sid: state)
    runs = ResearchRuns(root=tmp_path, stages=SimpleNamespace(synchronize_usage=lambda run: None))
    run_id = 'run_' + 'a'*32
    atomic_json(runs.folder(run_id) / 'run.json', dict(run_id=run_id, simulation_id='sim1',
        stage='simulation', status='failed', completed_stages=['analysis','graph','preparation'],
        error={'stage':'simulation','message':'Saving failed'}))
    result = runs.get(run_id)
    assert result['stage'] == result['error']['stage'] == 'memory'
    assert result['completed_stages'][-1] == 'simulation'
    assert result['memory_recovery_required'] is True
    assert result['simulation_restart_required'] is False


@pytest.mark.parametrize('remote_failure', [False, True])
def test_explicit_memory_retry_clears_old_cancellation_and_preserves_new_failure(tmp_path, monkeypatch, remote_failure):
    from research_runtime import InferenceContext, inference_scope
    from app.services.simulation_runner import SimulationRunner, SimulationRunState, RunnerStatus
    import app.utils.zep as zep
    updater, client = local_updater(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError): updater.stop()
    monkeypatch.setattr(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path))
    for name in ('_run_states', '_processes', '_monitor_threads', '_graph_memory_enabled', '_stop_threads'):
        monkeypatch.setattr(SimulationRunner, name, {})
    monkeypatch.setattr(SimulationRunner, '_sync_simulation_status', Mock())
    client.call = Mock(side_effect=RuntimeError('Graph disconnected') if remote_failure else None)
    monkeypatch.setattr(zep, 'get_zep_client', lambda: client)
    marker = tmp_path / 'stop'
    marker.touch()
    state = SimulationRunState('sim1', runner_status=RunnerStatus.FAILED, simulation_completed=True)
    SimulationRunner._save_run_state(state)
    def resume(**kw):
        assert not marker.exists(), 'An explicit save retry must clear an earlier stop'
        raise RuntimeError('Quota is still unavailable')
    client.graph.resume_simulation.side_effect = resume
    with inference_scope(InferenceContext('run_test', 'codex', stop_path=str(marker))):
        SimulationRunner.retry_memory('sim1')
        worker = SimulationRunner._stop_threads.get('sim1')
        if worker:
            worker.join(5)
    assert state.runner_status == RunnerStatus.FAILED
    assert state.to_dict()['memory_recovery_required'] is True
    assert state.to_dict()['memory_status'] == 'failed'
    assert ('Graph disconnected' if remote_failure else 'Quota is still unavailable') in state.error
    assert marker.exists() is remote_failure
    client.call.assert_called_once_with('research.stop', run_id='run_test', stopped=False)
