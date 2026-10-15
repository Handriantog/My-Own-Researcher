"""Bridge the coordinator to existing checkpoint-aware research services."""
import math
import time
from pathlib import Path
from research_runtime import current_context
from research_runtime.usage import import_records, usage_records
from ..models.project import ProjectManager, ProjectStatus
from .simulation_manager import SimulationManager
from .simulation_runner import SimulationRunner, RunnerStatus
from .report_agent import ReportManager, ReportStatus
from .research_drafts import ResearchDrafts
from .research_estimates import estimate, request_observations
from .research_runs import ResearchStopped
from .research_storage import atomic_json
from contextvars import ContextVar

stage_locale = ContextVar('research_stage_locale', default='en')


class ResearchStages:
    def __init__(self, app, root):
        self.app, self.root = app, Path(root)

    def call(self, path, data=None, *, method='POST', allow_stopped=False):
        context = current_context()
        if context and context.cancelled() and not allow_stopped:
            raise ResearchStopped('Research stopped')
        with self.app.test_client() as client:
            response = client.open('/api'+path,method=method,json=data,headers={'Accept-Language':stage_locale.get()})
        value = response.get_json() or {}
        if response.status_code >= 400 or value.get('success') is False:
            raise RuntimeError(value.get('error') or 'Research stage failed')
        return value.get('data',value)

    def wait(self, poll, stopped, update, *, terminal, failed=('failed',), key='status', rounds_only=False):
        while True:
            if stopped():
                raise ResearchStopped('Research stopped')
            value = poll()
            update(stage_progress={key:value[key] for key in ('status','runner_status','progress','current_round','total_rounds','total_actions_count','message','error','simulation_completed','memory_status') if key in value})
            state = value.get(key)
            if rounds_only and value.get('simulation_completed'):
                return value
            if state in terminal:
                return value
            if state in failed:
                raise RuntimeError(value.get('error') or value.get('error_message') or 'Research stage failed')
            time.sleep(.5)

    def graph_control(self, run, stopped):
        if (run.get('graph_settings') or {}).get('provider') == 'graphiti':
            from ..utils.zep import get_zep_client
            get_zep_client(timeout=5).call('research.stop',run_id=run['run_id'],stopped=stopped)

    def execute(self, stage, run, update, stopped):
        token = stage_locale.set(run.get('locale', 'en'))
        try:
            return self._execute(stage, run, update, stopped)
        finally:
            stage_locale.reset(token)

    def _execute(self, stage, run, update, stopped):
        if stopped():
            raise ResearchStopped('Research stopped')
        self.graph_control(run,False)
        settings = run['settings']
        if stage == 'analysis':
            project_id = run.get('project_id') or 'proj_'+run['run_id'][-12:]
            project = ProjectManager.get_project(project_id)
            if not project:
                draft = ResearchDrafts(self.root).get(run['draft_id'])
                project = ProjectManager.create_project(name=draft['question'][:80], project_id=project_id)
                project.simulation_requirement = draft['question']
                project.files = draft['files']
                text = ResearchDrafts(self.root).text(run['draft_id'])
                project.total_text_length = len(text)
                ProjectManager.save_extracted_text(project_id,text)
            project.research_run_id = run['run_id']
            project.research_settings = settings
            ProjectManager.save_project(project)
            update(project_id=project_id)
            self.call('/graph/ontology/resume',{'project_id':project_id})
        elif stage == 'graph':
            project = ProjectManager.get_project(run['project_id'])
            if project.status != ProjectStatus.GRAPH_COMPLETED:
                self.call('/graph/build',{'project_id':project.project_id})
                self.wait(lambda:ProjectManager.get_project(project.project_id).to_dict(),stopped,update,
                          terminal={'graph_completed'})
        elif stage == 'preparation':
            manager = SimulationManager()
            project = ProjectManager.get_project(run['project_id'])
            simulation_id = run.get('simulation_id') or 'sim_'+run['run_id'][-12:]
            state = manager.get_simulation(simulation_id)
            if not state:
                manager.create_simulation(project_id=run['project_id'],graph_id=project.graph_id,
                    enable_twitter=settings['platform'] != 'reddit',enable_reddit=settings['platform'] != 'twitter',
                    simulation_id=simulation_id)
            update(simulation_id=simulation_id)
            self.call('/simulation/prepare',{'simulation_id':simulation_id,
                'parallel_profile_count':settings['concurrency']})
            self.wait(lambda:self.call('/simulation/prepare/status',{'simulation_id':simulation_id}),
                      stopped,update,terminal={'ready','completed'})
            config = manager.get_simulation_config(simulation_id)
            timing = config.get('time_config',{})
            plan = {'agents':len(config.get('agent_configs',[])) or manager.get_simulation(simulation_id).entities_count,
                    'rounds':max(1,math.floor(timing.get('total_simulation_hours',72)*60/max(timing.get('minutes_per_round',30),1)))}
            records = usage_records(str(self.root / 'runs' / run['run_id'] / 'usage.sqlite3'))
            update(estimate=estimate(ProjectManager.get_extracted_text(run['project_id']),settings,
                                     plan=plan, observations=request_observations(records, settings)))
        elif stage == 'simulation':
            state = SimulationRunner.get_run_state(run['simulation_id'])
            if state and getattr(state, 'simulation_completed', False):
                return
            if state is None or state.runner_status not in {RunnerStatus.RUNNING,RunnerStatus.STARTING,RunnerStatus.COMPLETED}:
                self.call('/simulation/start',{'simulation_id':run['simulation_id'],
                    'platform':settings['platform'],'simulation_effort':settings['depth'],
                    'enable_graph_memory_update':True, 'force':state is not None})
            def poll():
                value = self.call('/simulation/'+run['simulation_id']+'/run-status',method='GET')
                # Natural OASIS completion can leave its interview process alive.
                # Runner finalizes memory and reports completed once all selected platforms finish.
                return value
            self.wait(poll,stopped,update,terminal={'completed'},failed={'failed','stopped'},key='runner_status',rounds_only=True)
        elif stage == 'memory':
            # Terminal runner status is only published after memory finalization.
            state = SimulationRunner.get_run_state(run['simulation_id'])
            if state is None:
                raise RuntimeError('Simulation results are missing')
            if state.runner_status not in {RunnerStatus.COMPLETED,RunnerStatus.STOPPED}:
                if getattr(state, 'simulation_completed', False):
                    if state.runner_status == RunnerStatus.FAILED:
                        self.call('/simulation/retry-memory', {'simulation_id':run['simulation_id']})
                else:
                    self.call('/simulation/stop',{'simulation_id':run['simulation_id'],'wait':False})
                self.wait(lambda:self.call('/simulation/'+run['simulation_id']+'/run-status',method='GET'),
                          stopped,update,terminal={'stopped','completed'},key='runner_status')
            self.synchronize_usage(run)
        elif stage == 'report':
            result = self.call('/report/generate',{'simulation_id':run['simulation_id'],'resume':True})
            report_id = result['report_id']
            update(report_id=report_id)
            def poll():
                report = ReportManager.get_report(report_id)
                return report.to_dict() if report else {'status':'pending'}
            self.wait(poll,stopped,update,terminal={'completed'})

    def stop(self, run):
        simulation_id = run.get('simulation_id')
        if run['stage'] in {'simulation','memory'} and simulation_id:
            state = SimulationRunner.get_run_state(simulation_id)
            if state:
                # Preserve the established finalization barrier; memory may finish
                # after Stop, but reporting never starts automatically.
                SimulationRunner.stop_simulation(simulation_id)
            self.graph_control(run,True)
            return
        self.graph_control(run,True)
        # Wait for the stage-owned thread to observe cancellation before releasing
        # coordinator ownership. A later Resume cannot revive an old worker.
        while True:
            if run['stage'] == 'graph' and run.get('project_id'):
                from ..api.graph import _project_has_active_build
                active = _project_has_active_build(ProjectManager.get_project(run['project_id']))
            elif run['stage'] == 'preparation' and simulation_id:
                from ..api.simulation import _active_prepare_task
                active = _active_prepare_task(simulation_id)
            elif run['stage'] == 'report' and simulation_id:
                from ..api.report import _active_report_tasks
                active = simulation_id in _active_report_tasks
            else:
                active = False
            if not active:
                return
            time.sleep(.25)

    def synchronize_usage(self, run):
        path = self.root / 'runs' / run['run_id'] / 'telemetry.json'
        graph = (run.get('graph_settings') or {}).get('provider')
        if graph != 'graphiti':
            if graph:
                atomic_json(path, {'graph_coverage':'unknown', 'checked_at':time.time()})
            return
        try:
            from ..utils.zep import get_zep_client
            result = get_zep_client(timeout=3).call('research.usage',run_id=run['run_id'])
            records = [vars(value) if not isinstance(value,dict) else value for value in result.calls]
            import_records(str(self.root / 'runs' / run['run_id'] / 'usage.sqlite3'),records)
            atomic_json(path, {'graph_coverage':'complete', 'checked_at':time.time()})
        except Exception:
            # Missing graph telemetry remains unknown, never silently zero.
            atomic_json(path, {'graph_coverage':'unknown', 'checked_at':time.time()})
