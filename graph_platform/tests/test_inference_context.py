import asyncio
from dataclasses import replace

import pytest
from research_runtime import InferenceContext, current_context
from research_graph.store import GraphStore
from research_graph.runtime import GraphRuntime


def test_batch_context_is_copied_to_durable_episode(tmp_path):
    store = GraphStore(tmp_path / 'graph.sqlite3')
    store.create_graph('g1', '', '')
    context = InferenceContext('run-graph', 'codex', 'reviewed-model', 3).to_dict()
    batch = store.create_batch({'graph_id':'g1', 'mirofish_operation_id':'op1', 'inference_context':context})
    rows = store.add_items(batch['batch_id'], [{'graph_id':'g1','data':'source','type':'text'}])
    assert rows[0]['inference_context'] == context
    store.process_batch(batch['batch_id'])
    assert store.claim_next()['inference_context']['model'] == 'reviewed-model'


@pytest.mark.asyncio
async def test_worker_binds_context_and_records_usage_locally(tmp_path):
    from research_runtime.usage import record_usage
    store = GraphStore(tmp_path / 'graph.sqlite3')
    store.create_graph('g1', '', '')
    context = InferenceContext('run-graph', 'codex', 'reviewed-model', 3).to_dict()
    episode = store.add_episode('g1', 'text', 'source', inference_context=context)
    seen = []
    class Engine:
        async def ingest(self, job, ontology):
            seen.append(current_context())
            record_usage(current_context(), 'graph-call', {'input_tokens':20,'output_tokens':5})
        async def close(self):
            pass
    runtime = GraphRuntime(store, Engine())
    await runtime.start()
    try:
        for _ in range(100):
            if store.episode(episode['uuid'])['processed']:
                break
            await asyncio.sleep(.01)
        assert seen and seen[0].model == 'reviewed-model'
        assert store.run_usage('run-graph')[0]['input_tokens'] == 20
        assert current_context() is None
    finally:
        await runtime.close()


def test_interrupted_upload_recovery_keeps_context_on_missing_chunks(tmp_path):
    import hashlib
    store=GraphStore(tmp_path/'graph.sqlite3')
    store.create_graph('g1','','')
    chunks=['first','second']
    digest=hashlib.sha256('\0'.join(chunks).encode()).hexdigest()
    operation=hashlib.sha256(f'g1:{digest}'.encode()).hexdigest()
    context=InferenceContext('run-recovery','codex','chosen',2).to_dict()
    batch=store.create_batch({'graph_id':'g1','mirofish_operation_id':operation,
        'chunk_count':2,'inference_context':context})
    store.add_items(batch['batch_id'],[{'graph_id':'g1','data':'first','type':'text'}])
    store.resume_batch(batch['batch_id'],operation_id=operation,chunks=chunks)
    with store.connection() as db:
        import json
        payloads=[json.loads(r[0]) for r in db.execute('SELECT payload FROM episodes ORDER BY sequence_index')]
    assert [p.get('inference_context') for p in payloads]==[context,context]
