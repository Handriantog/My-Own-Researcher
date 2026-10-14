"""The real coordinator and HTTP stage bridge, with only expensive stages faked."""
import io
import time
from flask import Flask, request
from werkzeug.datastructures import FileStorage
from research_runtime import current_context
from app.models.project import ProjectManager, ProjectStatus
from app.services.simulation_manager import SimulationManager
from app.services.simulation_runner import SimulationRunner
from app.services.report_agent import ReportManager
from app.services.research_runs import ResearchRuns
from app.services.research_drafts import ResearchDrafts
from types import SimpleNamespace


def test_full_pipeline_preserves_reviewed_model_rounds_platform_and_report(tmp_path,monkeypatch):
    monkeypatch.setattr(ProjectManager,'PROJECTS_DIR',str(tmp_path / 'projects'))
    manager=SimulationManager()
    states={}
    monkeypatch.setattr(SimulationManager,'get_simulation',lambda self,id:states.get(id))
    def create(self,**kw):
        states[kw['simulation_id']]=SimpleNamespace(**kw,entities_count=5)
        return states[kw['simulation_id']]
    monkeypatch.setattr(SimulationManager,'create_simulation',create)
    monkeypatch.setattr(SimulationManager,'get_simulation_config',lambda self,id:{'agent_configs':[{}]*5,'time_config':{'total_simulation_hours':24,'minutes_per_round':60}})
    monkeypatch.setattr(SimulationRunner,'get_run_state',lambda id:None)
    monkeypatch.setattr(ReportManager,'get_report',lambda id:SimpleNamespace(to_dict=lambda:{'status':'completed','report_id':id}))
    app=Flask(__name__)
    calls=[]
    @app.route('/api/<path:path>',methods=['GET','POST'])
    def stage(path):
        data=request.get_json(silent=True) or {}
        calls.append((path,data,current_context().model))
        if path=='graph/ontology/resume':
            project=ProjectManager.get_project(data['project_id']);project.ontology={'entity_types':[]};ProjectManager.save_project(project)
        elif path=='graph/build':
            project=ProjectManager.get_project(data['project_id']);project.status=ProjectStatus.GRAPH_COMPLETED;project.graph_id='g1';ProjectManager.save_project(project)
        elif path=='simulation/prepare/status':
            return {'success':True,'data':{'status':'ready'}}
        elif path.endswith('/run-status'):
            return {'success':True,'data':{'runner_status':'completed'}}
        elif path=='report/generate':
            return {'success':True,'data':{'report_id':'report_final'}}
        return {'success':True,'data':{}}
    # Memory finalization already tested separately in runner barrier tests.
    from app.services.research_stages import ResearchStages
    execute=ResearchStages.execute
    def finalized(self,stage,run,update,stopped):
        if stage!='memory':
            return execute(self,stage,run,update,stopped)
    monkeypatch.setattr(ResearchStages,'execute',finalized)
    draft=ResearchDrafts(tmp_path).create([FileStorage(stream=io.BytesIO(b'Evidence from 200 employees.'),filename='brief.txt')],'Launch a pilot?')
    runs=ResearchRuns(app,root=tmp_path)
    run=runs.start(draft['draft_id'],{'provider':'codex','model':'chosen-model','concurrency':3,'depth':'quick','platform':'reddit'},'pipeline')
    for _ in range(200):
        result=runs.get(run['run_id'])
        if result['status'] in {'failed','completed'}:break
        time.sleep(.01)
    assert result['status']=='completed',result.get('error')
    assert result['report_id']=='report_final'
    assert all(model=='chosen-model' for _,_,model in calls)
    start=next(data for path,data,_ in calls if path=='simulation/start')
    assert start['platform']=='reddit' and start['simulation_effort']=='quick'
    assert start['enable_graph_memory_update'] is True
    assert result['estimate']['assumptions']['rounds']==[6,6]
    assert result['estimate']['assumptions']['agents']==[5,5]
    project=ProjectManager.get_project(result['project_id'])
    assert project.research_run_id==run['run_id']
