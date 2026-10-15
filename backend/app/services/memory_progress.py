"""Read durable save progress. Observation never starts or retries ingestion."""
import json
from pathlib import Path
import re
import time

from ..config import Config
from ..utils.zep import get_zep_client


def read_memory_progress(simulation_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', simulation_id):
        raise ValueError('Invalid simulation ID')
    if Config.GRAPH_PROVIDER != 'graphiti':
        return None
    path = Path(Config.OASIS_SIMULATION_DATA_DIR) / simulation_id / 'ingestion_checkpoint.json'
    if not path.exists():
        return None  # The uploader has not finished accepting activity yet.
    saved = json.loads(path.read_text(encoding='utf-8'))
    if saved.get('simulation_id') != simulation_id or saved.get('provider') != 'graphiti':
        raise ValueError('Graph ingestion checkpoint does not match this simulation')
    ids = set(saved.get('progress_episode_uuids', saved.get('episode_uuids', [])))
    if not ids:
        return None
    started = saved.get('started_at') or path.stat().st_mtime
    result = dict(total=len(ids), completed=0, processing=0, queued=0, failed=0, unknown=0,
                  percent=None, started_at=started, checked_at=time.time(), error=None,
                  completed_ai_calls=None, last_activity_at=None)
    client = get_zep_client(timeout=3)
    # One read instead of an HTTP request for every pending batch. The existing
    # API caps history at 1000: anything outside that window remains unknown.
    episodes = client.graph.episode.get_by_graph_id(saved['graph_id'], lastn=1000)
    seen, run_ids = set(), set()
    for episode in episodes:
        metadata = getattr(episode, 'metadata', None) or {}
        eid = getattr(episode, 'uuid', None)
        if (eid not in ids or eid in seen or metadata.get('simulation_id') != simulation_id
                or metadata.get('source') != 'mirofish_simulation'):
            continue
        seen.add(eid)
        status = getattr(episode, 'status', None)
        key = {'succeeded': 'completed', 'running': 'processing', 'queued': 'queued',
               'failed': 'failed', 'canceled': 'failed'}.get(status, 'unknown')
        result[key] += 1
        if key == 'failed' and not result['error']:
            result['error'] = getattr(episode, 'error', None)
        context = getattr(episode, 'inference_context', None) or {}
        if context.get('run_id'):
            run_ids.add(context['run_id'])
    result['unknown'] += len(ids - seen)
    if not result['unknown']:
        result['percent'] = int(100 * result['completed'] / result['total'])
    if len(run_ids) == 1:
        try:
            records = client.call('research.usage', run_id=run_ids.pop()).calls
            completed = [r for r in records if r.recorded_at >= started and not r.error]
            result['completed_ai_calls'] = len(completed)
            result['last_activity_at'] = max((r.recorded_at for r in completed), default=None)
        except Exception:
            pass  # Telemetry loss does not erase authoritative batch progress.
    return result
