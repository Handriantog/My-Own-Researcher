"""Durable single-owner orchestration; browser requests only start or observe."""
import copy
import fcntl
import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

from research_runtime import InferenceContext, ContextThread, inference_scope
from research_runtime.usage import usage_summary
from .research_storage import research_root, read_json, atomic_json, file_lock
from .research_drafts import ResearchDrafts
from .research_estimates import estimate

STAGES = ('analysis', 'graph', 'preparation', 'simulation', 'memory', 'report')
ACTIVE = {'queued', 'running', 'stopping'}


class ResearchStopped(RuntimeError):
    pass


class ResearchRuns:
    def __init__(self, app=None, *, root=None, stages=None):
        self.root = research_root(root)
        self.drafts = ResearchDrafts(self.root)
        if stages is None:
            from .research_stages import ResearchStages
            stages = ResearchStages(app, self.root)
        self.stages = stages
        self.recover()

    def folder(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r'run_[a-f0-9]{32}', run_id):
            raise ValueError('Invalid research run ID')
        return self.root / 'runs' / run_id

    def raw(self, run_id):
        run = read_json(self.folder(run_id) / 'run.json')
        if not run:
            raise LookupError('Research run not found')
        return run

    def update(self, run_id, **values):
        with file_lock(self.folder(run_id) / 'state.lock'):
            run = self.raw(run_id)
            run.update(values, updated_at=time.time())
            atomic_json(self.folder(run_id) / 'run.json', run)
        return run

    def get(self, run_id):
        run = self.raw(run_id)
        self.stages.synchronize_usage(run)
        result = copy.deepcopy(run)
        result['usage'] = usage_summary(str(self.folder(run_id) / 'usage.sqlite3'))
        if (run.get('graph_settings') or {}).get('provider'):
            telemetry = read_json(self.folder(run_id) / 'telemetry.json', {})
            result['usage']['graph_coverage'] = telemetry.get('graph_coverage', 'unknown')
            if result['usage']['graph_coverage'] != 'complete':
                result['usage']['coverage'] = 'partial' if result['usage']['reported_calls'] else 'unknown'
                if result['usage']['reasoning_coverage'] == 'complete':
                    result['usage']['reasoning_coverage'] = 'partial'
        simulation_finished = False
        if run.get('simulation_id') and run['stage'] in {'simulation', 'memory'}:
            from .simulation_runner import SimulationRunner
            state = SimulationRunner.get_run_state(run['simulation_id'])
            simulation_finished = bool(state and getattr(state, 'simulation_completed', False))
            if simulation_finished and result['stage'] == 'simulation':
                result['stage'] = 'memory'
                result['completed_stages'] = list(dict.fromkeys([*result['completed_stages'], 'simulation']))
                if result.get('error'):
                    result['error']['stage'] = 'memory'
        result['memory_recovery_required'] = simulation_finished and run['status'] in {'failed','interrupted','stopped'}
        result['simulation_restart_required'] = not simulation_finished and run['stage'] == 'simulation' and run['status'] in {'failed','interrupted','stopped'}
        result.pop('fingerprint', None)
        return result

    @staticmethod
    def fingerprint(draft_id, settings, project_id=None, simulation_id=None):
        payload = dict(draft_id=draft_id, project_id=project_id,
                       simulation_id=simulation_id, settings=settings)
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def retry(self, data):
        """Resolve an accepted intent before revalidating mutable configuration."""
        key = data.get('idempotency_key')
        if not isinstance(key, str) or not 1 <= len(key) <= 200:
            raise ValueError('A stable start idempotency key is required')
        with file_lock(self.root / 'start.lock'):
            run_id = read_json(self.root / 'start-index.json', {}).get(hashlib.sha256(key.encode()).hexdigest())
            if not run_id:
                return None
            run = self.raw(run_id)
            from .research_settings import validate_settings
            chosen = validate_settings(data.get('settings', {}), provider=run['settings']['provider'])
            if self.fingerprint(data.get('draft_id'), chosen, data.get('project_id'), data.get('simulation_id')) != run['fingerprint']:
                raise ValueError('This start key was already used with different settings')
            return self.get(run_id)

    def start(self, draft_id, settings, idempotency_key, *, project_id=None, simulation_id=None,
              graph_settings=None, locale='en'):
        if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=200:
            raise ValueError('A stable start idempotency key is required')
        payload = dict(draft_id=draft_id, project_id=project_id, simulation_id=simulation_id,
                       settings=settings, graph_settings=graph_settings or {})
        fingerprint = self.fingerprint(draft_id, settings, project_id, simulation_id)
        key = hashlib.sha256(idempotency_key.encode()).hexdigest()
        with file_lock(self.root / 'start.lock'):
            index = read_json(self.root / 'start-index.json', {})
            if key in index:
                run = self.raw(index[key])
                if run['fingerprint'] != fingerprint:
                    raise ValueError('This start key was already used with different settings')
                return self.get(run['run_id'])
            if draft_id:
                if simulation_id or project_id:
                    raise ValueError('A new source draft cannot reuse a project or simulation')
                draft = self.drafts.get(draft_id)
                if draft.get('run_id'):
                    raise ValueError('This source draft already has a run. Open that run instead.')
                text = self.drafts.text(draft_id)
                summary = self.drafts.public(draft)
            else:
                from ..models.project import ProjectManager
                if not re.fullmatch(r'proj_[A-Za-z0-9_-]+', project_id or ''):
                    raise ValueError('A draft or saved project is required')
                project = ProjectManager.get_project(project_id)
                text = ProjectManager.get_extracted_text(project_id) if project else None
                if not project or not text:
                    raise ValueError('Saved project source text is unavailable')
                if getattr(project, 'research_run_id', None):
                    raise ValueError('This project already has a research run. Open that run instead.')
                if simulation_id:
                    from .simulation_manager import SimulationManager
                    if not re.fullmatch(r'sim_[A-Za-z0-9_-]+', simulation_id):
                        raise ValueError('Invalid simulation ID')
                    simulation = SimulationManager().get_simulation(simulation_id)
                    if not simulation or simulation.project_id != project_id:
                        raise ValueError('The simulation does not belong to this project')
                summary = {'question':project.simulation_requirement,'files':project.files}
            run_id = 'run_' + uuid.uuid4().hex
            run = dict(payload, run_id=run_id, fingerprint=fingerprint, source=summary, locale=locale,
                stage='analysis', status='queued', completed_stages=[], stop_requested=False,
                created_at=time.time(), updated_at=time.time(), error=None, report_id=None,
                estimate=estimate(text,settings), partial_report=False)
            run['original_estimate'] = copy.deepcopy(run['estimate'])
            atomic_json(self.folder(run_id) / 'run.json', run)
            index[key] = run_id
            atomic_json(self.root / 'start-index.json', index)
            if draft_id:
                self.drafts.attach(draft_id,run_id)
            elif project_id:
                # Reserve the saved project before a queued worker can be delayed.
                project.research_run_id = run_id
                project.research_settings = copy.deepcopy(settings)
                ProjectManager.save_project(project)
            self._launch(run_id)
        return self.get(run_id)

    def context(self, run):
        graph = run.get('graph_settings') or {}
        return InferenceContext(run['run_id'],run['settings']['provider'],run['settings']['model'],
            run['settings']['concurrency'],str(self.folder(run['run_id']) / 'usage.sqlite3'),
            str(self.folder(run['run_id']) / 'stop'), graph.get('inference_provider'),graph.get('model'))

    def _claim(self, run_id):
        path = self.folder(run_id) / 'worker.lock'
        handle = path.open('a')
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            handle.close()
            return None

    def _launch(self, run_id):
        # Claim before returning to the browser; avoids queued/status race windows.
        handle = self._claim(run_id)
        if handle is None:
            return
        try:
            ContextThread(target=self._work, args=(run_id,handle), daemon=True).start()
        except BaseException:
            handle.close()
            self.update(run_id,status='interrupted')
            raise

    def stopped(self, run_id):
        return (self.folder(run_id) / 'stop').exists()

    def _work(self, run_id, handle):
        run = self.raw(run_id)
        try:
            with inference_scope(self.context(run)):
                self.update(run_id,status='running',error=None)
                for stage in STAGES:
                    # State lock orders a stage launch against a Stop request.
                    with file_lock(self.folder(run_id) / 'state.lock'):
                        run = self.raw(run_id)
                        if run['stop_requested'] or self.stopped(run_id):
                            raise ResearchStopped('Research stopped')
                        if stage in run['completed_stages']:
                            continue
                        run.update(stage=stage,updated_at=time.time())
                        atomic_json(self.folder(run_id) / 'run.json',run)
                    self.stages.execute(stage,run,lambda **kw:self.update(run_id,**kw),lambda:self.stopped(run_id))
                    if self.stopped(run_id):
                        raise ResearchStopped('Research stopped')
                    completed = self.raw(run_id)['completed_stages']
                    self.update(run_id,completed_stages=[*completed,stage])
                self.update(run_id,status='completed',completed_at=time.time(),error=None)
        except BaseException as error:
            run = self.raw(run_id)
            if self.stopped(run_id):
                self._finish_stop(run_id)
            else:
                self.update(run_id,status='failed',error={'stage':run['stage'],'message':str(error)[:1500]})
        finally:
            try:
                self.stages.synchronize_usage(self.raw(run_id))
            finally:
                handle.close()

    def _finish_stop(self, run_id, handle=None):
        run = self.raw(run_id)
        self.update(run_id, status='stopping')
        try:
            with inference_scope(self.context(run)):
                self.stages.stop(run)
        except Exception as error:
            self.update(run_id, status='failed', error={'stage':run['stage'], 'message':str(error)[:1500]})
        else:
            self.update(run_id, status='stopped', error=None)
        finally:
            if handle:
                handle.close()

    def stop(self, run_id):
        with file_lock(self.folder(run_id) / 'state.lock'):
            run = self.raw(run_id)
            if run['status'] == 'completed':
                return self.get(run_id)
            (self.folder(run_id) / 'stop').touch()
            run.update(stop_requested=True,status='stopping')
            atomic_json(self.folder(run_id) / 'run.json',run)
        handle = self._claim(run_id)
        if handle is not None:
            try:
                ContextThread(target=self._finish_stop, args=(run_id,handle), daemon=True).start()
            except BaseException:
                handle.close()
                raise
        return self.get(run_id)

    def resume(self, run_id, *, partial_report=False):
        with file_lock(self.root / 'start.lock'):
            run = self.raw(run_id)
            if run['status'] in ACTIVE or run['status'] == 'completed':
                return self.get(run_id)
            handle = self._claim(run_id)
            if handle is None:
                raise ValueError('The previous worker is still finishing. Wait and retry.')
            try:
                if partial_report:
                    if not run.get('simulation_id'):
                        raise ValueError('Run the simulation before requesting a partial report')
                    completed = list(STAGES[:4])
                else:
                    completed = run['completed_stages']
                (self.folder(run_id) / 'stop').unlink(missing_ok=True)
                self.update(run_id,status='queued',stop_requested=False,error=None,
                    completed_stages=completed,partial_report=partial_report or run.get('partial_report',False))
                ContextThread(target=self._work,args=(run_id,handle),daemon=True).start()
            except BaseException:
                handle.close()
                raise
        return self.get(run_id)

    def recover(self):
        for path in (self.root / 'runs').glob('run_*/run.json'):
            run = read_json(path)
            if run and run['status'] in ACTIVE:
                handle = self._claim(run['run_id'])
                if handle:
                    try:
                        self.update(run['run_id'],status='interrupted',error={
                            'stage':run['stage'],'message':'The backend stopped. Resume to continue from saved work.'})
                    finally:
                        handle.close()
