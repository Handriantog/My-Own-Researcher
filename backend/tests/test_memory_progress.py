"""Saving progress must reflect durable work without resuming or extracting it."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.config import Config


def setup_progress(tmp_path, monkeypatch):
    from app.services import memory_progress
    monkeypatch.setattr(Config, 'GRAPH_PROVIDER', 'graphiti')
    monkeypatch.setattr(Config, 'OASIS_SIMULATION_DATA_DIR', str(tmp_path))
    folder = tmp_path / 'sim1'
    folder.mkdir()
    (folder / 'ingestion_checkpoint.json').write_text(json.dumps({
        'simulation_id': 'sim1', 'provider': 'graphiti', 'graph_id': 'g1',
        'episode_uuids': ['a', 'b', 'c', 'd'], 'started_at': 100,
    }))
    def episode(uuid, status):
        return SimpleNamespace(uuid=uuid, status=status, processed=status == 'succeeded',
            metadata={'simulation_id': 'sim1', 'source': 'mirofish_simulation'},
            inference_context={'run_id': 'run1'}, error=None)
    rows = [episode('a', 'succeeded'), episode('b', 'running'), episode('c', 'queued'),
            episode('d', 'queued'), episode('unrelated', 'succeeded')]
    client = SimpleNamespace(graph=SimpleNamespace(episode=SimpleNamespace(
        get_by_graph_id=Mock(return_value=rows))), call=Mock(return_value=SimpleNamespace(calls=[
            SimpleNamespace(recorded_at=50, error=False),
            SimpleNamespace(recorded_at=110, error=False),
            SimpleNamespace(recorded_at=120, error=False),
        ])))
    monkeypatch.setattr(memory_progress, 'get_zep_client', lambda **kw: client)
    return memory_progress, folder, client, rows


def test_memory_progress_counts_only_checkpointed_batches_without_starting_work(tmp_path, monkeypatch):
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    before = (folder / 'ingestion_checkpoint.json').read_bytes()
    result = module.read_memory_progress('sim1')
    assert {k:result[k] for k in ('total', 'completed', 'processing', 'queued', 'failed', 'unknown')} == {
        'total': 4, 'completed': 1, 'processing': 1, 'queued': 2, 'failed': 0, 'unknown': 0}
    assert result['percent'] == 25
    assert result['completed_ai_calls'] == 2
    assert result['last_activity_at'] == 120
    assert (folder / 'ingestion_checkpoint.json').read_bytes() == before


def test_missing_or_foreign_batches_cannot_report_complete(tmp_path, monkeypatch):
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    rows.pop(3)
    rows[1].metadata['simulation_id'] = 'other'
    result = module.read_memory_progress('sim1')
    assert result['unknown'] == 2
    assert result['percent'] is None
    assert result['completed'] == 1


def test_failed_batches_are_visible_and_never_count_as_saved(tmp_path, monkeypatch):
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    rows[1].status = 'failed'; rows[1].error = 'Provider limit reached'
    rows[2].status = rows[3].status = 'canceled'
    result = module.read_memory_progress('sim1')
    assert result['failed'] == 3
    assert result['completed'] == 1
    assert result['percent'] == 25
    assert result['error'] == 'Provider limit reached'


def test_finished_checkpoint_keeps_progress_visible_after_refresh(tmp_path, monkeypatch):
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    checkpoint = folder / 'ingestion_checkpoint.json'
    saved = json.loads(checkpoint.read_text())
    saved['progress_episode_uuids'] = saved['episode_uuids']; saved['episode_uuids'] = []
    checkpoint.write_text(json.dumps(saved))
    for row in rows: row.status = 'succeeded'; row.processed = True
    result = module.read_memory_progress('sim1')
    assert result['completed'] == result['total'] == 4
    assert result['percent'] == 100


def test_usage_unavailable_does_not_hide_batch_progress(tmp_path, monkeypatch):
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    client.call.side_effect = RuntimeError('Temporary telemetry failure')
    result = module.read_memory_progress('sim1')
    assert result['percent'] == 25
    assert result['completed_ai_calls'] is None
    assert result['last_activity_at'] is None


def test_one_unfinished_batch_cannot_round_progress_up_to_complete(tmp_path, monkeypatch):
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    checkpoint = folder / 'ingestion_checkpoint.json'
    saved = json.loads(checkpoint.read_text()); saved['episode_uuids'] = [str(i) for i in range(200)]
    checkpoint.write_text(json.dumps(saved))
    rows[:] = [SimpleNamespace(uuid=str(i), status='succeeded' if i < 199 else 'running',
        metadata={'simulation_id':'sim1', 'source':'mirofish_simulation'}) for i in range(200)]
    result = module.read_memory_progress('sim1')
    assert result['percent'] == 99
    assert result['processing'] == 1


def test_progress_route_reports_connection_failure_without_changing_the_run(tmp_path, monkeypatch):
    from flask import Flask
    from app.api.simulation import simulation_bp
    module, folder, client, rows = setup_progress(tmp_path, monkeypatch)
    app = Flask(__name__); app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    before = (folder / 'ingestion_checkpoint.json').read_bytes()
    response = app.test_client().get('/api/simulation/sim1/memory-progress')
    assert response.status_code == 200
    assert response.json['data']['completed'] == 1
    client.graph.episode.get_by_graph_id.side_effect = RuntimeError('Connection lost')
    response = app.test_client().get('/api/simulation/sim1/memory-progress')
    assert response.status_code == 503
    assert response.json['success'] is False
    assert (folder / 'ingestion_checkpoint.json').read_bytes() == before
